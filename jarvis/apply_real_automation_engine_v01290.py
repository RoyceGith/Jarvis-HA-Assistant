import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.90 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.90 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        '''    max_actions_per_hour: int = Field(default=2, ge=1, le=60)


class NotificationCenterSettingsRequest''',
        '''    max_actions_per_hour: int = Field(default=2, ge=1, le=60)
    enabled: bool = False
    trigger_entity: str = Field(default="", max_length=255, pattern=r"^(|[a-z0-9_]+\\.[a-z0-9_]+)$")
    trigger_operator: str = Field(default="changes_to", pattern="^(any_change|changes_to|equals|not_equals|above|below)$")
    trigger_value: str = Field(default="", max_length=255)
    trigger_for_seconds: int = Field(default=0, ge=0, le=86400)
    action_service_data: dict[str, Any] = Field(default_factory=dict)


class NotificationCenterSettingsRequest''',
        "structured automation request fields",
    )

    backend = replace_once(
        backend,
        '''                    elif isinstance(new_state, dict):
                        self.state_cache[entity_id] = new_state
        except asyncio.CancelledError:''',
        '''                    elif isinstance(new_state, dict):
                        self.state_cache[entity_id] = new_state
                    _dispatch_ha_state_changed(event)
        except asyncio.CancelledError:''',
        "Home Assistant live-event dispatch",
    )

    history_repair = r'''HA_LIVE_EVENTS: deque[dict[str, Any]] = deque(maxlen=500)
HA_EVENT_TASKS: set[asyncio.Task[Any]] = set()


def _dispatch_ha_state_changed(event: dict[str, Any]) -> None:
    data = event.get("data") or {}
    entity_id = str(data.get("entity_id") or "").lower()
    old_state = data.get("old_state") if isinstance(data.get("old_state"), dict) else {}
    new_state = data.get("new_state") if isinstance(data.get("new_state"), dict) else {}
    if not entity_id or not effective_entity_access(entity_id):
        return
    old_value = None if not old_state else str(old_state.get("state") or "")
    new_value = None if not new_state else str(new_state.get("state") or "")
    if old_value == new_value and old_state.get("attributes") == new_state.get("attributes"):
        return
    attributes = new_state.get("attributes") or old_state.get("attributes") or {}
    record = {
        "when": str(event.get("time_fired") or new_state.get("last_updated") or new_state.get("last_changed") or ""),
        "entity_id": entity_id,
        "name": str(attributes.get("friendly_name") or entity_id),
        "old_state": old_value,
        "state": new_value,
        "message": f"state changed from {old_value if old_value is not None else 'not present'} to {new_value if new_value is not None else 'removed'}",
        "source": "live",
        "context_id": str((event.get("context") or {}).get("id") or ""),
    }
    HA_LIVE_EVENTS.appendleft(record)
    try:
        task = asyncio.create_task(_automation_evaluate_state_change(record), name=f"zbrano-automation-{entity_id}")
    except RuntimeError:
        return
    HA_EVENT_TASKS.add(task)
    task.add_done_callback(HA_EVENT_TASKS.discard)


def _ha_live_events(entity_ids: list[str], hours: int, limit: int) -> list[dict[str, Any]]:
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, min(HA_HISTORY_MAX_HOURS, hours)))
    allowed = set(entity_ids)
    result: list[dict[str, Any]] = []
    for event in HA_LIVE_EVENTS:
        if event.get("entity_id") not in allowed:
            continue
        try:
            moment = datetime.fromisoformat(str(event.get("when") or "").replace("Z", "+00:00"))
        except ValueError:
            continue
        if moment < cutoff:
            continue
        result.append(dict(event))
        if len(result) >= limit:
            break
    return result


async def get_home_assistant_history(entity_ids: Any, hours: int = 24, max_points: int = 80) -> dict[str, Any]:
    """Recorder history mapped by entity ID and augmented with immediate live events."""
    from urllib.parse import quote
    entities = _ha_history_entities(entity_ids)
    if not SUPERVISOR_TOKEN:
        raise RuntimeError("Home Assistant API token unavailable")
    start, end, bounded_hours = _ha_history_bounds(hours)
    headers = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}", "Content-Type": "application/json"}
    path = f"{HA_API_BASE}/history/period/{quote(start.isoformat(), safe='')}"
    params = {
        "filter_entity_id": ",".join(entities), "end_time": end.isoformat(),
        "minimal_response": "", "no_attributes": "", "significant_changes_only": "",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(path, headers=headers, params=params)
    if response.is_error:
        raise RuntimeError(f"Home Assistant history returned HTTP {response.status_code}: {response.text[:300]}")
    payload = response.json()
    if not isinstance(payload, list):
        raise RuntimeError("Home Assistant history returned an unexpected response")
    raw_by_entity: dict[str, list[dict[str, Any]]] = {}
    for raw_series in payload:
        if not isinstance(raw_series, list):
            continue
        identity = next((str(item.get("entity_id") or "").lower() for item in raw_series if isinstance(item, dict) and item.get("entity_id")), "")
        if identity:
            raw_by_entity[identity] = raw_series
    metadata_results = await asyncio.gather(*(ha_get_state(entity_id) for entity_id in entities), return_exceptions=True)
    metadata = {entity_id: value if isinstance(value, dict) else {} for entity_id, value in zip(entities, metadata_results)}
    live = _ha_live_events(entities, bounded_hours, HA_HISTORY_MAX_EVENTS)
    live_by_entity: dict[str, list[dict[str, Any]]] = {entity_id: [] for entity_id in entities}
    for event in live:
        if event.get("state") is not None:
            live_by_entity[event["entity_id"]].append({
                "entity_id": event["entity_id"], "state": event["state"], "last_changed": event["when"],
            })
    series: list[dict[str, Any]] = []
    for entity_id in entities:
        combined = list(raw_by_entity.get(entity_id, [])) + live_by_entity.get(entity_id, [])
        points = _ha_history_normalize_series(combined, entity_id)
        deduped = list({(point["last_changed"], point["state"]): point for point in points}.values())
        deduped.sort(key=lambda item: item["last_changed"])
        if not deduped and isinstance(metadata.get(entity_id), dict) and metadata[entity_id].get("state") is not None:
            deduped = [{
                "entity_id": entity_id,
                "state": str(metadata[entity_id].get("state")),
                "last_changed": str(metadata[entity_id].get("last_changed") or end.isoformat()),
            }]
        series.append({
            "entity_id": entity_id,
            "summary": _ha_history_summary(entity_id, deduped, metadata.get(entity_id)),
            "points": _ha_history_downsample(deduped, max_points),
            "raw_point_count": len(deduped),
        })
    return {
        "read_only": True, "hours": bounded_hours, "start": start.isoformat(), "end": end.isoformat(),
        "entity_count": len(entities), "series": series, "live_event_count": len(live),
        "limits": {"entities": HA_HISTORY_MAX_ENTITIES, "hours": HA_HISTORY_MAX_HOURS, "points_per_entity": HA_HISTORY_MAX_POINTS},
    }


async def correlate_home_assistant_timeline(entity_ids: Any, hours: int = 24, query: str = "", limit: int = 160) -> dict[str, Any]:
    entities = _ha_history_entities(entity_ids)
    bounded_limit = max(10, min(HA_HISTORY_MAX_EVENTS, int(limit or 160)))
    results = await asyncio.gather(
        get_home_assistant_history(entities, hours, min(120, bounded_limit)),
        search_home_assistant_logbook(entities, hours, query, bounded_limit),
        return_exceptions=True,
    )
    history_result, logbook_result = results
    if isinstance(history_result, Exception):
        raise history_result
    warnings: list[str] = []
    if isinstance(logbook_result, Exception):
        warnings.append(f"Logbook unavailable: {str(logbook_result)[:240]}")
        logbook_events: list[dict[str, Any]] = []
    else:
        logbook_events = list(logbook_result.get("events") or [])
    events = logbook_events + _ha_live_events(entities, int(history_result["hours"]), bounded_limit)
    for series in history_result["series"]:
        for point in series["points"]:
            events.append({
                "when": point["last_changed"], "entity_id": series["entity_id"],
                "name": series["summary"].get("friendly_name"), "message": f"state changed to {point['state']}",
                "state": point["state"], "source": "history",
            })
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for event in events:
        identity = (str(event.get("when") or ""), str(event.get("entity_id") or ""), str(event.get("state") or event.get("message") or ""))
        existing = unique.get(identity)
        if existing is None or event.get("source") == "live":
            unique[identity] = event
    events = sorted(unique.values(), key=lambda item: str(item.get("when") or ""), reverse=True)[:bounded_limit]
    return {
        "read_only": True, "hours": history_result["hours"], "start": history_result["start"], "end": history_result["end"],
        "entity_count": history_result["entity_count"], "series": history_result["series"], "events": events,
        "correlation_windows": _ha_correlation_windows(events), "event_count": len(events),
        "live_event_count": history_result.get("live_event_count", 0), "warnings": warnings,
        "truncated": len(events) >= bounded_limit,
    }


@app.get("/api/ha/live-events")
async def api_home_assistant_live_events(limit: int = 100) -> dict[str, Any]:
    bounded = max(1, min(300, int(limit or 100)))
    events = [dict(item) for item in list(HA_LIVE_EVENTS)[:bounded]]
    return {"read_only": True, "events": events, "count": len(events), "connected": ha_ws.connected}


'''
    backend = replace_once(
        backend,
        "async def ha_get_state_rest(entity_id: str) -> dict[str, Any]:\n",
        history_repair + "async def ha_get_state_rest(entity_id: str) -> dict[str, Any]:\n",
        "resilient live History implementation",
    )

    backend = replace_once(
        backend,
        '''    payload["action_service"] = payload["action_service"].strip()
    return payload''',
        '''    payload["action_service"] = payload["action_service"].strip().lower()
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
    if payload["action_service"] and not re.fullmatch(r"[a-z0-9_]+\\.[a-z0-9_]+", payload["action_service"]):
        raise HTTPException(status_code=400, detail="Action service must use domain.service format")
    if len(json.dumps(payload["action_service_data"], ensure_ascii=False)) > 4000:
        raise HTTPException(status_code=400, detail="Action service data is too large")
    return payload''',
        "automation payload validation",
    )
    backend = backend.replace(
        'payload["presence_entity"] = payload["presence_entity"].strip()',
        'payload["presence_entity"] = payload["presence_entity"].strip().lower()',
        1,
    )
    backend = backend.replace(
        'str(value).strip()[:255] for value in payload["signal_entities"]',
        'str(value).strip().lower()[:255] for value in payload["signal_entities"]',
        1,
    )
    backend = backend.replace(
        'payload["action_entity"] = payload["action_entity"].strip()',
        'payload["action_entity"] = payload["action_entity"].strip().lower()',
        1,
    )

    backend = replace_once(
        backend,
        '''        "engine": {
            "status": "foundation_ready",
            "continuous_monitoring": False,
            "context_reasoning": False,
            "automatic_execution": False,
            "message": "Automation workspace ready; continuous evaluator is not implemented yet.",
        },''',
        '''        "engine": {
            "status": "active" if ha_ws.connected else "waiting_for_home_assistant",
            "continuous_monitoring": True,
            "context_reasoning": True,
            "automatic_execution": data["settings"].get("operating_mode") == "selective_autonomy",
            "live_event_count": len(HA_LIVE_EVENTS),
            "pending_evaluations": sum(not task.done() for task in AUTOMATION_PENDING_TASKS.values()),
            "message": "Event-driven evaluator active; no AI model is called while idle.",
        },''',
        "active automation engine status",
    )

    backend = backend.replace(
        "f\"Mode: {settings['operating_mode']}; execution engine remains inactive in this version.\"",
        "f\"Mode: {settings['operating_mode']}; event-driven evaluator active.\"",
        1,
    )
    backend = backend.replace(
        '"id": secrets.token_hex(12), "status": "draft",',
        '"id": secrets.token_hex(12), "status": "armed" if request.enabled else "draft",',
        1,
    )
    backend = backend.replace(
        '    automation["status"] = "draft"\n    _automation_event(data, "draft", f"Draft updated: {automation[\'name\']}")',
        '    automation["status"] = "armed" if automation.get("enabled") else "draft"\n    _automation_event(data, "configuration", f"Automation updated: {automation[\'name\']}", automation["status"])',
        1,
    )
    backend = backend.replace(
        '''f"{len(payload.get('automations', [])) if isinstance(payload, dict) else 0} automation drafts; evaluator intentionally inactive"''',
        '''f"{len(payload.get('automations', [])) if isinstance(payload, dict) else 0} automation definitions; event-driven evaluator={payload.get('engine', {}).get('status', 'unavailable') if isinstance(payload, dict) else 'unavailable'}"''',
        1,
    )
    backend = backend.replace(
        '''lambda p: (isinstance(p.get("automations"), list) and p.get("engine", {}).get("status") == "foundation_ready", f"{len(p.get('automations', []))} drafts; evaluator inactive by design")''',
        '''lambda p: (isinstance(p.get("automations"), list) and p.get("engine", {}).get("status") in {"active", "waiting_for_home_assistant"}, f"{len(p.get('automations', []))} definitions; evaluator={p.get('engine', {}).get('status', 'unavailable')}")''',
        1,
    )

    engine_backend = r'''AUTOMATION_ENGINE_LOCK = asyncio.Lock()
AUTOMATION_PENDING_TASKS: dict[str, asyncio.Task[Any]] = {}
AUTOMATION_RISK_ORDER = {"informational": 0, "low": 1, "controlled": 2, "high": 3}
AUTOMATION_AUTONOMOUS_DOMAINS = {"light", "switch", "fan", "media_player", "climate"}


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


def _automation_presence_confirmed(item: dict[str, Any], settings: dict[str, Any]) -> tuple[bool, str]:
    if not settings.get("require_presence"):
        return True, "presence not required"
    entity_id = str(item.get("presence_entity") or settings.get("presence_entity") or "")
    if not entity_id:
        return False, "presence required but no presence entity is configured"
    state = ha_ws.state_cache.get(entity_id) or {}
    value = str(state.get("state") or "").casefold()
    present = value in {"on", "home", "present", "occupied", "true", "1"}
    return present, f"{entity_id}={value or 'unavailable'}"


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
        presence_ok, presence_detail = _automation_presence_confirmed(item, data["settings"])
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


@app.post("/api/automations/suggestions/{suggestion_id}/approve")
async def approve_automation_suggestion(suggestion_id: str) -> dict[str, Any]:
    async with AUTOMATION_ENGINE_LOCK:
        data = automation_store()
        suggestion = next((item for item in data["suggestions"] if item.get("id") == suggestion_id), None)
        if not suggestion or suggestion.get("status") not in {"pending", "approval_required"}:
            raise HTTPException(status_code=404, detail="Pending automation suggestion not found")
        automation = next((item for item in data["automations"] if item.get("id") == suggestion.get("automation_id")), None)
        if not automation:
            raise HTTPException(status_code=404, detail="Automation definition not found")
        try:
            result = await _automation_execute_action(data, automation, suggestion, "explicit_approval")
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Automation action failed: {exc}") from exc
        return {**result, "suggestion": suggestion}


@app.post("/api/automations/suggestions/{suggestion_id}/dismiss")
async def dismiss_automation_suggestion(suggestion_id: str) -> dict[str, Any]:
    data = automation_store()
    suggestion = next((item for item in data["suggestions"] if item.get("id") == suggestion_id), None)
    if not suggestion or suggestion.get("status") not in {"pending", "approval_required"}:
        raise HTTPException(status_code=404, detail="Pending automation suggestion not found")
    suggestion["status"] = "dismissed"
    suggestion["resolved_at"] = time.time()
    _automation_event(data, "dismissed", f"Suggestion dismissed: {suggestion.get('title')}")
    _automation_save(data)
    return {"dismissed": True, "suggestion": suggestion}


'''
    backend = replace_once(
        backend,
        'NOTIFICATION_STORAGE_PATH = Path("/data/notification_center.json")\n',
        engine_backend + 'NOTIFICATION_STORAGE_PATH = Path("/data/notification_center.json")\n',
        "Real Automation Engine backend",
    )

    frontend = frontend.replace(
        "FOUNDATION READY · EVALUATOR INACTIVE",
        "LIVE EVENT ENGINE",
        1,
    )
    frontend = frontend.replace(
        "<strong>Current capability:</strong> Continuous monitoring and action execution are not active in this version. Drafts may define observe-only, suggest-only, approval-required, or fully autonomous future behavior.",
        "<strong>Current capability:</strong> Live Home Assistant events are evaluated without AI polling. Existing drafts remain disabled until you add a structured trigger and explicitly enable them.",
        1,
    )
    frontend = frontend.replace(
        '<article><span>Engine</span><strong id="autonomy-engine-status">Foundation ready</strong><small>Continuous evaluator not active</small></article>',
        '<article><span>Engine</span><strong id="autonomy-engine-status">Waiting</strong><small>Event-driven · no idle AI usage</small></article>',
        1,
    )
    frontend = frontend.replace(
        "Future proactive recommendations will include evidence, confidence, proposed action, and safety impact.",
        "Live recommendations include the triggering evidence, confidence, proposed action, and authority decision.",
        1,
    )
    frontend = frontend.replace(
        "No suggestions yet. ZBRANO will never invent activity before the evaluator is implemented.",
        "No live automation suggestions yet.",
    )
    frontend = frontend.replace(
        "Current Home Assistant states referenced by your drafts. This is a manual snapshot, not continuous monitoring.",
        "Current Home Assistant states referenced by enabled and draft automations.",
        1,
    )
    frontend = frontend.replace(
        "Templates prefill a draft; they do not activate monitoring or control devices.",
        "Templates prefill a disabled rule. Review its entities, trigger, action, and authority before enabling it.",
        1,
    )
    frontend = frontend.replace(
        "Describe the intent and evidence. The future evaluator will implement the reasoning code separately.",
        "Define a deterministic trigger, evidence context, and authority. Disabled rules never evaluate or act.",
        1,
    )
    frontend = frontend.replace(
        "Drafts are persistent design specifications. None are evaluated in v0.12.10.",
        "Disabled rules remain drafts; enabled rules are evaluated from live Home Assistant state changes.",
        1,
    )
    frontend = frontend.replace(
        "Configuration changes appear now. Future observations, suppressed suggestions, approvals, actions, and outcomes will be auditable here.",
        "Observations, suppressions, suggestions, approvals, autonomous actions, failures, and configuration changes are recorded here.",
        1,
    )

    frontend = replace_once(
        frontend,
        '''                <label>Signal entities<input id="automation-signals" maxlength="1500" placeholder="sensor.workshop_temperature, sensor.outdoor_temperature"></label>
                <label class="wide">Context and baseline strategy''',
        '''                <label>Signal entities<input id="automation-signals" maxlength="1500" placeholder="sensor.workshop_temperature, sensor.outdoor_temperature"></label>
                <label>Trigger entity<input id="automation-trigger-entity" list="automation-entity-options" maxlength="255" placeholder="sensor.workshop_temperature"></label>
                <label>Trigger condition<select id="automation-trigger-operator"><option value="any_change">Any state change</option><option value="changes_to" selected>Changes to</option><option value="equals">Equals</option><option value="not_equals">Does not equal</option><option value="above">Above</option><option value="below">Below</option></select></label>
                <label>Trigger value<input id="automation-trigger-value" maxlength="255" placeholder="on or 28"></label>
                <label>Sustain condition (seconds)<input id="automation-trigger-for" type="number" min="0" max="86400" value="0"></label>
                <label class="check wide"><input id="automation-enabled" type="checkbox"> Enable live evaluation after saving</label>
                <label class="wide">Context and baseline strategy''',
        "structured automation trigger editor",
    )
    frontend = replace_once(
        frontend,
        '''                <label>Proposed HA service<input id="automation-action-service" maxlength="120" placeholder="climate.set_hvac_mode"></label>
                <label>Cooldown''',
        '''                <label>Proposed HA service<input id="automation-action-service" maxlength="120" placeholder="climate.set_hvac_mode"></label>
                <label class="wide">Action service data (JSON)<textarea id="automation-action-data" rows="2" maxlength="4000" placeholder='{"hvac_mode":"cool"}'>{}</textarea></label>
                <label>Cooldown''',
        "automation action data editor",
    )

    frontend = replace_once(
        frontend,
        '''  function renderSummary(){
    $("autonomy-engine-status").textContent=state.engine?.status==="foundation_ready"?"Foundation ready":"Unavailable";''',
        '''  function renderSummary(){
    $("autonomy-engine-status").textContent=state.engine?.status==="active"?"Live":state.engine?.status==="waiting_for_home_assistant"?"Waiting for HA":"Unavailable";''',
        "live engine frontend status",
    )

    old_suggestions = '''  function renderSuggestions(){
    const root=$("autonomy-suggestions");root.replaceChildren();
    if(!state.suggestions.length){root.innerHTML='<div class="autonomy-empty">No live automation suggestions yet.</div>';return}
    for(const item of state.suggestions){const row=document.createElement("div");row.className="autonomy-draft";row.innerHTML=`<strong>${esc(item.title||"Suggestion")}</strong><span>${esc(item.detail||"")}</span>`;root.appendChild(row)}
  }'''
    new_suggestions = '''  function renderSuggestions(){
    const root=$("autonomy-suggestions");root.replaceChildren();
    const visible=(state.suggestions||[]).filter(item=>!["dismissed"].includes(item.status)).slice(0,30);
    if(!visible.length){root.innerHTML='<div class="autonomy-empty">No live automation suggestions yet.</div>';return}
    for(const item of visible){const row=document.createElement("div");row.className="autonomy-draft";const actionable=["pending","approval_required"].includes(item.status)&&item.action_service&&item.action_entity;const actions=actionable?`<div class="autonomy-draft-actions"><button type="button" data-suggestion-approve="${esc(item.id)}">Approve action</button><button type="button" data-suggestion-dismiss="${esc(item.id)}">Dismiss</button></div>`:"";row.innerHTML=`<div class="autonomy-draft-head"><strong>${esc(item.title||"Suggestion")}</strong><span class="automation-state" data-state="${esc(item.status||"pending")}">${esc(item.status||"pending")}</span></div><span>${esc(item.detail||"")}</span>${item.evidence?`<small>Evidence: ${esc(item.evidence)}</small>`:""}${actions}`;root.appendChild(row)}
  }'''
    frontend = replace_once(frontend, old_suggestions, new_suggestions, "actionable suggestion inbox")

    frontend = frontend.replace(
        'const tags=[isWatch?(item.status||"armed"):"Draft",authorityLabel(item.execution_policy)',
        'const tags=[isWatch?(item.status||"armed"):(item.enabled?(item.status||"armed"):"Disabled"),authorityLabel(item.execution_policy)',
        1,
    )

    old_clear = '''    $("automation-draft-form").reset();$("automation-edit-id").value="";$("automation-editor-title").textContent="New automation draft";$("automation-cancel-edit").hidden=true;$("automation-cooldown").value=String(state.settings?.default_cooldown_minutes||30);$("automation-confidence").value=String(state.settings?.minimum_confidence||0.75);$("automation-risk").value="controlled";$("automation-execution-policy").value="suggest";$("automation-max-actions").value="2";$("automation-notify-action").checked=true;$("automation-reversible-only").checked=true;$("automation-draft-state").textContent="";'''
    new_clear = '''    $("automation-draft-form").reset();$("automation-edit-id").value="";$("automation-editor-title").textContent="New automation draft";$("automation-cancel-edit").hidden=true;$("automation-cooldown").value=String(state.settings?.default_cooldown_minutes||30);$("automation-confidence").value=String(state.settings?.minimum_confidence||0.75);$("automation-risk").value="controlled";$("automation-execution-policy").value="suggest";$("automation-max-actions").value="2";$("automation-trigger-operator").value="changes_to";$("automation-trigger-for").value="0";$("automation-action-data").value="{}";$("automation-enabled").checked=false;$("automation-notify-action").checked=true;$("automation-reversible-only").checked=true;$("automation-draft-state").textContent="";'''
    frontend = replace_once(frontend, old_clear, new_clear, "automation editor reset")

    old_fill = '''    $("automation-edit-id").value=item.id||"";$("automation-name").value=item.name||"";$("automation-objective").value=item.objective||"";$("automation-presence").value=item.presence_entity||"";$("automation-signals").value=(item.signal_entities||[]).join(", ");$("automation-context-notes").value=item.context_notes||"";$("automation-proposal").value=item.proposal_template||"";$("automation-action-entity").value=item.action_entity||"";$("automation-action-service").value=item.action_service||"";$("automation-cooldown").value=String(item.cooldown_minutes||30);$("automation-confidence").value=String(item.confidence_threshold||0.75);$("automation-risk").value=item.risk_level||"controlled";$("automation-execution-policy").value=item.execution_policy||"suggest";$("automation-max-actions").value=String(item.max_actions_per_hour||2);$("automation-notify-action").checked=item.notify_on_action!==false;$("automation-reversible-only").checked=item.reversible_only!==false;$("automation-editor-title").textContent=item.id?"Edit automation draft":"New automation draft";$("automation-cancel-edit").hidden=!item.id;showView("library");$("automation-name").focus();'''
    new_fill = '''    $("automation-edit-id").value=item.id||"";$("automation-name").value=item.name||"";$("automation-objective").value=item.objective||"";$("automation-presence").value=item.presence_entity||"";$("automation-signals").value=(item.signal_entities||[]).join(", ");$("automation-trigger-entity").value=item.trigger_entity||(item.signal_entities||[])[0]||"";$("automation-trigger-operator").value=item.trigger_operator||"changes_to";$("automation-trigger-value").value=item.trigger_value||"";$("automation-trigger-for").value=String(item.trigger_for_seconds||0);$("automation-enabled").checked=Boolean(item.enabled);$("automation-context-notes").value=item.context_notes||"";$("automation-proposal").value=item.proposal_template||"";$("automation-action-entity").value=item.action_entity||"";$("automation-action-service").value=item.action_service||"";$("automation-action-data").value=JSON.stringify(item.action_service_data||{},null,2);$("automation-cooldown").value=String(item.cooldown_minutes||30);$("automation-confidence").value=String(item.confidence_threshold||0.75);$("automation-risk").value=item.risk_level||"controlled";$("automation-execution-policy").value=item.execution_policy||"suggest";$("automation-max-actions").value=String(item.max_actions_per_hour||2);$("automation-notify-action").checked=item.notify_on_action!==false;$("automation-reversible-only").checked=item.reversible_only!==false;$("automation-editor-title").textContent=item.id?"Edit automation":"New automation";$("automation-cancel-edit").hidden=!item.id;showView("library");$("automation-name").focus();'''
    frontend = replace_once(frontend, old_fill, new_fill, "automation editor population")

    frontend = replace_once(
        frontend,
        r'''    const body={name:$("automation-name").value.trim(),objective:$("automation-objective").value.trim(),presence_entity:$("automation-presence").value.trim(),signal_entities:$("automation-signals").value.split(/[,\n]/).map(v=>v.trim()).filter(Boolean),context_notes:$("automation-context-notes").value.trim(),proposal_template:$("automation-proposal").value.trim(),action_entity:$("automation-action-entity").value.trim(),action_service:$("automation-action-service").value.trim(),cooldown_minutes:Number($("automation-cooldown").value),confidence_threshold:Number($("automation-confidence").value),risk_level:$("automation-risk").value,execution_policy:$("automation-execution-policy").value,notify_on_action:$("automation-notify-action").checked,reversible_only:$("automation-reversible-only").checked,max_actions_per_hour:Number($("automation-max-actions").value)};''',
        r'''    let actionData={};try{actionData=JSON.parse($("automation-action-data").value||"{}");if(!actionData||Array.isArray(actionData)||typeof actionData!=="object")throw new Error("must be an object")}catch(error){status.textContent=`Action data must be valid JSON: ${error.message||error}`;return}
    const body={name:$("automation-name").value.trim(),objective:$("automation-objective").value.trim(),presence_entity:$("automation-presence").value.trim(),signal_entities:$("automation-signals").value.split(/[,\n]/).map(v=>v.trim()).filter(Boolean),trigger_entity:$("automation-trigger-entity").value.trim(),trigger_operator:$("automation-trigger-operator").value,trigger_value:$("automation-trigger-value").value.trim(),trigger_for_seconds:Number($("automation-trigger-for").value||0),enabled:$("automation-enabled").checked,context_notes:$("automation-context-notes").value.trim(),proposal_template:$("automation-proposal").value.trim(),action_entity:$("automation-action-entity").value.trim(),action_service:$("automation-action-service").value.trim(),action_service_data:actionData,cooldown_minutes:Number($("automation-cooldown").value),confidence_threshold:Number($("automation-confidence").value),risk_level:$("automation-risk").value,execution_policy:$("automation-execution-policy").value,notify_on_action:$("automation-notify-action").checked,reversible_only:$("automation-reversible-only").checked,max_actions_per_hour:Number($("automation-max-actions").value)};''',
        "structured automation save payload",
    )

    frontend = replace_once(
        frontend,
        '''    const notificationWatch=event.target.closest("[data-auto-watch]");if(notificationWatch){showView("notifications");window.zbranoNotificationCenter?.showView("watchlist");window.zbranoNotificationCenter?.load();return}
    const edit=event.target.closest("[data-auto-edit]");''',
        '''    const notificationWatch=event.target.closest("[data-auto-watch]");if(notificationWatch){showView("notifications");window.zbranoNotificationCenter?.showView("watchlist");window.zbranoNotificationCenter?.load();return}
    const approve=event.target.closest("[data-suggestion-approve]");if(approve){approve.disabled=true;try{await api(`api/automations/suggestions/${encodeURIComponent(approve.dataset.suggestionApprove)}/approve`,{method:"POST"});await loadWorkspace()}catch(error){alert(`Action failed: ${error.message||error}`);approve.disabled=false}return}
    const dismiss=event.target.closest("[data-suggestion-dismiss]");if(dismiss){dismiss.disabled=true;try{await api(`api/automations/suggestions/${encodeURIComponent(dismiss.dataset.suggestionDismiss)}/dismiss`,{method:"POST"});await loadWorkspace()}catch(error){alert(`Dismiss failed: ${error.message||error}`);dismiss.disabled=false}return}
    const edit=event.target.closest("[data-auto-edit]");''',
        "suggestion decision controls",
    )

    frontend = replace_once(
        frontend,
        '''      const editAction = canEdit ? `<button class="calendar-edit-reminders" type="button" data-calendar-edit-reminders="${esc(item.id)}">Edit reminders</button>` : "";
      node.innerHTML = `<div class="calendar-appointment-head"><div><div class="calendar-appointment-title">${esc(item.title)}</div><div class="calendar-appointment-time">${esc(time)}</div></div>${editAction}</div><div class="calendar-meta">${meta.map(value => `<span>${esc(value)}</span>`).join("")}<span class="calendar-reminder-state" data-state="${esc(reminderSummary.state)}">${esc(reminderSummary.label)}</span></div>${item.notes ? `<div>${esc(item.notes)}</div>` : ""}<div class="calendar-reminder-badges">${(item.reminders || []).map(reminderBadge).join("") || '<span class="muted">No reminders</span>'}</div>`;''',
        '''      const editAction = canEdit ? `<button class="calendar-edit-reminders" type="button" data-calendar-edit-reminders="${esc(item.id)}">Edit reminders</button>` : "";
      const deleteAction = `<button class="calendar-cancel calendar-month-delete" type="button" data-calendar-month-delete="${esc(item.id)}">Delete</button>`;
      node.innerHTML = `<div class="calendar-appointment-head"><div><div class="calendar-appointment-title">${esc(item.title)}</div><div class="calendar-appointment-time">${esc(time)}</div></div><div class="calendar-appointment-actions">${editAction}${deleteAction}</div></div><div class="calendar-meta">${meta.map(value => `<span>${esc(value)}</span>`).join("")}<span class="calendar-reminder-state" data-state="${esc(reminderSummary.state)}">${esc(reminderSummary.label)}</span></div>${item.notes ? `<div>${esc(item.notes)}</div>` : ""}<div class="calendar-reminder-badges">${(item.reminders || []).map(reminderBadge).join("") || '<span class="muted">No reminders</span>'}</div>`;''',
        "Month selected-day appointment delete control",
    )
    frontend = replace_once(
        frontend,
        '''  $("calendar-day-appointments").addEventListener("click", event => {
    const edit = event.target.closest("[data-calendar-edit-reminders]");
    if (edit) openReminderEditor(edit.dataset.calendarEditReminders);
  });''',
        '''  $("calendar-day-appointments").addEventListener("click", async event => {
    const edit = event.target.closest("[data-calendar-edit-reminders]");
    if (edit) { openReminderEditor(edit.dataset.calendarEditReminders); return; }
    const remove = event.target.closest("[data-calendar-month-delete]");
    if (!remove || !confirm("Delete this appointment and cancel its pending reminders?")) return;
    remove.disabled = true;
    try { await api(`api/calendar/${encodeURIComponent(remove.dataset.calendarMonthDelete)}`, {method:"DELETE"}); await loadCalendar(); }
    catch (error) { $("calendar-month-summary").textContent = `Delete failed: ${error.message || error}`; }
    finally { remove.disabled = false; }
  });''',
        "Month appointment delete handler",
    )

    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.90 could not locate stylesheet")
    contrast_css = r'''
    /* v0.12.90 reminder contrast and live automation state. */
    :root[data-theme="light"] .calendar-reminder-status button[data-reminder-filter="completed"] strong,
    :root[data-theme="light"] .calendar-reminder-state[data-state="completed"],
    :root[data-theme="light"] .calendar-month-reminder-state[data-state="completed"],
    :root[data-theme="light"] .calendar-reminder-badge[data-status="delivered"] { color:#126b3a; border-color:#2b7d50; }
    .automation-state { width:max-content; padding:.14rem .4rem; border:1px solid var(--line); border-radius:999px; color:var(--cyan); font-size:.66rem; text-transform:capitalize; }
    .automation-state[data-state="executed"] { color:#39d6a1; }
    .automation-state[data-state="approval_required"] { color:#e7a449; }
'''
    frontend = frontend[:style_close] + contrast_css + frontend[style_close:]

    frontend = replace_once(
        frontend,
        '''    $("ha-history-status").textContent=`Read-only timeline loaded · ${data.entity_count||data.series?.length||entities.length} entities · ${data.hours} hours · ${data.event_count||0} events${data.truncated?" · bounded result":""}`;''',
        '''    const warning=(data.warnings||[]).length?` · ${data.warnings.join(" · ")}`:"";$("ha-history-status").textContent=`Read-only timeline loaded · ${data.entity_count||data.series?.length||entities.length} entities · ${data.hours} hours · ${data.event_count||0} events${data.live_event_count?` · ${data.live_event_count} live`:""}${data.truncated?" · bounded result":""}${warning}`;''',
        "history source status",
    )

    body_close = frontend.rfind("</body>")
    if body_close < 0:
        raise RuntimeError("ZBRANO v0.12.90 could not locate body close")
    history_runtime = r'''
<script id="zbrano-v01290-live-history">
(() => {
  const historyTab=document.querySelector('[data-entity-view="history"]');
  const input=document.getElementById('ha-history-entities');
  const status=document.getElementById('ha-history-status');
  if(!historyTab||!input||!status)return;
  let loading=false;
  async function api(path){const response=await fetch(path,{cache:'no-store'});const data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(data.detail||`HTTP ${response.status}`);return data}
  async function initialize(){
    if(loading)return;loading=true;status.textContent='Loading recent approved Home Assistant activity…';
    try{
      if(input.value.trim()){await window.zbranoHaHistory?.load();return}
      const live=await api('api/ha/live-events?limit=100');
      let ids=[...new Set((live.events||[]).map(item=>item.entity_id).filter(Boolean))].slice(0,8);
      if(!ids.length){const approved=await api('api/ha/approved');ids=[...new Set([...(approved.control_entities||[]),...(approved.read_entities||[])])].slice(0,8)}
      input.value=ids.join(', ');
      if(ids.length)await window.zbranoHaHistory?.load();else status.textContent='No approved entities are available for History.';
    }catch(error){status.textContent=`History initialization failed: ${error.message||error}`}finally{loading=false}
  }
  historyTab.addEventListener('click',()=>setTimeout(initialize,0));
})();
</script>
'''
    frontend = frontend[:body_close] + history_runtime + frontend[body_close:]

    backend = backend.replace('version="0.12.89"', 'version="0.12.90"')
    backend = backend.replace('"version": "0.12.89"', '"version": "0.12.90"')
    frontend = frontend.replace("HUD 0.12.89", "HUD 0.12.90")

    for marker, location in [
        ('version="0.12.90"', backend),
        ('_dispatch_ha_state_changed(event)', backend),
        ('HA_LIVE_EVENTS: deque', backend),
        ('AUTOMATION_ENGINE_LOCK', backend),
        ('@app.post("/api/automations/suggestions/{suggestion_id}/approve")', backend),
        ('"automatic_execution": data["settings"].get("operating_mode") == "selective_autonomy"', backend),
        ('id="zbrano-v01290-live-history"', frontend),
        ('id="automation-trigger-entity"', frontend),
        ('data-calendar-month-delete', frontend),
        ('#126b3a', frontend),
        ('HUD 0.12.90', frontend),
    ]:
        require(location, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
