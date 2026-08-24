from __future__ import annotations

import asyncio
import contextlib
import json
from pathlib import Path
import re
import secrets
import time
from typing import Any

from fastapi import HTTPException

from ..schemas import (
    AutomationChatDraftRequest,
    AutonomousAutomationRequest,
    NotificationTestRequest,
)


def configure_automation_domain(
    *, plugin_load, plugin_save, search_tokens, live_events,
    pending_confirmations, entity_domain_fn, effective_entity_access_fn,
    ensure_control_allowed_fn, ensure_read_allowed_fn, ha_client,
    entity_policy_loader, notification_store_fn,
    notification_quiet_now_fn, notification_test_fn,
) -> None:
    global _plugin_load, _plugin_save, _search_tokens, HA_LIVE_EVENTS
    global PENDING_AUTOMATION_CONFIRMATIONS, entity_domain, effective_entity_access
    global ensure_control_allowed, ensure_read_allowed, ha_ws, load_entity_policy
    global notification_store, _notification_quiet_now, test_notification_channel
    _plugin_load = plugin_load
    _plugin_save = plugin_save
    _search_tokens = search_tokens
    HA_LIVE_EVENTS = live_events
    PENDING_AUTOMATION_CONFIRMATIONS = pending_confirmations
    entity_domain = entity_domain_fn
    effective_entity_access = effective_entity_access_fn
    ensure_control_allowed = ensure_control_allowed_fn
    ensure_read_allowed = ensure_read_allowed_fn
    ha_ws = ha_client
    load_entity_policy = entity_policy_loader
    notification_store = notification_store_fn
    _notification_quiet_now = notification_quiet_now_fn
    test_notification_channel = notification_test_fn


AUTOMATION_STORAGE_PATH = Path("/data/autonomous_automations.json")

AUTOMATION_DEFAULT_SETTINGS = {
    "operating_mode": "suggest_only",
    "presence_entity": "",
    "require_presence": True,
    "respect_quiet_hours": True,
    "minimum_confidence": 0.75,
    "default_cooldown_minutes": 30,
    "autonomous_risk_ceiling": "low",
    "notify_after_autonomous_action": True,
    "passive_learning_enabled": True,
}

AUTOMATION_AREA_CACHE_SECONDS = 300

AUTOMATION_ROOM_OCCUPANCY_SECONDS = 120

AUTOMATION_CONTEXT_LOCK = asyncio.Lock()

AUTOMATION_AREA_REFRESHED_AT = 0.0

AUTOMATION_DISCOVERY_TASKS: dict[str, asyncio.Task[Any]] = {}

def _automation_empty_store():
    return {
        "settings": dict(AUTOMATION_DEFAULT_SETTINGS),
        "automations": [],
        "suggestions": [],
        "timeline": [],
        "entity_memory": [],
        "area_context": {"refreshed_at": 0, "areas": [], "entities": [], "labels": [], "zones": []},
        "observations": [],
        "patterns": [],
        "discoveries": [],
    }

def automation_store():
    data = _plugin_load(AUTOMATION_STORAGE_PATH)
    if not data:
        return _automation_empty_store()
    settings = dict(AUTOMATION_DEFAULT_SETTINGS)
    if isinstance(data.get("settings"), dict):
        settings.update(data["settings"])
    return {
        "settings": settings,
        "automations": data.get("automations") if isinstance(data.get("automations"), list) else [],
        "suggestions": data.get("suggestions") if isinstance(data.get("suggestions"), list) else [],
        "timeline": data.get("timeline") if isinstance(data.get("timeline"), list) else [],
        "entity_memory": data.get("entity_memory") if isinstance(data.get("entity_memory"), list) else [],
        "area_context": data.get("area_context") if isinstance(data.get("area_context"), dict) else {"refreshed_at": 0, "areas": [], "entities": [], "labels": [], "zones": []},
        "observations": data.get("observations") if isinstance(data.get("observations"), list) else [],
        "patterns": data.get("patterns") if isinstance(data.get("patterns"), list) else [],
        "discoveries": data.get("discoveries") if isinstance(data.get("discoveries"), list) else [],
    }

def _automation_save(data):
    data["automations"] = list(data.get("automations") or [])[:100]
    data["suggestions"] = list(data.get("suggestions") or [])[:100]
    data["timeline"] = list(data.get("timeline") or [])[:200]
    data["entity_memory"] = list(data.get("entity_memory") or [])[:200]
    data["observations"] = list(data.get("observations") or [])[:1500]
    data["patterns"] = list(data.get("patterns") or [])[:200]
    data["discoveries"] = list(data.get("discoveries") or [])[:100]
    _plugin_save(AUTOMATION_STORAGE_PATH, data)

def _automation_entity_role(entity_id: str, attributes: dict[str, Any] | None = None) -> str:
    attributes = attributes or {}
    domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
    device_class = str(attributes.get("device_class") or "").casefold()
    identity = f"{entity_id} {attributes.get('friendly_name') or ''}".casefold()
    if domain == "light":
        return "light"
    if domain in {"person", "device_tracker"}:
        return "home_presence"
    if domain == "binary_sensor" and device_class in {"occupancy", "motion", "presence"}:
        return "room_presence"
    if domain == "binary_sensor" and any(word in identity for word in ("occupancy", "motion", "presence")):
        return "room_presence"
    if domain == "sensor" and (device_class == "illuminance" or "illuminance" in identity or "lux" in identity):
        return "illuminance"
    if domain == "sensor" and device_class == "temperature":
        return "temperature"
    if domain == "climate":
        return "climate"
    if domain == "sun":
        return "daylight"
    return domain or "entity"

def _automation_context_key(value: Any) -> str:
    return "_".join(re.findall(r"[a-z0-9]+", str(value or "").casefold()))

def _automation_site_key(value: Any) -> str:
    key = _automation_context_key(value)
    for prefix in ("site_", "location_", "property_"):
        if key.startswith(prefix):
            return key[len(prefix):]
    return key

