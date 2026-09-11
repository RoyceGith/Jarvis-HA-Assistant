from __future__ import annotations

import asyncio
import math
import re
from collections import deque
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable
from urllib.parse import quote

HA_HISTORY_MAX_ENTITIES = 8
HA_HISTORY_MAX_HOURS = 168
HA_HISTORY_MAX_POINTS = 240
HA_HISTORY_MAX_EVENTS = 300
HA_LIVE_EVENTS: deque[dict[str, Any]] = deque(maxlen=500)
HA_EVENT_TASKS: set[asyncio.Task[Any]] = set()

_supervisor_token = ""
_ha_api_base = ""
_ensure_read_allowed: Callable[[str], Any] = lambda entity_id: None
_effective_entity_access: Callable[[str], Any] = lambda entity_id: None
_ha_get_state: Callable[[str], Awaitable[dict[str, Any]]] | None = None
_automation_evaluate: Callable[[dict[str, Any]], Awaitable[Any]] | None = None
_automation_learn: Callable[[dict[str, Any]], Awaitable[Any]] | None = None


def configure_ha_history_service(
    *,
    supervisor_token: str,
    ha_api_base: str,
    ensure_read_allowed_fn: Callable[[str], Any],
    effective_entity_access_fn: Callable[[str], Any],
    ha_get_state_fn: Callable[[str], Awaitable[dict[str, Any]]],
    automation_evaluate_fn: Callable[[dict[str, Any]], Awaitable[Any]],
    automation_learn_fn: Callable[[dict[str, Any]], Awaitable[Any]],
) -> None:
    global _supervisor_token, _ha_api_base, _ensure_read_allowed, _effective_entity_access
    global _ha_get_state, _automation_evaluate, _automation_learn
    _supervisor_token = supervisor_token
    _ha_api_base = ha_api_base
    _ensure_read_allowed = ensure_read_allowed_fn
    _effective_entity_access = effective_entity_access_fn
    _ha_get_state = ha_get_state_fn
    _automation_evaluate = automation_evaluate_fn
    _automation_learn = automation_learn_fn


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
        _ensure_read_allowed(entity_id)
        entities.append(entity_id)
    if not entities:
        raise ValueError("Select at least one approved Home Assistant entity")
    if len(entities) > HA_HISTORY_MAX_ENTITIES:
        raise ValueError(f"History is limited to {HA_HISTORY_MAX_ENTITIES} entities per request")
    return entities


def _ha_history_bounds(hours: int) -> tuple[datetime, datetime, int]:
    bounded = max(1, min(HA_HISTORY_MAX_HOURS, int(hours or 24)))
    end = datetime.now(timezone.utc)
    return end - timedelta(hours=bounded), end, bounded


def _ha_history_float(value: Any) -> float | None:
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


