from __future__ import annotations

import asyncio
from pathlib import Path
import time
from typing import Any

from fastapi import HTTPException

from ..schemas import NotificationTestRequest, NotificationWatchRequest


def configure_notification_domain(
    *, plugin_load, plugin_save, entity_lister, ha_client,
    automation_store_fn, automation_event_fn, automation_save_fn,
    notification_test_fn, supervisor_token,
) -> None:
    global _plugin_load, _plugin_save, list_ha_entities, ha_ws
    global automation_store, _automation_event, _automation_save
    global test_notification_channel, SUPERVISOR_TOKEN
    _plugin_load = plugin_load
    _plugin_save = plugin_save
    list_ha_entities = entity_lister
    ha_ws = ha_client
    automation_store = automation_store_fn
    _automation_event = automation_event_fn
    _automation_save = automation_save_fn
    test_notification_channel = notification_test_fn
    SUPERVISOR_TOKEN = supervisor_token


NOTIFICATION_STORAGE_PATH = Path("/data/notification_center.json")

NOTIFICATION_DEFAULT_SETTINGS = {
    "default_channel": "",
    "suggestion_notifications": True,
    "autonomous_action_notifications": True,
    "quiet_hours_enabled": False,
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "07:00",
    "critical_override": True,
    "repeat_critical_minutes": 15,
}

def notification_store() -> dict[str, Any]:
    data = _plugin_load(NOTIFICATION_STORAGE_PATH) or {}
    settings = dict(NOTIFICATION_DEFAULT_SETTINGS)
    if isinstance(data.get("settings"), dict):
        settings.update(data["settings"])
    deliveries = data.get("deliveries") if isinstance(data.get("deliveries"), list) else []
    return {"settings": settings, "deliveries": deliveries[:100]}

def _notification_save(data: dict[str, Any]) -> None:
    data["deliveries"] = list(data.get("deliveries") or [])[:100]
    _plugin_save(NOTIFICATION_STORAGE_PATH, data)

def _notification_delivery(
    data: dict[str, Any], *, target: str, severity: str, title: str,
    status: str, detail: str = "",
) -> dict[str, Any]:
    import secrets

    delivery = {
        "id": secrets.token_hex(8),
        "target": str(target)[:255],
        "severity": str(severity)[:24],
        "title": str(title)[:120],
        "status": str(status)[:24],
        "detail": str(detail)[:500],
        "created_at": time.time(),
    }
    data.setdefault("deliveries", []).insert(0, delivery)
    return delivery

async def notification_channels() -> list[dict[str, Any]]:
    payload = await list_ha_entities()
    registry_platforms: dict[str, str] = {}
    try:
        registry = await ha_ws.command({"type": "config/entity_registry/list"})
        for entry in registry.get("result") or []:
            if isinstance(entry, dict) and entry.get("entity_id"):
                registry_platforms[str(entry["entity_id"])] = str(entry.get("platform") or "").lower()
    except (RuntimeError, OSError, asyncio.TimeoutError):
        pass

    channels = []
    for entity in payload.get("entities") or []:
        entity_id = str(entity.get("entity_id") or "")
        if not entity_id.startswith("notify."):
            continue
        friendly_name = str(entity.get("friendly_name") or entity_id)
        integration = registry_platforms.get(entity_id, "")
        identity = f"{integration} {entity_id} {friendly_name}".lower()
        platform = "telegram" if integration in {"telegram", "telegram_bot"} or "telegram" in identity else "home_assistant"
        channels.append({
            "entity_id": entity_id,
            "friendly_name": friendly_name,
            "platform": platform,
            "integration": integration or "unknown",
            "available": bool(entity.get("available")),
            "state": entity.get("state"),
            "icon": entity.get("icon"),
        })
    channels.sort(key=lambda item: (item["platform"] != "telegram", item["friendly_name"].lower()))
    return channels