def _automation_reconcile_learning(data: dict[str, Any], snapshot: dict[str, Any]) -> None:
    entity_map = {str(item.get("entity_id") or ""): item for item in snapshot.get("entities", [])}
    for collection in ("patterns", "discoveries"):
        for item in data.get(collection, []):
            mapping = entity_map.get(str(item.get("action_entity") or ""))
            if not mapping or not mapping.get("area_id"):
                continue
            item["area_id"] = mapping.get("area_id")
            item["area_name"] = mapping.get("area_name")
            item["site_label"] = mapping.get("site_label") or ""
            item["site_name"] = mapping.get("site_name") or ""
            item["zone_entity_id"] = mapping.get("zone_entity_id") or ""
            kind = str(item.get("kind") or "")
            prefix = "dark_occupied_light" if kind == "dark_occupied_light" else "occupancy_light"
            item["key"] = f"{prefix}:{mapping.get('area_id')}:{item.get('action_entity')}"
            if kind == "dark_occupied_light":
                item["title"] = f"{mapping.get('area_name') or mapping.get('area_id')} lighting"

async def _automation_refresh_area_context(force: bool = False) -> dict[str, Any]:
    """Import HA Areas, Labels, Zones, and inherited device assignments."""
    global AUTOMATION_AREA_REFRESHED_AT
    now = time.time()
    current = automation_store().get("area_context") or {}
    if not force and current.get("entities") and now - AUTOMATION_AREA_REFRESHED_AT < AUTOMATION_AREA_CACHE_SECONDS:
        return current
    async with AUTOMATION_CONTEXT_LOCK:
        now = time.time()
        current = automation_store().get("area_context") or {}
        if not force and current.get("entities") and now - AUTOMATION_AREA_REFRESHED_AT < AUTOMATION_AREA_CACHE_SECONDS:
            return current
        await ha_ws.connect()
        area_result, device_result, entity_result = await asyncio.gather(
            ha_ws.command({"type": "config/area_registry/list"}),
            ha_ws.command({"type": "config/device_registry/list"}),
            ha_ws.command({"type": "config/entity_registry/list"}),
        )
        try:
            label_result = await ha_ws.command({"type": "config/label_registry/list"})
        except (RuntimeError, OSError, asyncio.TimeoutError):
            label_result = {"result": []}
        area_records = {
            str(item.get("area_id") or item.get("id") or ""): item
            for item in area_result.get("result") or [] if isinstance(item, dict)
        }
        labels = {
            str(item.get("label_id") or item.get("id") or ""): str(item.get("name") or item.get("label_id") or item.get("id") or "")
            for item in label_result.get("result") or [] if isinstance(item, dict)
        }
        devices = {
            str(item.get("id") or ""): item for item in device_result.get("result") or []
            if isinstance(item, dict) and item.get("id")
        }
        zones = []
        zone_keys: dict[str, dict[str, Any]] = {}
        for entity_id, state in ha_ws.state_cache.items():
            if not entity_id.startswith("zone."):
                continue
            attributes = state.get("attributes") or {}
            zone = {
                "entity_id": entity_id,
                "name": str(attributes.get("friendly_name") or entity_id.split(".", 1)[1].replace("_", " ").title()),
                "occupants": state.get("state"),
                "passive": bool(attributes.get("passive", False)),
            }
            zones.append(zone)
            for value in (zone["name"], entity_id.split(".", 1)[1]):
                zone_keys[_automation_site_key(value)] = zone

        areas: dict[str, dict[str, Any]] = {}
        for area_id, entry in area_records.items():
            if not area_id:
                continue
            label_ids = [str(value) for value in entry.get("labels") or [] if str(value)]
            label_names = [labels.get(value, value) for value in label_ids]
            site_label = next((name for name in label_names if _automation_context_key(name).startswith(("site_", "location_", "property_"))), "")
            if not site_label:
                site_label = next((name for name in label_names if _automation_site_key(name) in zone_keys), "")
            zone = zone_keys.get(_automation_site_key(site_label)) if site_label else None
            areas[area_id] = {
                "area_id": area_id,
                "name": str(entry.get("name") or area_id),
                "label_ids": label_ids,
                "labels": label_names,
                "site_label": site_label,
                "site_name": str((zone or {}).get("name") or site_label.removeprefix("site-").removeprefix("site_").strip()),
                "zone_entity_id": str((zone or {}).get("entity_id") or ""),
            }

        entities: list[dict[str, Any]] = []
        for entry in entity_result.get("result") or []:
            if not isinstance(entry, dict) or not entry.get("entity_id"):
                continue
            entity_id = str(entry["entity_id"]).lower()
            state = ha_ws.state_cache.get(entity_id) or {}
            attributes = state.get("attributes") or {}
            device = devices.get(str(entry.get("device_id") or "")) or {}
            direct_area = str(entry.get("area_id") or "")
            inherited_area = str(device.get("area_id") or "")
            area_id = direct_area or inherited_area
            area = areas.get(area_id) or {}
            entity_label_ids = [str(value) for value in entry.get("labels") or [] if str(value)]
            device_label_ids = [str(value) for value in device.get("labels") or [] if str(value)]
            combined_label_ids = list(dict.fromkeys([*entity_label_ids, *device_label_ids, *area.get("label_ids", [])]))
            combined_labels = [labels.get(value, value) for value in combined_label_ids]
            label_keys = {_automation_context_key(value) for value in combined_labels}
            role = _automation_entity_role(entity_id, attributes)
            if label_keys & {"presence_signal", "room_presence", "occupancy_signal"}:
                role = "room_presence"
            entities.append({
                "entity_id": entity_id,
                "area_id": area_id,
                "area_name": area.get("name") or "",
                "area_source": "entity" if direct_area else "device" if inherited_area else "unassigned",
                "device_id": str(entry.get("device_id") or ""),
                "role": role,
                "label_ids": combined_label_ids,
                "labels": combined_labels,
                "control_blocked_by_label": bool(label_keys & {"never_automate", "observe_only", "no_control"}),
                "primary_entity": bool(label_keys & {"primary_light", "primary_device"}),
                "site_label": area.get("site_label") or "",
                "site_name": area.get("site_name") or "",
                "zone_entity_id": area.get("zone_entity_id") or "",
            })
        snapshot = {
            "refreshed_at": now,
            "areas": sorted(areas.values(), key=lambda item: str(item.get("name") or "").casefold()),
            "entities": entities,
            "labels": [{"label_id": key, "name": value} for key, value in sorted(labels.items(), key=lambda item: item[1].casefold()) if key],
            "zones": sorted(zones, key=lambda item: str(item.get("name") or "").casefold()),
        }
        engine_lock = globals().get("AUTOMATION_ENGINE_LOCK")
        if engine_lock is None:
            data = automation_store()
            data["area_context"] = snapshot
            _automation_reconcile_learning(data, snapshot)
            _automation_save(data)
        else:
            async with engine_lock:
                data = automation_store()
                data["area_context"] = snapshot
                _automation_reconcile_learning(data, snapshot)
                _automation_save(data)
        AUTOMATION_AREA_REFRESHED_AT = now
        return snapshot