def _ha_history_summary(
    entity_id: str,
    points: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
        change = values[-1] - values[0]
        stable_threshold = max(abs(sum(values) / len(values)) * 0.005, 0.01)
        result.update({
            "minimum": round(min(values), 4),
            "maximum": round(max(values), 4),
            "average": round(sum(values) / len(values), 4),
            "change": round(change, 4),
            "trend": "stable" if abs(change) <= stable_threshold else "rising" if change > 0 else "falling",
            "largest_step": round(max(differences), 4) if differences else 0.0,
            "possible_anomaly_count": sum(
                1 for difference in differences
                if difference > anomaly_threshold and difference > median_step
            ),
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


def _ha_correlation_windows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
                windows.append({
                    "signature": signature,
                    "start": group[0].get("when"),
                    "end": group[-1].get("when"),
                    "entity_ids": entity_set,
                    "event_count": len(group),
                })
    for window in windows:
        window.pop("signature", None)
    return windows[:12]


def _ha_live_events(entity_ids: list[str], hours: int, limit: int) -> list[dict[str, Any]]:
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


def _schedule_event_handler(handler: Callable[[dict[str, Any]], Awaitable[Any]] | None, record: dict[str, Any], name: str) -> bool:
    if handler is None:
        return False
    try:
        task = asyncio.create_task(handler(record), name=name)
    except RuntimeError:
        return False
    HA_EVENT_TASKS.add(task)
    task.add_done_callback(HA_EVENT_TASKS.discard)
    return True


def dispatch_ha_state_changed(event: dict[str, Any]) -> None:
    data = event.get("data") or {}
    entity_id = str(data.get("entity_id") or "").lower()
    old_state = data.get("old_state") if isinstance(data.get("old_state"), dict) else {}
    new_state = data.get("new_state") if isinstance(data.get("new_state"), dict) else {}
    if not entity_id or not _effective_entity_access(entity_id):
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
    if not _schedule_event_handler(_automation_evaluate, record, f"zbrano-automation-{entity_id}"):
        return
    _schedule_event_handler(_automation_learn, record, f"zbrano-learning-{entity_id}")


async def search_home_assistant_logbook(
    entity_ids: Any,
    hours: int = 24,
    query: str = "",
    limit: int = 120,
) -> dict[str, Any]:
    import httpx

    entities = _ha_history_entities(entity_ids)
    if not _supervisor_token:
        raise RuntimeError("Home Assistant API token unavailable")
    start, end, bounded_hours = _ha_history_bounds(hours)
    bounded_limit = max(10, min(HA_HISTORY_MAX_EVENTS, int(limit or 120)))
    headers = {"Authorization": f"Bearer {_supervisor_token}", "Content-Type": "application/json"}
    path = f"{_ha_api_base}/logbook/{quote(start.isoformat(), safe='')}"
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
                "when": str(item.get("when") or ""),
                "entity_id": str(item.get("entity_id") or entity_id),
                "name": str(item.get("name") or ""),
                "message": str(item.get("message") or ""),
                "domain": str(item.get("domain") or ""),
                "source": "logbook",
            }
            haystack = " ".join(str(event[key]).casefold() for key in ("entity_id", "name", "message", "domain"))
            if needle and needle not in haystack:
                continue
            identity = (event["when"], event["entity_id"], event["message"])
            if not event["when"] or identity in seen:
                continue
            seen.add(identity)
            events.append(event)
    events.sort(key=lambda item: item["when"], reverse=True)
    return {
        "read_only": True,
        "hours": bounded_hours,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "query": query,
        "count": min(len(events), bounded_limit),
        "events": events[:bounded_limit],
        "truncated": len(events) > bounded_limit,
    }


async def get_home_assistant_history(entity_ids: Any, hours: int = 24, max_points: int = 80) -> dict[str, Any]:
    import httpx

    entities = _ha_history_entities(entity_ids)
    if not _supervisor_token:
        raise RuntimeError("Home Assistant API token unavailable")
    if _ha_get_state is None:
        raise RuntimeError("Home Assistant history service is not configured")
    start, end, bounded_hours = _ha_history_bounds(hours)
    headers = {"Authorization": f"Bearer {_supervisor_token}", "Content-Type": "application/json"}
    path = f"{_ha_api_base}/history/period/{quote(start.isoformat(), safe='')}"
    params = {
        "filter_entity_id": ",".join(entities),
        "end_time": end.isoformat(),
        "minimal_response": "",
        "no_attributes": "",
        "significant_changes_only": "",
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
    metadata_results = await asyncio.gather(*(_ha_get_state(entity_id) for entity_id in entities), return_exceptions=True)
    metadata = {entity_id: value if isinstance(value, dict) else {} for entity_id, value in zip(entities, metadata_results)}
    live = _ha_live_events(entities, bounded_hours, HA_HISTORY_MAX_EVENTS)
    live_by_entity: dict[str, list[dict[str, Any]]] = {entity_id: [] for entity_id in entities}
    for event in live:
        if event.get("state") is not None:
            live_by_entity[event["entity_id"]].append({
                "entity_id": event["entity_id"],
                "state": event["state"],
                "last_changed": event["when"],
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
        "read_only": True,
        "hours": bounded_hours,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "entity_count": len(entities),
        "series": series,
        "live_event_count": len(live),
        "limits": {
            "entities": HA_HISTORY_MAX_ENTITIES,
            "hours": HA_HISTORY_MAX_HOURS,
            "points_per_entity": HA_HISTORY_MAX_POINTS,
        },
    }


async def correlate_home_assistant_timeline(
    entity_ids: Any,
    hours: int = 24,
    query: str = "",
    limit: int = 160,
) -> dict[str, Any]:
    entities = _ha_history_entities(entity_ids)
    bounded_limit = max(10, min(HA_HISTORY_MAX_EVENTS, int(limit or 160)))
    history_result, logbook_result = await asyncio.gather(
        get_home_assistant_history(entities, hours, min(120, bounded_limit)),
        search_home_assistant_logbook(entities, hours, query, bounded_limit),
        return_exceptions=True,
    )
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
                "when": point["last_changed"],
                "entity_id": series["entity_id"],
                "name": series["summary"].get("friendly_name"),
                "message": f"state changed to {point['state']}",
                "state": point["state"],
                "source": "history",
            })
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for event in events:
        identity = (
            str(event.get("when") or ""),
            str(event.get("entity_id") or ""),
            str(event.get("state") or event.get("message") or ""),
        )
        existing = unique.get(identity)
        if existing is None or event.get("source") == "live":
            unique[identity] = event
    events = sorted(unique.values(), key=lambda item: str(item.get("when") or ""), reverse=True)[:bounded_limit]
    return {
        "read_only": True,
        "hours": history_result["hours"],
        "start": history_result["start"],
        "end": history_result["end"],
        "entity_count": history_result["entity_count"],
        "series": history_result["series"],
        "events": events,
        "correlation_windows": _ha_correlation_windows(events),
        "event_count": len(events),
        "live_event_count": history_result.get("live_event_count", 0),
        "warnings": warnings,
        "truncated": len(events) >= bounded_limit,
    }
