import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.76 history expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    history_tools = r'''    {
        "type": "function",
        "name": "get_home_assistant_history",
        "description": "Read bounded state history and deterministic trend summaries for one to eight ZBRANO-approved Home Assistant entities. This is read-only and never changes Home Assistant.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 8},
                "hours": {"type": "integer", "minimum": 1, "maximum": 168},
                "max_points": {"type": "integer", "minimum": 10, "maximum": 240}
            },
            "required": ["entity_ids", "hours", "max_points"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "correlate_home_assistant_timeline",
        "description": "Build a bounded chronological timeline across approved Home Assistant entities, including state changes, logbook events, trends, and close-in-time correlation windows. Read-only.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 8},
                "hours": {"type": "integer", "minimum": 1, "maximum": 168},
                "query": {"type": "string", "description": "Optional case-insensitive logbook text filter; use an empty string for all relevant events."},
                "limit": {"type": "integer", "minimum": 10, "maximum": 300}
            },
            "required": ["entity_ids", "hours", "query", "limit"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "search_home_assistant_logbook",
        "description": "Search bounded Home Assistant logbook events for one to eight approved entities. Read-only; returns only the requested time window and a maximum of 300 events.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 8},
                "hours": {"type": "integer", "minimum": 1, "maximum": 168},
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 10, "maximum": 300}
            },
            "required": ["entity_ids", "hours", "query", "limit"],
            "additionalProperties": False
        },
        "strict": True
    },
'''
    backend = replace_once(
        backend,
        '''    {
        "type": "function",
        "name": "save_general_instruction",''',
        history_tools + '''    {
        "type": "function",
        "name": "save_general_instruction",''',
        "Home Assistant history tools",
    )

    history_backend = r'''HA_HISTORY_MAX_ENTITIES = 8
HA_HISTORY_MAX_HOURS = 168
HA_HISTORY_MAX_POINTS = 240
HA_HISTORY_MAX_EVENTS = 300


def _ha_history_entities(values: Any) -> list[str]:
    if isinstance(values, str):
        candidates = values.split(",")
    elif isinstance(values, list):
        candidates = values
    else:
        raise ValueError("entity_ids must be a list or comma-separated string")
    entities: list[str] = []
    for value in candidates:
        entity_id = str(value or "").strip().lower()
        if not entity_id or entity_id in entities:
            continue
        if not re.fullmatch(r"[a-z0-9_]+\.[a-z0-9_]+", entity_id):
            raise ValueError(f"Invalid Home Assistant entity ID: {entity_id}")
        ensure_read_allowed(entity_id)
        entities.append(entity_id)
    if not entities:
        raise ValueError("Select at least one approved Home Assistant entity")
    if len(entities) > HA_HISTORY_MAX_ENTITIES:
        raise ValueError(f"History is limited to {HA_HISTORY_MAX_ENTITIES} entities per request")
    return entities


def _ha_history_bounds(hours: int) -> tuple[Any, Any, int]:
    from datetime import datetime, timedelta, timezone
    bounded = max(1, min(HA_HISTORY_MAX_HOURS, int(hours or 24)))
    end = datetime.now(timezone.utc)
    return end - timedelta(hours=bounded), end, bounded


def _ha_history_float(value: Any) -> float | None:
    import math
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _ha_history_downsample(points: list[dict[str, Any]], maximum: int) -> list[dict[str, Any]]:
    maximum = max(2, min(HA_HISTORY_MAX_POINTS, int(maximum or 80)))
    if len(points) <= maximum:
        return points
    indexes = {round(index * (len(points) - 1) / (maximum - 1)) for index in range(maximum)}
    return [points[index] for index in sorted(indexes)]


def _ha_history_summary(entity_id: str, points: list[dict[str, Any]], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = metadata or {}
    attributes = metadata.get("attributes") or {}
    states = [str(point.get("state") or "") for point in points]
    numeric = [
        (str(point.get("last_changed") or ""), value)
        for point in points
        if (value := _ha_history_float(point.get("state"))) is not None
    ]
    transitions = sum(1 for left, right in zip(states, states[1:]) if left != right)
    unavailable = sum(1 for state in states if state.casefold() in {"unknown", "unavailable", "none", ""})
    result: dict[str, Any] = {
        "entity_id": entity_id,
        "friendly_name": metadata.get("friendly_name") or attributes.get("friendly_name") or entity_id,
        "unit": attributes.get("unit_of_measurement"),
        "point_count": len(points),
        "first_state": states[0] if states else None,
        "last_state": states[-1] if states else None,
        "transitions": transitions,
        "unavailable_points": unavailable,
        "numeric": bool(numeric),
    }
    if numeric:
        values = [value for _, value in numeric]
        differences = [abs(right - left) for left, right in zip(values, values[1:])]
        ordered_differences = sorted(differences)
        median_step = ordered_differences[len(ordered_differences) // 2] if ordered_differences else 0.0
        anomaly_threshold = max(median_step * 6.0, 0.000001)
        anomaly_count = sum(1 for difference in differences if difference > anomaly_threshold and difference > median_step)
        change = values[-1] - values[0]
        stable_threshold = max(abs(sum(values) / len(values)) * 0.005, 0.01)
        trend = "stable" if abs(change) <= stable_threshold else "rising" if change > 0 else "falling"
        result.update({
            "minimum": round(min(values), 4), "maximum": round(max(values), 4),
            "average": round(sum(values) / len(values), 4), "change": round(change, 4),
            "trend": trend, "largest_step": round(max(differences), 4) if differences else 0.0,
            "possible_anomaly_count": anomaly_count,
        })
    return result


def _ha_history_normalize_series(raw: Any, entity_id: str) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    points: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        changed = str(item.get("last_changed") or item.get("last_updated") or "")
        state = item.get("state")
        if not changed or state is None:
            continue
        point: dict[str, Any] = {"entity_id": entity_id, "state": str(state), "last_changed": changed}
        number = _ha_history_float(state)
        if number is not None:
            point["numeric_value"] = number
        points.append(point)
    points.sort(key=lambda item: item["last_changed"])
    return points


async def get_home_assistant_history(entity_ids: Any, hours: int = 24, max_points: int = 80) -> dict[str, Any]:
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
    metadata_results = await asyncio.gather(*(ha_get_state(entity_id) for entity_id in entities), return_exceptions=True)
    metadata = {
        entity_id: value if isinstance(value, dict) else {}
        for entity_id, value in zip(entities, metadata_results)
    }
    series: list[dict[str, Any]] = []
    for index, entity_id in enumerate(entities):
        raw = payload[index] if index < len(payload) else []
        full_points = _ha_history_normalize_series(raw, entity_id)
        series.append({
            "entity_id": entity_id,
            "summary": _ha_history_summary(entity_id, full_points, metadata.get(entity_id)),
            "points": _ha_history_downsample(full_points, max_points),
            "raw_point_count": len(full_points),
        })
    return {
        "read_only": True, "hours": bounded_hours, "start": start.isoformat(), "end": end.isoformat(),
        "entity_count": len(entities), "series": series,
        "limits": {"entities": HA_HISTORY_MAX_ENTITIES, "hours": HA_HISTORY_MAX_HOURS, "points_per_entity": HA_HISTORY_MAX_POINTS},
    }


async def search_home_assistant_logbook(entity_ids: Any, hours: int = 24, query: str = "", limit: int = 120) -> dict[str, Any]:
    from urllib.parse import quote
    entities = _ha_history_entities(entity_ids)
    if not SUPERVISOR_TOKEN:
        raise RuntimeError("Home Assistant API token unavailable")
    start, end, bounded_hours = _ha_history_bounds(hours)
    bounded_limit = max(10, min(HA_HISTORY_MAX_EVENTS, int(limit or 120)))
    headers = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}", "Content-Type": "application/json"}
    path = f"{HA_API_BASE}/logbook/{quote(start.isoformat(), safe='')}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        responses = await asyncio.gather(*(
            client.get(path, headers=headers, params={"end_time": end.isoformat(), "entity": entity_id})
            for entity_id in entities
        ))
    needle = " ".join(str(query or "").casefold().split())
    events: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for entity_id, response in zip(entities, responses):
        if response.is_error:
            raise RuntimeError(f"Home Assistant logbook returned HTTP {response.status_code}: {response.text[:300]}")
        payload = response.json()
        if not isinstance(payload, list):
            continue
        for item in payload:
            if not isinstance(item, dict):
                continue
            event = {
                "when": str(item.get("when") or ""), "entity_id": str(item.get("entity_id") or entity_id),
                "name": str(item.get("name") or ""), "message": str(item.get("message") or ""),
                "domain": str(item.get("domain") or ""), "source": "logbook",
            }
            haystack = " ".join(str(event[key]).casefold() for key in ("entity_id", "name", "message", "domain"))
            if needle and needle not in haystack:
                continue
            identity = (event["when"], event["entity_id"], event["message"])
            if not event["when"] or identity in seen:
                continue
            seen.add(identity); events.append(event)
    events.sort(key=lambda item: item["when"], reverse=True)
    return {"read_only": True, "hours": bounded_hours, "start": start.isoformat(), "end": end.isoformat(), "query": query, "count": min(len(events), bounded_limit), "events": events[:bounded_limit], "truncated": len(events) > bounded_limit}


def _ha_correlation_windows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from datetime import datetime
    ordered = sorted(events, key=lambda item: str(item.get("when") or ""))
    windows: list[dict[str, Any]] = []
    for index, event in enumerate(ordered):
        try:
            start = datetime.fromisoformat(str(event.get("when") or "").replace("Z", "+00:00"))
        except ValueError:
            continue
        group = [event]
        for candidate in ordered[index + 1:]:
            try:
                moment = datetime.fromisoformat(str(candidate.get("when") or "").replace("Z", "+00:00"))
            except ValueError:
                continue
            if (moment - start).total_seconds() > 60:
                break
            group.append(candidate)
        entity_set = sorted({str(item.get("entity_id") or "") for item in group if item.get("entity_id")})
        if len(entity_set) >= 2:
            signature = (str(group[0].get("when")), tuple(entity_set))
            if not windows or windows[-1].get("signature") != signature:
                windows.append({"signature": signature, "start": group[0].get("when"), "end": group[-1].get("when"), "entity_ids": entity_set, "event_count": len(group)})
    for window in windows:
        window.pop("signature", None)
    return windows[:12]


async def correlate_home_assistant_timeline(entity_ids: Any, hours: int = 24, query: str = "", limit: int = 160) -> dict[str, Any]:
    bounded_limit = max(10, min(HA_HISTORY_MAX_EVENTS, int(limit or 160)))
    history, logbook = await asyncio.gather(
        get_home_assistant_history(entity_ids, hours, min(120, bounded_limit)),
        search_home_assistant_logbook(entity_ids, hours, query, bounded_limit),
    )
    events = list(logbook["events"])
    for series in history["series"]:
        for point in series["points"]:
            events.append({
                "when": point["last_changed"], "entity_id": series["entity_id"],
                "name": series["summary"].get("friendly_name"), "message": f"state changed to {point['state']}",
                "state": point["state"], "source": "history",
            })
    events.sort(key=lambda item: str(item.get("when") or ""), reverse=True)
    events = events[:bounded_limit]
    return {
        "read_only": True, "hours": history["hours"], "start": history["start"], "end": history["end"],
        "entity_count": history["entity_count"], "series": history["series"], "events": events,
        "correlation_windows": _ha_correlation_windows(events),
        "event_count": len(events), "truncated": len(events) >= bounded_limit,
    }


'''
    backend = replace_once(
        backend,
        "async def ha_get_state_rest(entity_id: str) -> dict[str, Any]:\n",
        history_backend + "async def ha_get_state_rest(entity_id: str) -> dict[str, Any]:\n",
        "history REST client",
    )

    backend = replace_once(
        backend,
        '''                if name == "create_calendar_appointment":''',
        '''                if name == "get_home_assistant_history":
                    result = await get_home_assistant_history(arguments["entity_ids"], arguments["hours"], arguments["max_points"])
                elif name == "correlate_home_assistant_timeline":
                    result = await correlate_home_assistant_timeline(arguments["entity_ids"], arguments["hours"], arguments["query"], arguments["limit"])
                elif name == "search_home_assistant_logbook":
                    result = await search_home_assistant_logbook(arguments["entity_ids"], arguments["hours"], arguments["query"], arguments["limit"])
                elif name == "create_calendar_appointment":''',
        "history tool execution",
    )

    history_routing = r'''HOME_ASSISTANT_HISTORY_TOOL_NAMES = {
    "find_home_assistant_entities", "get_home_assistant_state", "get_home_assistant_history",
    "correlate_home_assistant_timeline", "search_home_assistant_logbook",
}
HOME_ASSISTANT_HISTORY_TERMS = (
    "history", "historical", "timeline", "logbook", "trend", "anomaly", "correlate", "correlation",
    "state changes", "changed over", "over time", "last hour", "last 24", "last day", "last week",
    "past hour", "past day", "past week", "when did", "how often", "how many times",
)


def is_home_assistant_history_intent(message: str) -> bool:
    normalized = " ".join(str(message or "").casefold().split())
    return bool(normalized and any(term in normalized for term in HOME_ASSISTANT_HISTORY_TERMS))


def home_assistant_history_tools() -> list[dict[str, Any]]:
    return [tool for tool in WORKSHOP_TOOLS if str(tool.get("name") or "") in HOME_ASSISTANT_HISTORY_TOOL_NAMES]


'''
    backend = replace_once(
        backend,
        "def priority_system_instructions(base: str, message: str) -> str:\n",
        history_routing + '''def priority_system_instructions(base: str, message: str) -> str:
    if not developer_mode_enabled() and is_home_assistant_history_intent(message):
        return base + """

HOME ASSISTANT HISTORY AND EVENT TIMELINE INTENT IS ACTIVE.
Use only the provided read-only Home Assistant tools. Resolve natural device names with find_home_assistant_entities,
then request bounded history for exact approved entity IDs. Use get_home_assistant_history for one or more trends,
search_home_assistant_logbook for named events, and correlate_home_assistant_timeline when timing relationships matter.
Default to 24 hours when the user gives no period. Never request more than seven days or eight entities in one call.
Report the exact observed window and distinguish measurements from inferred correlations. A close-in-time correlation
is not proof of causation. Do not inspect repositories, Workshop Memory, plugins, or the public web for this request.
""".strip()
''',
        "history priority instructions",
    )
    backend = replace_once(
        backend,
        '''    if is_calendar_intent(message):
        return calendar_priority_tools()
    if is_home_assistant_priority_intent(message):''',
        '''    if is_calendar_intent(message):
        return calendar_priority_tools()
    if is_home_assistant_history_intent(message):
        return home_assistant_history_tools()
    if is_home_assistant_priority_intent(message):''',
        "history priority tool routing",
    )
    backend = replace_once(
        backend,
        '''def local_tool_activity(tool_names: list[str], *, writing: bool = False) -> dict[str, str]:
    local_ha = {
        "find_home_assistant_entities", "get_home_assistant_state",
        "turn_on_home_assistant_entity", "turn_off_home_assistant_entity",
    }''',
        '''def local_tool_activity(tool_names: list[str], *, writing: bool = False) -> dict[str, str]:
    history_tools = {
        "get_home_assistant_history", "correlate_home_assistant_timeline", "search_home_assistant_logbook",
    }
    local_ha = {
        "find_home_assistant_entities", "get_home_assistant_state",
        "turn_on_home_assistant_entity", "turn_off_home_assistant_entity", *history_tools,
    }''',
        "history activity tool set",
    )
    backend = replace_once(
        backend,
        '''    if tool_names and all(name in local_ha for name in tool_names):
        return {"label": "Reading Home Assistant", "provider": "home_assistant", "plugin_id": ""}''',
        '''    if tool_names and all(name in local_ha for name in tool_names):
        label = "Reading Home Assistant History" if any(name in history_tools for name in tool_names) else "Reading Home Assistant"
        return {"label": label, "provider": "home_assistant", "plugin_id": ""}''',
        "history activity classification",
    )
    backend = replace_once(
        backend,
        '''        local_ha_tools = {
            "find_home_assistant_entities",
            "get_home_assistant_state",
            "turn_on_home_assistant_entity",
            "turn_off_home_assistant_entity",
        }''',
        '''        local_ha_tools = {
            "find_home_assistant_entities",
            "get_home_assistant_state",
            "turn_on_home_assistant_entity",
            "turn_off_home_assistant_entity",
            "get_home_assistant_history",
            "correlate_home_assistant_timeline",
            "search_home_assistant_logbook",
        }''',
        "history streaming status classification",
    )

    api_endpoints = r'''

@app.get("/api/ha/history")
async def api_home_assistant_history(entity_ids: str, hours: int = 24, max_points: int = 80) -> dict[str, Any]:
    try:
        return await get_home_assistant_history(entity_ids, hours, max_points)
    except (RuntimeError, PermissionError, ValueError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=400 if isinstance(exc, (PermissionError, ValueError)) else 502, detail=str(exc)) from exc


@app.get("/api/ha/timeline")
async def api_home_assistant_timeline(entity_ids: str, hours: int = 24, query: str = "", limit: int = 160) -> dict[str, Any]:
    try:
        return await correlate_home_assistant_timeline(entity_ids, hours, query, limit)
    except (RuntimeError, PermissionError, ValueError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=400 if isinstance(exc, (PermissionError, ValueError)) else 502, detail=str(exc)) from exc


@app.get("/api/ha/logbook")
async def api_home_assistant_logbook(entity_ids: str, hours: int = 24, query: str = "", limit: int = 160) -> dict[str, Any]:
    try:
        return await search_home_assistant_logbook(entity_ids, hours, query, limit)
    except (RuntimeError, PermissionError, ValueError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=400 if isinstance(exc, (PermissionError, ValueError)) else 502, detail=str(exc)) from exc
'''
    backend = replace_once(
        backend,
        '\n\n@app.get("/api/ha/entities")\n',
        api_endpoints + '\n\n@app.get("/api/ha/entities")\n',
        "history interface APIs",
    )

    backend = replace_once(
        backend,
        '''    frontend_text = ""
    try:''',
        '''    try:
        approved_result = await approved_ha_entities()
        approved_history = sorted(set(approved_result.get("read_entities", [])) | set(approved_result.get("control_entities", [])))
        if not SUPERVISOR_TOKEN:
            add("Home Assistant History API", "failed", "Supervisor token unavailable", "entities", "Enable Home Assistant API access for the add-on.")
        elif not approved_history:
            add("Home Assistant History API", "setup_required", "No read-approved entity available for a bounded probe", "entities", "Enable at least one entity in the Entities inventory.")
        else:
            history_probe = await get_home_assistant_history(approved_history[:1], 1, 10)
            add("Home Assistant History API", "operational", f"Read-only recorder query succeeded for {history_probe.get('entity_count', 0)} entity", "entities", "Inspect Home Assistant Recorder and the Supervisor API.")
    except Exception as exc:
        add("Home Assistant History API", "failed", str(exc), "entities", "Inspect Home Assistant Recorder, entity policy, and Supervisor API logs.")

    frontend_text = ""
    try:''',
        "history diagnostics",
    )
    backend = replace_once(
        backend,
        '''            "Fast Memory frontend wired": ('id="fast-memory-list"', 'id="fast-memory-form"', 'zbrano-v01274-fast-memory'),
            "Entities frontend wired":''',
        '''            "Fast Memory frontend wired": ('id="fast-memory-list"', 'id="fast-memory-form"', 'zbrano-v01274-fast-memory'),
            "HA History frontend wired": ('data-entity-view="history"', 'id="ha-timeline-events"', 'zbrano-v01276-ha-history'),
            "Entities frontend wired":''',
        "history frontend diagnostics",
    )
    backend = replace_once(
        backend,
        '''    "fast_memory": {
        "title": "Fast Memory",''',
        '''    "ha_history": {
        "title": "Home Assistant History & Event Timeline",
        "aliases": ("history", "timeline", "logbook", "entity trend", "state changes", "correlation"),
        "terms": ("history API", "logbook API", "approved entities", "bounded query", "timeline interface"),
        "layers": ("entity policy", "Recorder history", "Logbook", "trend summary", "timeline interface"),
        "files": ("jarvis/apply_ha_history_timeline_v01276.py", "jarvis/app/main.py", "jarvis/app/static/index.html"),
    },
    "fast_memory": {
        "title": "Fast Memory",''',
        "history Developer feature",
    )

    frontend = replace_once(
        frontend,
        '''  <section id="entities-panel" class="panel hidden">
    <div class="toolbar">''',
        '''  <section id="entities-panel" class="panel hidden">
    <div class="entity-view-tabs" role="tablist" aria-label="Entity views">
      <button type="button" class="active" data-entity-view="inventory" role="tab" aria-selected="true">Entity Inventory</button>
      <button type="button" data-entity-view="history" role="tab" aria-selected="false">History &amp; Event Timeline</button>
    </div>
    <div data-entity-view-panel="inventory">
    <div class="toolbar">''',
        "entity history subtab",
    )
    timeline_html = r'''    </div>
    <div data-entity-view-panel="history" class="hidden">
      <div class="ha-history-shell">
        <div class="ha-history-heading"><div><h2>HOME ASSISTANT HISTORY &amp; EVENT TIMELINE</h2><p>Read-only, bounded Recorder and Logbook evidence for approved entities.</p></div><span class="ha-history-readonly">READ ONLY</span></div>
        <form id="ha-history-form" class="ha-history-controls">
          <label class="wide">Entity IDs<input id="ha-history-entities" required placeholder="sensor.workshop_temperature, binary_sensor.workshop_door"><small>Up to eight entities enabled for reading in ZBRANO policy.</small></label>
          <label>Period<select id="ha-history-hours"><option value="1">Last hour</option><option value="6">Last 6 hours</option><option value="24" selected>Last 24 hours</option><option value="72">Last 3 days</option><option value="168">Last 7 days</option></select></label>
          <label>Logbook filter<input id="ha-history-query" placeholder="Optional event text"></label>
          <button id="ha-history-use-approved" type="button">Use approved entities</button>
          <button type="submit">Load timeline</button>
        </form>
        <div id="ha-history-status" class="ha-history-status" role="status">Choose approved entities and load a bounded timeline.</div>
        <div id="ha-history-summaries" class="ha-history-summaries"></div>
        <div id="ha-history-charts" class="ha-history-charts"></div>
        <section class="ha-history-event-card"><div class="ha-history-section-head"><h3>Event timeline</h3><span id="ha-history-event-count"></span></div><div id="ha-timeline-events" class="ha-timeline-events"></div></section>
      </div>
    </div>
'''
    frontend = replace_once(
        frontend,
        '''    </div>
  </section>

  <section id="settings-panel" class="panel hidden">''',
        timeline_html + '''  </section>

  <section id="settings-panel" class="panel hidden">''',
        "history timeline panel",
    )

    history_css = r'''
    /* v0.12.76 Home Assistant History and Event Timeline. */
    .entity-view-tabs { display:flex; flex-wrap:wrap; gap:.38rem; padding-bottom:.55rem; margin-bottom:.65rem; border-bottom:1px solid var(--line); }
    .entity-view-tabs button { padding:.38rem .65rem; font-size:.73rem; }
    .entity-view-tabs button.active { border-color:var(--cyan); color:var(--cyan); }
    [data-entity-view-panel].hidden { display:none; }
    .ha-history-shell { display:grid; gap:.75rem; min-width:0; height:100%; overflow:auto; padding-bottom:1rem; }
    .ha-history-heading,.ha-history-section-head { display:flex; justify-content:space-between; align-items:flex-start; gap:.75rem; }
    .ha-history-heading h2,.ha-history-section-head h3 { margin:.05rem 0 .22rem; }
    .ha-history-heading p { margin:0; color:var(--text-muted); }
    .ha-history-readonly { flex:0 0 auto; padding:.24rem .48rem; border:1px solid var(--line); border-radius:999px; color:var(--cyan); font-size:.62rem; letter-spacing:.08em; }
    .ha-history-controls { display:grid; grid-template-columns:minmax(18rem,2fr) minmax(8rem,.6fr) minmax(12rem,1fr) auto auto; align-items:end; gap:.55rem; padding:.7rem; border:1px solid var(--line); border-radius:7px; background:var(--surface); }
    .ha-history-controls label { display:grid; gap:.25rem; color:var(--text-muted); font-size:.7rem; }
    .ha-history-controls input,.ha-history-controls select { box-sizing:border-box; width:100%; min-height:2.15rem; }
    .ha-history-controls small { font-size:.62rem; }
    .ha-history-status { padding:.5rem .65rem; border-left:2px solid var(--cyan); color:var(--text-muted); }
    .ha-history-summaries { display:grid; grid-template-columns:repeat(auto-fit,minmax(13rem,1fr)); gap:.55rem; }
    .ha-history-summary,.ha-history-chart,.ha-history-event-card { min-width:0; padding:.7rem; border:1px solid var(--line); border-radius:7px; background:color-mix(in srgb,var(--surface) 82%,transparent); }
    .ha-history-summary strong { display:block; overflow-wrap:anywhere; }
    .ha-history-summary-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.3rem .6rem; margin-top:.45rem; font-size:.69rem; color:var(--text-muted); }
    .ha-history-summary-grid b { color:var(--text); font-weight:600; }
    .ha-history-charts { display:grid; grid-template-columns:repeat(auto-fit,minmax(18rem,1fr)); gap:.55rem; }
    .ha-history-chart-head { display:flex; justify-content:space-between; gap:.5rem; margin-bottom:.35rem; font-size:.72rem; }
    .ha-history-chart svg { display:block; width:100%; height:8rem; overflow:visible; }
    .ha-history-chart polyline { fill:none; stroke:var(--cyan); stroke-width:2; vector-effect:non-scaling-stroke; }
    .ha-history-chart line { stroke:var(--line); stroke-width:1; vector-effect:non-scaling-stroke; }
    .ha-timeline-events { display:grid; gap:.36rem; max-height:28rem; overflow:auto; }
    .ha-timeline-event { display:grid; grid-template-columns:9.5rem minmax(9rem,.7fr) minmax(0,1.5fr); gap:.55rem; padding:.5rem .55rem; border-left:2px solid var(--line); background:color-mix(in srgb,var(--surface-strong) 68%,transparent); font-size:.72rem; }
    .ha-timeline-event[data-source="logbook"] { border-left-color:var(--cyan); }
    .ha-timeline-event time,.ha-timeline-source { color:var(--text-muted); }
    .ha-history-empty { padding:1rem; border:1px dashed var(--line); border-radius:6px; color:var(--text-muted); text-align:center; }
    @media(max-width:1050px) { .ha-history-controls { grid-template-columns:1fr 1fr; } .ha-history-controls .wide { grid-column:1/-1; } }
    @media(max-width:620px) { .ha-history-controls { grid-template-columns:1fr; } .ha-history-controls .wide { grid-column:auto; } .ha-timeline-event { grid-template-columns:1fr; gap:.2rem; } .ha-history-charts { grid-template-columns:1fr; } }
'''
    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.76 history could not locate the stylesheet close")
    frontend = frontend[:style_close] + history_css + frontend[style_close:]

    history_runtime = r'''

<script id="zbrano-v01276-ha-history">
(() => {
  const panel=document.getElementById("entities-panel");
  const form=document.getElementById("ha-history-form");
  if(!panel||!form)return;
  const $=id=>document.getElementById(id);
  const esc=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"})[char]);
  const tabs=[...panel.querySelectorAll("[data-entity-view]")];
  const views=[...panel.querySelectorAll("[data-entity-view-panel]")];

  function showView(name){
    for(const tab of tabs){const active=tab.dataset.entityView===name;tab.classList.toggle("active",active);tab.setAttribute("aria-selected",String(active));}
    for(const view of views)view.classList.toggle("hidden",view.dataset.entityViewPanel!==name);
  }
  tabs.forEach(tab=>tab.addEventListener("click",()=>showView(tab.dataset.entityView)));

  async function api(path){const response=await fetch(path,{cache:"no-store"});const data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(data.detail||`HTTP ${response.status}`);return data;}
  function selectedEntities(){return [...new Set($("ha-history-entities").value.split(",").map(value=>value.trim().toLowerCase()).filter(Boolean))];}
  function metric(label,value){return `<span>${esc(label)} <b>${esc(value??"—")}</b></span>`;}

  function renderSummaries(series){
    const root=$("ha-history-summaries");root.replaceChildren();
    for(const item of series||[]){const summary=item.summary||{};const node=document.createElement("article");node.className="ha-history-summary";
      const metrics=[metric("Latest",`${summary.last_state??"—"}${summary.unit?` ${summary.unit}`:""}`),metric("Changes",summary.transitions),metric("Points",summary.point_count),metric("Unavailable",summary.unavailable_points)];
      if(summary.numeric)metrics.push(metric("Trend",summary.trend),metric("Range",`${summary.minimum}–${summary.maximum}`),metric("Average",summary.average),metric("Possible jumps",summary.possible_anomaly_count));
      node.innerHTML=`<strong>${esc(summary.friendly_name||item.entity_id)}</strong><small>${esc(item.entity_id)}</small><div class="ha-history-summary-grid">${metrics.join("")}</div>`;root.appendChild(node);}
  }

  function renderCharts(series){
    const root=$("ha-history-charts");root.replaceChildren();
    for(const item of series||[]){const points=(item.points||[]).filter(point=>Number.isFinite(Number(point.numeric_value)));if(points.length<2)continue;
      const values=points.map(point=>Number(point.numeric_value)),minimum=Math.min(...values),maximum=Math.max(...values),span=maximum-minimum||1;
      const coordinates=values.map((value,index)=>`${(index/(values.length-1)*100).toFixed(2)},${(92-((value-minimum)/span)*84).toFixed(2)}`).join(" ");
      const node=document.createElement("article");node.className="ha-history-chart";node.innerHTML=`<div class="ha-history-chart-head"><strong>${esc(item.summary?.friendly_name||item.entity_id)}</strong><span>${esc(minimum)}–${esc(maximum)} ${esc(item.summary?.unit||"")}</span></div><svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="${esc(item.entity_id)} history trend"><line x1="0" y1="92" x2="100" y2="92"></line><line x1="0" y1="8" x2="100" y2="8"></line><polyline points="${coordinates}"></polyline></svg>`;root.appendChild(node);}
  }

  function renderEvents(events){
    const root=$("ha-timeline-events");root.replaceChildren();$("ha-history-event-count").textContent=`${events.length} bounded events`;
    if(!events.length){root.innerHTML='<div class="ha-history-empty">No matching history or logbook events in this period.</div>';return;}
    for(const event of events){const node=document.createElement("article");node.className="ha-timeline-event";node.dataset.source=event.source||"history";const when=new Date(event.when);node.innerHTML=`<time>${esc(Number.isNaN(when.getTime())?event.when:when.toLocaleString())}</time><strong>${esc(event.name||event.entity_id||"Home Assistant")}</strong><span>${esc(event.message||event.state||"")} <small class="ha-timeline-source">${esc(event.source||"")}</small></span>`;root.appendChild(node);}
  }

  async function loadTimeline(){
    const entities=selectedEntities();if(!entities.length){$("ha-history-status").textContent="Enter at least one approved entity ID.";return;}
    if(entities.length>8){$("ha-history-status").textContent="Select no more than eight entities.";return;}
    const hours=Number($("ha-history-hours").value||24),query=$("ha-history-query").value.trim();$("ha-history-status").textContent="Reading bounded Home Assistant history and logbook…";
    const data=await api(`api/ha/timeline?entity_ids=${encodeURIComponent(entities.join(","))}&hours=${hours}&query=${encodeURIComponent(query)}&limit=160`);
    renderSummaries(data.series||[]);renderCharts(data.series||[]);renderEvents(data.events||[]);
    $("ha-history-status").textContent=`Read-only timeline loaded · ${data.entity_count||data.series?.length||entities.length} entities · ${data.hours} hours · ${data.event_count||0} events${data.truncated?" · bounded result":""}`;
  }
  form.addEventListener("submit",event=>{event.preventDefault();loadTimeline().catch(error=>{$("ha-history-status").textContent=`Timeline failed: ${error.message||error}`;});});
  $("ha-history-use-approved").addEventListener("click",async()=>{try{const data=await api("api/ha/approved");const ids=[...new Set([...(data.read_entities||[]),...(data.control_entities||[])])].slice(0,8);$("ha-history-entities").value=ids.join(", ");$("ha-history-status").textContent=ids.length?`${ids.length} approved entities selected.`:"No approved entities are available.";}catch(error){$("ha-history-status").textContent=`Could not load approved entities: ${error.message||error}`;}});
  window.zbranoHaHistory={show:()=>showView("history"),load:loadTimeline};
})();
</script>
'''
    frontend = replace_once(frontend, "\n</body>\n</html>", history_runtime + "\n</body>\n</html>", "history frontend runtime")

    backend = backend.replace('version="0.12.75"', 'version="0.12.76"')
    backend = backend.replace('"version": "0.12.75"', '"version": "0.12.76"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.75"', '"X-ZBRANO-Frontend-Version": "0.12.76"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.75"', '"name": "ZBRANO Developer Mode", "version": "0.12.76"')
    frontend = frontend.replace("HUD 0.12.75", "HUD 0.12.76")

    backend_markers = (
        'version="0.12.76"', '"name": "get_home_assistant_history"',
        '"name": "correlate_home_assistant_timeline"', '"name": "search_home_assistant_logbook"',
        "async def get_home_assistant_history(", "async def search_home_assistant_logbook(",
        "async def correlate_home_assistant_timeline(", '@app.get("/api/ha/timeline")',
        "HOME ASSISTANT HISTORY AND EVENT TIMELINE INTENT IS ACTIVE", '"Home Assistant History API"',
        '"Reading Home Assistant History"',
    )
    frontend_markers = (
        "HUD 0.12.76", 'data-entity-view="history"', 'id="ha-history-form"',
        'id="ha-timeline-events"', 'id="zbrano-v01276-ha-history"', "window.zbranoHaHistory",
    )
    missing = [marker for marker in backend_markers if marker not in backend]
    missing += [marker for marker in frontend_markers if marker not in frontend]
    if missing:
        raise RuntimeError("ZBRANO v0.12.76 history verification failed: " + ", ".join(missing))

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