def _automation_area_entity(data: dict[str, Any], entity_id: str) -> dict[str, Any]:
    return next((
        item for item in (data.get("area_context") or {}).get("entities", [])
        if str(item.get("entity_id") or "") == entity_id
    ), {})

def _automation_label_blocks_control(data: dict[str, Any], entity_id: str) -> bool:
    return bool(_automation_area_entity(data, entity_id).get("control_blocked_by_label"))

def _automation_alias_key(value: Any) -> str:
    return " ".join(re.sub(r"[^a-z0-9\u0370-\u03ff]+", " ", str(value or "").casefold()).split())[:255]

def _automation_remember_entity(data: dict[str, Any], alias: str, entity_id: str, role: str) -> None:
    import secrets

    normalized_alias = _automation_alias_key(alias)
    entity_id = str(entity_id or "").strip().lower()
    if not normalized_alias or len(normalized_alias) < 2 or not entity_id:
        return
    ensure_read_allowed(entity_id)
    policy = load_entity_policy().get(entity_id) or {}
    records = data.setdefault("entity_memory", [])
    existing = next((
        item for item in records
        if _automation_alias_key(item.get("alias")) == normalized_alias and str(item.get("role") or "") == role
    ), None)
    now = time.time()
    if existing:
        existing.update({
            "entity_id": entity_id,
            "friendly_name": str(policy.get("friendly_name") or entity_id)[:255],
            "confirmed_at": now,
            "use_count": int(existing.get("use_count") or 0) + 1,
        })
        return
    records.insert(0, {
        "id": secrets.token_hex(8),
        "alias": normalized_alias,
        "entity_id": entity_id,
        "friendly_name": str(policy.get("friendly_name") or entity_id)[:255],
        "role": role,
        "confirmed_at": now,
        "use_count": 1,
    })

def automation_entity_memory_context(message: str) -> str:
    query = _automation_alias_key(message)
    query_tokens = _search_tokens(query)
    matches: list[dict[str, Any]] = []
    for item in automation_store().get("entity_memory", []):
        alias = _automation_alias_key(item.get("alias"))
        alias_tokens = _search_tokens(alias)
        if alias and (alias in query or query in alias or query_tokens & alias_tokens):
            entity_id = str(item.get("entity_id") or "")
            if effective_entity_access(entity_id):
                matches.append(item)
    if not matches:
        return ""
    compact = [{
        "alias": item.get("alias"), "entity_id": item.get("entity_id"),
        "friendly_name": item.get("friendly_name"), "role": item.get("role"),
    } for item in matches[:12]]
    return "Remembered automation entity mappings (verify availability before use): " + json.dumps(compact, ensure_ascii=False)

def automation_brain_memory_context(message: str) -> str:
    normalized = _automation_alias_key(message)
    if not any(term in normalized for term in ("automation", "learn", "notice", "pattern", "suggest", "room", "area", "home", "light")):
        return ""
    data = automation_store()
    context = data.get("area_context") or {}
    areas = [{
        "name": item.get("name"), "site": item.get("site_name"),
        "site_label": item.get("site_label"), "zone": item.get("zone_entity_id"),
    } for item in context.get("areas", []) if item.get("name")]
    zones = [{"entity_id": item.get("entity_id"), "name": item.get("name"), "occupants": item.get("occupants")} for item in context.get("zones", [])]
    patterns = [{
        "kind": item.get("kind"), "area": item.get("area_name"),
        "action_entity": item.get("action_entity"), "occurrences": item.get("occurrences"),
        "confidence": item.get("confidence"), "status": item.get("status"),
    } for item in data.get("patterns", []) if item.get("status") == "learned"][:8]
    discoveries = [{
        "title": item.get("title"), "area": item.get("area_name"),
        "confidence": item.get("confidence"), "status": item.get("status"),
        "preference": item.get("preference"), "evidence": item.get("evidence"),
    } for item in data.get("discoveries", [])][:8]
    if not areas and not patterns and not discoveries:
        return ""
    return "Automation Brain local context (observations are evidence, not certainty): " + json.dumps({
        "home_assistant_areas": areas[:30], "home_assistant_zones": zones[:20],
        "learned_patterns": patterns, "discoveries": discoveries,
    }, ensure_ascii=False)

def _automation_event(data, event_type, title, detail=""):
    import secrets

    data.setdefault("timeline", []).insert(0, {
        "id": secrets.token_hex(8), "type": str(event_type)[:40],
        "title": str(title)[:160], "detail": str(detail)[:500],
        "created_at": time.time(),
    })