def notification_watches(data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    store = data or automation_store()
    return [item for item in store.get("automations", []) if item.get("kind") == "notification_watch"]

def _notification_watch_payload(request: NotificationWatchRequest) -> dict[str, Any]:
    settings = notification_store()["settings"]
    destination = request.destination.strip().lower() or str(settings.get("default_channel") or "")
    if not destination:
        raise HTTPException(status_code=400, detail="Choose a default Notification Center channel or provide a destination")
    return {
        "kind": "notification_watch",
        "status": "armed" if request.enabled else "paused",
        "name": " ".join(request.name.split()),
        "objective": f"Notify when {request.entity_id} becomes {request.trigger_state.strip()}",
        "presence_entity": "",
        "signal_entities": [request.entity_id.strip().lower()],
        "context_notes": "Notification-only automation created from an explicit user request.",
        "proposal_template": request.message.strip(),
        "action_entity": destination,
        "action_service": "notify.send_message",
        "cooldown_minutes": request.cooldown_minutes,
        "confidence_threshold": 0.99,
        "risk_level": "informational" if request.severity in {"information", "suggestion"} else "controlled",
        "execution_policy": "autonomous",
        "notify_on_action": True,
        "reversible_only": True,
        "max_actions_per_hour": 60,
        "trigger_entity": request.entity_id.strip().lower(),
        "trigger_state": request.trigger_state.strip(),
        "destination": destination,
        "severity": request.severity,
        "title": request.title.strip() or "ZBRANO notification",
        "message": request.message.strip(),
        "active_start": request.active_start,
        "active_end": request.active_end,
        "one_shot": request.one_shot,
        "expires_at": request.expires_at,
        "enabled": request.enabled,
        "last_observed_state": None,
        "last_triggered_at": 0.0,
        "trigger_count": 0,
    }

def _notification_watch_key(watch: dict[str, Any]) -> tuple[str, str, str, str, str, bool]:
    return (
        str(watch.get("trigger_entity") or "").strip().lower(),
        str(watch.get("trigger_state") or "").strip().lower(),
        str(watch.get("destination") or "").strip().lower(),
        str(watch.get("active_start") or ""),
        str(watch.get("active_end") or ""),
        bool(watch.get("one_shot")),
    )

async def _create_notification_watch(request: NotificationWatchRequest, source: str = "interface") -> dict[str, Any]:
    import secrets

    data = automation_store()
    entity_id = request.entity_id.strip().lower()
    try:
        entity = await ha_ws.get_state(entity_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not entity:
        raise HTTPException(status_code=404, detail=f"Home Assistant entity not found: {entity_id}")
    channels = await notification_channels()
    destination = request.destination.strip().lower() or str(notification_store()["settings"].get("default_channel") or "")
    if not any(item["entity_id"] == destination for item in channels):
        raise HTTPException(status_code=400, detail="Notification destination is unavailable")

    now = time.time()
    payload = _notification_watch_payload(request)
    key = _notification_watch_key(payload)
    matches = [item for item in notification_watches(data) if _notification_watch_key(item) == key]
    if matches:
        watch = matches[0]
        runtime = {
            "id": watch.get("id") or secrets.token_hex(12),
            "created_at": float(watch.get("created_at") or now),
            "last_observed_state": watch.get("last_observed_state"),
            "last_triggered_at": float(watch.get("last_triggered_at") or 0.0),
            "trigger_count": int(watch.get("trigger_count") or 0),
        }
        watch.update(payload)
        watch.update(runtime)
        watch["updated_at"] = now
        watch["source"] = source
        data["automations"] = [
            item for item in data.get("automations", [])
            if item.get("kind") != "notification_watch" or _notification_watch_key(item) != key
        ]
        data["automations"].insert(0, watch)
        _automation_event(
            data, "notification_watch", f"Notification watch refreshed: {watch['name']}",
            f"Moved to first position; retained one rule and removed {max(0, len(matches) - 1)} older duplicate(s).",
        )
        _automation_save(data)
        return {"created": False, "deduplicated": len(matches), "watch": watch}

    if len(data["automations"]) >= 100:
        raise HTTPException(status_code=400, detail="Automation limit reached (100)")
    watch = {
        "id": secrets.token_hex(12),
        "created_at": now,
        "updated_at": now,
        "source": source,
        **payload,
    }
    data["automations"].insert(0, watch)
    _automation_event(data, "notification_watch", f"Notification watch armed: {watch['name']}", watch["objective"])
    _automation_save(data)
    return {"created": True, "deduplicated": 0, "watch": watch}

def _watch_time_active(watch: dict[str, Any], now: float) -> bool:
    start = str(watch.get("active_start") or "")
    end = str(watch.get("active_end") or "")
    if not start or not end:
        return True
    current = time.strftime("%H:%M", time.localtime(now))
    return start <= current <= end if start <= end else current >= start or current <= end

def _notification_quiet_now(severity: str, now: float) -> bool:
    settings = notification_store()["settings"]
    if not settings.get("quiet_hours_enabled"):
        return False
    if severity == "critical" and settings.get("critical_override", True):
        return False
    start = str(settings.get("quiet_hours_start") or "22:00")
    end = str(settings.get("quiet_hours_end") or "07:00")
    current = time.strftime("%H:%M", time.localtime(now))
    return start <= current <= end if start <= end else current >= start or current <= end

async def notification_watch_worker() -> None:
    while True:
        await asyncio.sleep(2.0)
        if not SUPERVISOR_TOKEN:
            continue
        if not ha_ws.connected:
            try:
                await ha_ws.connect()
            except RuntimeError:
                continue
        data = automation_store()
        changed = False
        now = time.time()
        for watch in notification_watches(data):
            if not watch.get("enabled"):
                continue
            expires_at = float(watch.get("expires_at") or 0)
            if expires_at and now >= expires_at:
                watch["enabled"] = False
                watch["status"] = "expired"
                watch["updated_at"] = now
                changed = True
                continue
            state = ha_ws.state_cache.get(str(watch.get("trigger_entity") or ""))
            if not state:
                if watch.get("status") != "unavailable":
                    watch["status"] = "unavailable"
                    changed = True
                continue
            current = str(state.get("state") or "")
            previous = watch.get("last_observed_state")
            if previous != current:
                watch["last_observed_state"] = current
                watch["updated_at"] = now
                changed = True
            if previous is None or previous == current or current != str(watch.get("trigger_state") or ""):
                if watch.get("status") == "unavailable":
                    watch["status"] = "armed"
                    changed = True
                continue
            if not _watch_time_active(watch, now):
                continue
            cooldown = max(0, int(watch.get("cooldown_minutes") or 0)) * 60
            if now - float(watch.get("last_triggered_at") or 0) < cooldown:
                continue
            if _notification_quiet_now(str(watch.get("severity") or "information"), now):
                notice = notification_store()
                _notification_delivery(
                    notice, target=str(watch.get("destination") or ""), severity=str(watch.get("severity") or "information"),
                    title=str(watch.get("title") or "ZBRANO notification"), status="suppressed", detail="Matched during configured quiet hours",
                )
                _notification_save(notice)
                watch["last_triggered_at"] = now
                changed = True
                continue
            try:
                await test_notification_channel(NotificationTestRequest(
                    target=str(watch.get("destination") or ""),
                    severity=str(watch.get("severity") or "information"),
                    title=str(watch.get("title") or "ZBRANO notification"),
                    message=str(watch.get("message") or watch.get("objective") or "Notification condition matched."),
                ))
                watch["last_triggered_at"] = now
                watch["trigger_count"] = int(watch.get("trigger_count") or 0) + 1
                watch["status"] = "triggered" if watch.get("one_shot") else "armed"
                if watch.get("one_shot"):
                    watch["enabled"] = False
                watch["updated_at"] = now
                _automation_event(data, "notification", f"Notification delivered: {watch.get('name')}", str(watch.get("destination") or ""))
                changed = True
            except (HTTPException, RuntimeError, ValueError) as exc:
                watch["status"] = "failed"
                watch["last_error"] = str(getattr(exc, "detail", exc))[:500]
                watch["updated_at"] = now
                changed = True
        if changed:
            _automation_save(data)