def _automation_payload(request):
    payload = request.model_dump()
    payload["name"] = " ".join(payload["name"].split())
    payload["objective"] = payload["objective"].strip()
    payload["presence_entity"] = payload["presence_entity"].strip().lower()
    payload["signal_entities"] = list(dict.fromkeys(
        str(value).strip().lower()[:255] for value in payload["signal_entities"] if str(value).strip()
    ))[:20]
    payload["context_notes"] = payload["context_notes"].strip()
    payload["proposal_template"] = payload["proposal_template"].strip()
    payload["action_entity"] = payload["action_entity"].strip().lower()
    payload["action_service"] = payload["action_service"].strip().lower()
    payload["trigger_entity"] = payload["trigger_entity"].strip().lower()
    payload["trigger_value"] = payload["trigger_value"].strip()
    payload["action_service_data"] = dict(payload.get("action_service_data") or {})
    if payload["enabled"] and not payload["trigger_entity"]:
        raise HTTPException(status_code=400, detail="An enabled automation requires a trigger entity")
    if payload["trigger_entity"]:
        ensure_read_allowed(payload["trigger_entity"])
    if payload["presence_entity"]:
        ensure_read_allowed(payload["presence_entity"])
    for entity_id in payload["signal_entities"]:
        ensure_read_allowed(entity_id)
    if payload["action_entity"] and not effective_entity_access(payload["action_entity"]):
        raise HTTPException(status_code=403, detail="The action entity is not enabled in ZBRANO entity policy")
    if payload["action_service"] and not re.fullmatch(r"[a-z0-9_]+\.[a-z0-9_]+", payload["action_service"]):
        raise HTTPException(status_code=400, detail="Action service must use domain.service format")
    if len(json.dumps(payload["action_service_data"], ensure_ascii=False)) > 4000:
        raise HTTPException(status_code=400, detail="Action service data is too large")
    return payload

def _automation_payload_http(request: AutonomousAutomationRequest) -> dict[str, Any]:
    try:
        return _automation_payload(request)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

def _automation_preview(item: dict[str, Any]) -> dict[str, Any]:
    trigger = f"{item.get('trigger_entity')} {str(item.get('trigger_operator') or '').replace('_', ' ')}"
    if str(item.get("trigger_value") or ""):
        trigger += f" {item.get('trigger_value')}"
    if int(item.get("trigger_for_seconds") or 0):
        trigger += f" for {int(item.get('trigger_for_seconds') or 0)} seconds"
    action = "No device action"
    if item.get("action_service") and item.get("action_entity"):
        action = f"{item.get('action_service')} → {item.get('action_entity')}"
    return {
        "name": item.get("name"),
        "trigger": trigger,
        "presence": item.get("presence_entity") or "not required by this rule",
        "suggestion": item.get("proposal_template"),
        "action": action,
        "authority": item.get("execution_policy"),
        "cooldown_minutes": item.get("cooldown_minutes"),
        "enabled": bool(item.get("enabled")),
    }

async def _prepare_chat_automation(request: AutomationChatDraftRequest, session_id: str) -> dict[str, Any]:
    import secrets

    data = automation_store()
    if len(data["automations"]) >= 100:
        raise HTTPException(status_code=400, detail="Automation draft limit reached (100)")
    if bool(request.action_entity) != bool(request.action_service):
        raise HTTPException(status_code=400, detail="An automation action requires both an entity and a Home Assistant service")
    if request.action_entity:
        action_domain = entity_domain(request.action_entity)
        service_domain = request.action_service.split(".", 1)[0]
        if action_domain not in AUTOMATION_AUTONOMOUS_DOMAINS or service_domain != action_domain:
            raise HTTPException(status_code=400, detail="Chat-created actions must use the same approved low-risk domain as their target entity")
    try:
        payload = _automation_payload(AutonomousAutomationRequest(
            name=request.name,
            objective=request.objective,
            presence_entity=request.presence_entity,
            signal_entities=request.signal_entities,
            context_notes="Prepared conversationally from an explicit user request. Confirmed entity mappings are retained in Automation Memory.",
            proposal_template=request.suggestion,
            action_entity=request.action_entity,
            action_service=request.action_service,
            action_service_data=request.action_service_data,
            cooldown_minutes=request.cooldown_minutes,
            confidence_threshold=max(0.75, float(data["settings"].get("minimum_confidence") or 0.75)),
            risk_level=request.risk_level,
            execution_policy=request.execution_policy,
            notify_on_action=request.notify_on_action,
            reversible_only=request.reversible_only,
            max_actions_per_hour=request.max_actions_per_hour,
            enabled=False,
            trigger_entity=request.trigger_entity,
            trigger_operator=request.trigger_operator,
            trigger_value=request.trigger_value,
            trigger_for_seconds=request.trigger_for_seconds,
        ))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    now = time.time()
    duplicate = next((item for item in data["automations"] if (
        item.get("source") == "chat" and not item.get("enabled")
        and str(item.get("trigger_entity") or "") == payload["trigger_entity"]
        and str(item.get("trigger_operator") or "") == payload["trigger_operator"]
        and str(item.get("trigger_value") or "") == payload["trigger_value"]
        and str(item.get("action_entity") or "") == payload["action_entity"]
        and str(item.get("action_service") or "") == payload["action_service"]
    )), None)
    if duplicate:
        duplicate.update(payload)
        duplicate.update({"status": "review_required", "updated_at": now, "review_required": True})
        automation = duplicate
        data["automations"] = [automation, *[item for item in data["automations"] if item is not automation]]
    else:
        automation = {
            "id": secrets.token_hex(12), "status": "review_required",
            "created_at": now, "updated_at": now, "source": "chat",
            "review_required": True,
            **payload,
        }
        data["automations"].insert(0, automation)
    _automation_remember_entity(data, request.trigger_alias, request.trigger_entity, "trigger")
    _automation_remember_entity(data, request.presence_alias, request.presence_entity, "presence")
    _automation_remember_entity(data, request.action_alias, request.action_entity, "action")
    _automation_event(data, "draft", f"Chat automation prepared: {automation['name']}", _automation_preview(automation)["trigger"])
    _automation_save(data)
    PENDING_AUTOMATION_CONFIRMATIONS[session_id] = automation["id"]
    return {
        "prepared": True,
        "updated_existing_draft": bool(duplicate),
        "automation_id": automation["id"],
        "preview": _automation_preview(automation),
        "confirmation_required": True,
        "instruction": "Explain this preview in plain language and ask the user to reply confirm or cancel. Do not claim the automation is active yet.",
    }

def _activate_automation(automation_id: str, source: str) -> dict[str, Any]:
    data = automation_store()
    automation = next((item for item in data["automations"] if item.get("id") == automation_id), None)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation draft not found")
    try:
        ensure_read_allowed(str(automation.get("trigger_entity") or ""))
        if automation.get("presence_entity"):
            ensure_read_allowed(str(automation.get("presence_entity")))
        for entity_id in automation.get("signal_entities") or []:
            ensure_read_allowed(str(entity_id))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    policy = str(automation.get("execution_policy") or "suggest")
    if policy in {"approval_required", "autonomous"} and not (
        automation.get("action_entity") and automation.get("action_service")
    ):
        raise HTTPException(status_code=400, detail="This authority requires a complete proposed action")
    automation["enabled"] = True
    automation["status"] = "armed"
    automation["review_required"] = False
    automation["reviewed_at"] = time.time()
    automation["updated_at"] = time.time()
    _automation_event(data, "configuration", f"Automation activated: {automation.get('name')}", f"source={source}; authority={policy}")
    _automation_save(data)
    return {"activated": True, "automation": automation, "preview": _automation_preview(automation)}

AUTOMATION_ENGINE_LOCK = asyncio.Lock()

AUTOMATION_PENDING_TASKS: dict[str, asyncio.Task[Any]] = {}

AUTOMATION_RISK_ORDER = {"informational": 0, "low": 1, "controlled": 2, "high": 3}

AUTOMATION_AUTONOMOUS_DOMAINS = {"light", "switch", "fan", "media_player", "climate", "input_boolean"}

def _automation_state_positive(value: Any) -> bool:
    return str(value or "").casefold() in {"on", "home", "present", "occupied", "true", "1"}

def _automation_dark_context(data: dict[str, Any], area_id: str) -> tuple[bool, str, float]:
    illuminance = []
    for mapping in (data.get("area_context") or {}).get("entities", []):
        if mapping.get("area_id") != area_id or mapping.get("role") != "illuminance":
            continue
        state = ha_ws.state_cache.get(str(mapping.get("entity_id") or "")) or {}
        try:
            illuminance.append((str(mapping.get("entity_id")), float(state.get("state"))))
        except (TypeError, ValueError):
            continue
    if illuminance:
        entity_id, lux = min(illuminance, key=lambda item: item[1])
        return lux < 80.0, f"{entity_id}={lux:g} lux", 0.92 if lux < 40 else 0.86
    sun_state = str((ha_ws.state_cache.get("sun.sun") or {}).get("state") or "").casefold()
    if sun_state:
        return sun_state == "below_horizon", f"sun.sun={sun_state}", 0.82
    hour = time.localtime().tm_hour
    return hour >= 21 or hour < 6, f"local hour={hour}; no illuminance or sun state", 0.68

def _automation_learning_pattern(data: dict[str, Any], area_id: str, light_id: str) -> dict[str, Any] | None:
    key = f"occupancy_light:{area_id}:{light_id}"
    return next((item for item in data.get("patterns", []) if item.get("key") == key), None)

def _automation_record_behavior(data: dict[str, Any], record: dict[str, Any], mapping: dict[str, Any]) -> None:
    import secrets

    now = time.time()
    role = str(mapping.get("role") or "entity")
    area_id = str(mapping.get("area_id") or "")
    observation = {
        "id": secrets.token_hex(6), "created_at": now,
        "entity_id": record.get("entity_id"), "area_id": area_id,
        "area_name": mapping.get("area_name") or "Unassigned",
        "site_name": mapping.get("site_name") or "",
        "zone_entity_id": mapping.get("zone_entity_id") or "",
        "role": role, "old_state": record.get("old_state"), "state": record.get("state"),
    }
    data.setdefault("observations", []).insert(0, observation)
    if role != "light" or not _automation_state_positive(record.get("state")) or not area_id:
        return
    recent_presence = next((item for item in data.get("observations", [])[1:] if (
        item.get("area_id") == area_id and item.get("role") == "room_presence"
        and _automation_state_positive(item.get("state")) and now - float(item.get("created_at") or 0) <= 600
    )), None)
    if not recent_presence:
        return
    light_id = str(record.get("entity_id") or "")
    key = f"occupancy_light:{area_id}:{light_id}"
    patterns = data.setdefault("patterns", [])
    pattern = next((item for item in patterns if item.get("key") == key), None)
    if not pattern:
        pattern = {
            "id": secrets.token_hex(8), "key": key, "kind": "occupancy_then_light",
            "area_id": area_id, "area_name": mapping.get("area_name") or area_id,
            "site_label": mapping.get("site_label") or "", "site_name": mapping.get("site_name") or "",
            "zone_entity_id": mapping.get("zone_entity_id") or "",
            "presence_entity": recent_presence.get("entity_id"), "action_entity": light_id,
            "occurrences": 0, "confidence": 0.55, "status": "watching", "created_at": now,
        }
        patterns.insert(0, pattern)
    pattern["occurrences"] = int(pattern.get("occurrences") or 0) + 1
    pattern["confidence"] = min(0.96, 0.55 + pattern["occurrences"] * 0.1)
    pattern["status"] = "learned" if pattern["occurrences"] >= 3 else "watching"
    pattern["last_observed_at"] = now

def _automation_discovery_record(data: dict[str, Any], area_id: str, area_name: str, light_id: str, mapping: dict[str, Any] | None = None) -> dict[str, Any]:
    import secrets

    key = f"dark_occupied_light:{area_id}:{light_id}"
    discovery = next((item for item in data.get("discoveries", []) if item.get("key") == key), None)
    if discovery:
        return discovery
    mapping = mapping or {}
    discovery = {
        "id": secrets.token_hex(8), "key": key, "kind": "dark_occupied_light",
        "title": f"{area_name} lighting", "area_id": area_id, "area_name": area_name,
        "site_label": mapping.get("site_label") or "", "site_name": mapping.get("site_name") or "",
        "zone_entity_id": mapping.get("zone_entity_id") or "",
        "action_entity": light_id, "action_service": "light.turn_on",
        "status": "learning", "confidence": 0.0, "evidence_count": 0,
        "positive_feedback": 0, "negative_feedback": 0, "preference": "ask",
        "created_at": time.time(), "last_suggested_at": 0,
    }
    data.setdefault("discoveries", []).insert(0, discovery)
    return discovery

async def _automation_discover_area(area_id: str) -> None:
    import secrets

    if not area_id:
        return
    async with AUTOMATION_ENGINE_LOCK:
        data = automation_store()
        if not data["settings"].get("passive_learning_enabled", True):
            return
        mappings = [item for item in (data.get("area_context") or {}).get("entities", []) if item.get("area_id") == area_id]
        if not mappings:
            return
        area_name = str(next((item.get("area_name") for item in mappings if item.get("area_name")), area_id))
        area_mapping = next((item for item in mappings if item.get("area_name")), mappings[0])
        site_name = str(area_mapping.get("site_name") or "")
        zone_entity_id = str(area_mapping.get("zone_entity_id") or "")
        occupancy = [item for item in mappings if item.get("role") == "room_presence" and effective_entity_access(str(item.get("entity_id") or ""))]
        now = time.time()
        sustained_presence_ids = {
            str(item.get("entity_id") or "") for item in data.get("observations", [])
            if item.get("area_id") == area_id and item.get("role") == "room_presence"
            and _automation_state_positive(item.get("state"))
            and AUTOMATION_ROOM_OCCUPANCY_SECONDS <= now - float(item.get("created_at") or 0) <= 300
        }
        active_occupancy = [item for item in occupancy if str(item.get("entity_id") or "") in sustained_presence_ids]
        if not active_occupancy:
            return
        if data["settings"].get("require_presence") and data["settings"].get("presence_entity"):
            presence_ok, presence_detail = _automation_presence_confirmed({}, data["settings"], zone_entity_id)
        else:
            presence_ok, presence_detail = True, f"room occupancy confirmed by {str(active_occupancy[0].get('entity_id') or '')}"
        if not presence_ok:
            return
        dark, darkness_detail, base_confidence = _automation_dark_context(data, area_id)
        if not dark:
            return
        lights = [item for item in mappings if item.get("role") == "light" and not item.get("control_blocked_by_label") and effective_entity_access(str(item.get("entity_id") or "")) == "low_risk_control_proposed"]
        lights.sort(key=lambda item: (not bool(item.get("primary_entity")), str(item.get("entity_id") or "")))
        off_lights = [item for item in lights if str((ha_ws.state_cache.get(str(item.get("entity_id") or "")) or {}).get("state") or "").casefold() == "off"]
        if not off_lights:
            return
        occupancy_id = str(active_occupancy[0].get("entity_id") or "")
        for light in off_lights[:3]:
            light_id = str(light.get("entity_id") or "")
            discovery = _automation_discovery_record(data, area_id, area_name, light_id, light)
            if discovery.get("preference") == "never_suggest" or discovery.get("status") == "suppressed":
                continue
            pattern = _automation_learning_pattern(data, area_id, light_id)
            pattern_confidence = float((pattern or {}).get("confidence") or 0)
            feedback_delta = 0.03 * int(discovery.get("positive_feedback") or 0) - 0.08 * int(discovery.get("negative_feedback") or 0)
            confidence = max(0.5, min(0.98, max(base_confidence, pattern_confidence) + feedback_delta))
            discovery.update({
                "status": "ready", "confidence": confidence,
                "evidence_count": int(discovery.get("evidence_count") or 0) + 1,
                "last_evidence_at": now, "presence_entity": occupancy_id,
                "evidence": f"{site_name + ' · ' if site_name else ''}{area_name} presence remained plausible for {AUTOMATION_ROOM_OCCUPANCY_SECONDS} seconds; {darkness_detail}; {light_id}=off; {presence_detail}",
            })
            if data["settings"].get("operating_mode") == "observe_only" or confidence < float(data["settings"].get("minimum_confidence") or 0.75):
                continue
            cooldown = max(30, int(data["settings"].get("default_cooldown_minutes") or 30)) * 60
            if now - float(discovery.get("last_suggested_at") or 0) < cooldown:
                continue
            if any(item.get("discovery_id") == discovery["id"] and item.get("status") in {"pending", "approval_required"} for item in data.get("suggestions", [])):
                continue
            detail = f"It is dark and you have been in {area_name} for a while. Would you like me to turn on the light?"
            suggestion = {
                "id": secrets.token_hex(10), "source": "automation_brain", "discovery_id": discovery["id"],
                "title": f"Lighting suggestion for {area_name}", "detail": detail,
                "evidence": discovery["evidence"], "confidence": confidence,
                "status": "approval_required", "action_entity": light_id,
                "action_service": "light.turn_on", "created_at": now,
            }
            data.setdefault("suggestions", []).insert(0, suggestion)
            discovery["last_suggested_at"] = now
            discovery["suggestion_count"] = int(discovery.get("suggestion_count") or 0) + 1
            _automation_event(data, "discovery", f"Automation Brain suggestion: {area_name} lighting", discovery["evidence"])
            _automation_save(data)
            await _automation_notify(suggestion["title"], detail)

async def _automation_delayed_area_discovery(area_id: str, delay: int = AUTOMATION_ROOM_OCCUPANCY_SECONDS) -> None:
    try:
        await asyncio.sleep(max(1, delay))
        await _automation_discover_area(area_id)
    finally:
        AUTOMATION_DISCOVERY_TASKS.pop(area_id, None)

async def _automation_brain_state_change(record: dict[str, Any]) -> None:
    if not automation_store()["settings"].get("passive_learning_enabled", True):
        return
    try:
        await _automation_refresh_area_context()
    except (RuntimeError, OSError, asyncio.TimeoutError):
        return
    discover_now = ""
    async with AUTOMATION_ENGINE_LOCK:
        data = automation_store()
        mapping = _automation_area_entity(data, str(record.get("entity_id") or ""))
        if not mapping or not mapping.get("area_id"):
            return
        _automation_record_behavior(data, record, mapping)
        _automation_save(data)
        area_id = str(mapping.get("area_id") or "")
        if mapping.get("role") == "room_presence":
            existing = AUTOMATION_DISCOVERY_TASKS.get(area_id)
            if _automation_state_positive(record.get("state")) and not (existing and not existing.done()):
                AUTOMATION_DISCOVERY_TASKS[area_id] = asyncio.create_task(
                    _automation_delayed_area_discovery(area_id),
                    name=f"zbrano-discovery-{area_id}",
                )
        elif mapping.get("role") in {"light", "illuminance"}:
            discover_now = area_id
    if discover_now:
        await _automation_discover_area(discover_now)

def _automation_condition_matches(item: dict[str, Any], old_state: Any, new_state: Any) -> bool:
    operator = str(item.get("trigger_operator") or "changes_to")
    expected = str(item.get("trigger_value") or "")
    old_text = "" if old_state is None else str(old_state)
    new_text = "" if new_state is None else str(new_state)
    if operator == "any_change":
        return old_text != new_text
    if operator == "changes_to":
        return old_text != new_text and new_text.casefold() == expected.casefold()
    if operator == "equals":
        return new_text.casefold() == expected.casefold()
    if operator == "not_equals":
        return new_text.casefold() != expected.casefold()
    try:
        current_number, expected_number = float(new_text), float(expected)
    except (TypeError, ValueError):
        return False
    return current_number > expected_number if operator == "above" else current_number < expected_number

def _automation_presence_confirmed(item: dict[str, Any], settings: dict[str, Any], expected_zone: str = "") -> tuple[bool, str]:
    if not settings.get("require_presence"):
        return True, "presence not required"
    entity_id = str(item.get("presence_entity") or settings.get("presence_entity") or "")
    if not entity_id:
        return False, "presence required but no presence entity is configured"
    state = ha_ws.state_cache.get(entity_id) or {}
    value = str(state.get("state") or "").casefold()
    accepted = {"on", "home", "present", "occupied", "true", "1"}
    expected = _automation_context_key(expected_zone.split(".", 1)[1] if expected_zone.startswith("zone.") else expected_zone)
    if expected and entity_id.split(".", 1)[0] in {"person", "device_tracker"}:
        zone = next((item for item in (automation_store().get("area_context") or {}).get("zones", []) if item.get("entity_id") == expected_zone), {})
        expected_values = {expected, _automation_context_key(zone.get("name"))}
        present = _automation_context_key(value) in expected_values
        return present, f"{entity_id}={value or 'unavailable'}; expected {expected_zone}"
    present = value in accepted
    return present, f"{entity_id}={value or 'unavailable'}"

def _automation_expected_zone(data: dict[str, Any], item: dict[str, Any]) -> str:
    for entity_id in (item.get("action_entity"), item.get("trigger_entity"), *(item.get("signal_entities") or [])):
        mapping = _automation_area_entity(data, str(entity_id or ""))
        if mapping.get("zone_entity_id"):
            return str(mapping["zone_entity_id"])
    return ""

def _automation_rate_available(item: dict[str, Any], now: float) -> tuple[bool, str]:
    cooldown = max(1, int(item.get("cooldown_minutes") or 30)) * 60
    if now - float(item.get("last_matched_at") or 0) < cooldown:
        return False, "cooldown active"
    history = [float(value) for value in item.get("action_history", []) if now - float(value) < 3600]
    item["action_history"] = history
    if len(history) >= max(1, int(item.get("max_actions_per_hour") or 2)):
        return False, "hourly action limit reached"
    return True, "rate limits clear"

def _automation_autonomous_allowed(item: dict[str, Any], settings: dict[str, Any]) -> tuple[bool, str]:
    if settings.get("operating_mode") != "selective_autonomy":
        return False, "global mode does not allow autonomous execution"
    if item.get("execution_policy") != "autonomous":
        return False, "automation is not marked autonomous"
    risk = str(item.get("risk_level") or "controlled")
    ceiling = str(settings.get("autonomous_risk_ceiling") or "low")
    if risk == "high" or AUTOMATION_RISK_ORDER.get(risk, 3) > AUTOMATION_RISK_ORDER.get(ceiling, 1):
        return False, "risk exceeds autonomous ceiling"
    if not item.get("reversible_only", True):
        return False, "autonomous action is not declared reversible"
    service = str(item.get("action_service") or "")
    domain = service.split(".", 1)[0] if "." in service else ""
    if domain not in AUTOMATION_AUTONOMOUS_DOMAINS:
        return False, "service domain is not allowed for autonomous execution"
    return True, "within autonomous authority"

async def _automation_notify(title: str, message: str, *, action: bool = False) -> None:
    notification = notification_store()
    settings = notification["settings"]
    target = str(settings.get("default_channel") or "")
    enabled = settings.get("autonomous_action_notifications" if action else "suggestion_notifications", True)
    if not target or not enabled or _notification_quiet_now("suggestion", time.time()):
        return
    with contextlib.suppress(HTTPException, RuntimeError, ValueError):
        await test_notification_channel(NotificationTestRequest(
            target=target, severity="suggestion", title=title, message=message,
        ))

async def _automation_execute_action(data: dict[str, Any], item: dict[str, Any], suggestion: dict[str, Any] | None, source: str) -> dict[str, Any]:
    service = str(item.get("action_service") or "")
    entity_id = str(item.get("action_entity") or "")
    if not service or not entity_id or "." not in service:
        raise RuntimeError("Automation has no complete Home Assistant action")
    access = effective_entity_access(entity_id)
    if not access or access == "read_only":
        raise RuntimeError("Automation action entity is not enabled for control")
    domain, action = service.split(".", 1)
    service_data = dict(item.get("action_service_data") or {})
    service_data["entity_id"] = entity_id
    now = time.time()
    item["last_matched_at"] = now
    item["last_triggered_at"] = now
    item["action_history"] = [*item.get("action_history", []), now][-60:]
    item["status"] = "executing"
    _automation_save(data)
    try:
        await ha_ws.call_service(domain, action, service_data)
    except Exception:
        item["status"] = "failed"
        _automation_event(data, "action_failed", f"Action failed: {item.get('name')}", f"{service} → {entity_id}")
        _automation_save(data)
        raise
    item["status"] = "armed"
    item["last_error"] = ""
    if suggestion is not None:
        suggestion["status"] = "executed"
        suggestion["resolved_at"] = time.time()
    _automation_event(data, "action", f"Automation action executed: {item.get('name')}", f"{service} → {entity_id}; source={source}")
    _automation_save(data)
    if item.get("notify_on_action", True):
        await _automation_notify(str(item.get("name") or "ZBRANO automation"), str(item.get("proposal_template") or f"Executed {service} for {entity_id}."), action=True)
    return {"executed": True, "service": service, "entity_id": entity_id}

async def _automation_commit_match(automation_id: str, evidence: dict[str, Any]) -> None:
    import secrets
    async with AUTOMATION_ENGINE_LOCK:
        data = automation_store()
        item = next((value for value in data["automations"] if value.get("id") == automation_id), None)
        if not item or not item.get("enabled"):
            return
        current = (ha_ws.state_cache.get(str(item.get("trigger_entity") or "")) or {}).get("state")
        if not _automation_condition_matches(item, evidence.get("old_state"), current):
            return
        now = time.time()
        rate_ok, rate_detail = _automation_rate_available(item, now)
        if not rate_ok:
            return
        presence_ok, presence_detail = _automation_presence_confirmed(item, data["settings"], _automation_expected_zone(data, item))
        if not presence_ok:
            item["last_suppressed_at"] = now
            item["status"] = "suppressed"
            _automation_event(data, "suppressed", f"Automation suppressed: {item.get('name')}", presence_detail)
            _automation_save(data)
            return
        item["last_matched_at"] = now
        confidence = 1.0
        detail = str(item.get("proposal_template") or item.get("objective") or "Automation condition matched.")
        evidence_text = f"{item.get('trigger_entity')} changed from {evidence.get('old_state')} to {current}; {presence_detail}; {rate_detail}"
        mode = str(data["settings"].get("operating_mode") or "suggest_only")
        policy = str(item.get("execution_policy") or "suggest")
        if mode == "observe_only" or policy == "observe":
            item["status"] = "observed"
            _automation_event(data, "observation", f"Condition observed: {item.get('name')}", evidence_text)
            _automation_save(data)
            return
        autonomous, authority_detail = _automation_autonomous_allowed(item, data["settings"])
        suggestion = {
            "id": secrets.token_hex(10), "automation_id": automation_id,
            "title": str(item.get("name") or "ZBRANO suggestion")[:160], "detail": detail[:1000],
            "evidence": evidence_text[:1000], "confidence": confidence,
            "status": "executing" if autonomous else "approval_required" if mode == "approval_gated" or policy == "approval_required" else "pending",
            "action_entity": str(item.get("action_entity") or ""), "action_service": str(item.get("action_service") or ""),
            "created_at": now,
        }
        data["suggestions"].insert(0, suggestion)
        item["status"] = suggestion["status"]
        _automation_event(data, "decision", f"Automation matched: {item.get('name')}", f"{evidence_text}; {authority_detail}")
        _automation_save(data)
        if autonomous:
            await _automation_execute_action(data, item, suggestion, "selective_autonomy")
        else:
            await _automation_notify(suggestion["title"], f"{detail}\n\nEvidence: {evidence_text}")

async def _automation_delayed_match(automation_id: str, evidence: dict[str, Any], delay: int) -> None:
    try:
        await asyncio.sleep(delay)
        await _automation_commit_match(automation_id, evidence)
    finally:
        AUTOMATION_PENDING_TASKS.pop(automation_id, None)

async def _automation_evaluate_state_change(event: dict[str, Any]) -> None:
    entity_id = str(event.get("entity_id") or "")
    data = automation_store()
    for item in data["automations"]:
        if item.get("kind") == "notification_watch" or not item.get("enabled") or str(item.get("trigger_entity") or "") != entity_id:
            continue
        matches = _automation_condition_matches(item, event.get("old_state"), event.get("state"))
        existing = AUTOMATION_PENDING_TASKS.get(str(item.get("id") or ""))
        if not matches:
            if existing and not existing.done():
                existing.cancel()
            continue
        delay = max(0, int(item.get("trigger_for_seconds") or 0))
        if delay:
            if existing and not existing.done():
                continue
            AUTOMATION_PENDING_TASKS[item["id"]] = asyncio.create_task(
                _automation_delayed_match(item["id"], event, delay),
                name=f"zbrano-automation-delay-{item['id']}",
            )
        else:
            await _automation_commit_match(item["id"], event)
