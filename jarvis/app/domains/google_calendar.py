from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
import re
import time
from typing import Any

import httpx


def configure_google_calendar_domain(
    *, plugin_load, plugin_save, calendar_store_fn, calendar_save_fn,
    oauth_records_fn, plugin_secrets_fn, oauth_scope_set_fn,
    refresh_oauth_token_fn, plugin_registry_fn, sync_task_provider,
) -> None:
    global _plugin_load, _plugin_save, calendar_store, _calendar_save
    global plugin_oauth_records, plugin_secrets, _oauth_scope_set
    global _refresh_plugin_oauth_token, plugin_registry, google_calendar_sync_task
    _plugin_load = plugin_load
    _plugin_save = plugin_save
    calendar_store = calendar_store_fn
    _calendar_save = calendar_save_fn
    plugin_oauth_records = oauth_records_fn
    plugin_secrets = plugin_secrets_fn
    _oauth_scope_set = oauth_scope_set_fn
    _refresh_plugin_oauth_token = refresh_oauth_token_fn
    plugin_registry = plugin_registry_fn
    google_calendar_sync_task = sync_task_provider


def google_calendar_worker_active() -> bool:
    task = google_calendar_sync_task()
    return task is not None and not task.done()


GOOGLE_CALENDAR_OAUTH_SCOPES = (
    "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
    "https://www.googleapis.com/auth/calendar.events",
)

GOOGLE_CALENDAR_RESOURCE_URL = "https://calendarmcp.googleapis.com/mcp/v1"

GOOGLE_CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"

GOOGLE_CALENDAR_SYNC_PATH = Path("/data/zbrano_google_calendar_sync.json")

GOOGLE_CALENDAR_SYNC_LOCK = asyncio.Lock()

def _google_calendar_plugin_id() -> str:
    import hashlib

    return hashlib.sha256(GOOGLE_CALENDAR_RESOURCE_URL.encode()).hexdigest()[:16]

def google_calendar_sync_store() -> dict[str, Any]:
    raw = _plugin_load(GOOGLE_CALENDAR_SYNC_PATH) or {}
    return {
        "version": 1,
        "enabled": bool(raw.get("enabled")),
        "calendar_id": str(raw.get("calendar_id") or "primary")[:1024],
        "calendar_name": str(raw.get("calendar_name") or "Primary calendar")[:300],
        "sync_token": str(raw.get("sync_token") or "")[:12000],
        "previewed_at": float(raw.get("previewed_at") or 0),
        "preview": raw.get("preview") if isinstance(raw.get("preview"), dict) else {},
        "initial_sync_complete": bool(raw.get("initial_sync_complete")),
        "last_sync_at": float(raw.get("last_sync_at") or 0),
        "last_success_at": float(raw.get("last_success_at") or 0),
        "last_error": str(raw.get("last_error") or "")[:1000],
        "last_result": raw.get("last_result") if isinstance(raw.get("last_result"), dict) else {},
    }

def _google_calendar_sync_save(state: dict[str, Any]) -> None:
    _plugin_save(GOOGLE_CALENDAR_SYNC_PATH, {**google_calendar_sync_store(), **state, "version": 1})

def _google_calendar_merge_concurrent_local_changes(data: dict[str, Any]) -> None:
    """Preserve reminders and appointments changed while a network sync was awaiting Google."""
    fresh = calendar_store()
    staged = {str(item.get("id") or ""): item for item in data.get("appointments") or []}
    for current in fresh["appointments"]:
        appointment_id = str(current.get("id") or "")
        target = staged.get(appointment_id)
        if not target:
            data.setdefault("appointments", []).append(current)
            staged[appointment_id] = current
            continue
        target["reminders"] = current.get("reminders", [])
        target["destination"] = current.get("destination", "")
        if current.get("status") == "cancelled" and target.get("status") != "cancelled":
            target["status"] = "cancelled"
            target["google_sync_state"] = current.get("google_sync_state", target.get("google_sync_state"))
            target["updated_at"] = max(float(target.get("updated_at") or 0), float(current.get("updated_at") or 0))

def google_calendar_connected() -> bool:
    plugin_id = _google_calendar_plugin_id()
    record = plugin_oauth_records().get(plugin_id) or {}
    return bool(
        plugin_secrets().get(plugin_id)
        and set(GOOGLE_CALENDAR_OAUTH_SCOPES).issubset(_oauth_scope_set(record.get("scope")))
    )

async def _google_calendar_access_token() -> str:
    plugin_id = _google_calendar_plugin_id()
    await _refresh_plugin_oauth_token(plugin_id)
    token = str(plugin_secrets().get(plugin_id) or "")
    record = plugin_oauth_records().get(plugin_id) or {}
    if not token or not set(GOOGLE_CALENDAR_OAUTH_SCOPES).issubset(_oauth_scope_set(record.get("scope"))):
        raise PermissionError("Google Calendar Direct is not connected with the required scopes")
    return token

def _google_calendar_error(response: httpx.Response) -> str:
    detail = ""
    with contextlib.suppress(ValueError, TypeError):
        payload = response.json()
        error = payload.get("error") or {}
        detail = str(error.get("message") or error.get("status") or "") if isinstance(error, dict) else str(error)
    return (detail or f"Google Calendar API returned HTTP {response.status_code}")[:500]

async def _google_calendar_request(
    method: str, path: str, *, params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None, allow_empty: bool = False,
) -> dict[str, Any]:
    if not path.startswith("/") or ".." in path or not re.fullmatch(r"/[A-Za-z0-9_./%@:+-]+", path):
        raise ValueError("Invalid Google Calendar API path")
    plugin_id = _google_calendar_plugin_id()
    token = await _google_calendar_access_token()
    async with httpx.AsyncClient(timeout=httpx.Timeout(25.0, connect=8.0), follow_redirects=False) as client:
        response = await client.request(
            method, GOOGLE_CALENDAR_API_BASE + path, params=params, json=json_body,
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 401 and await _refresh_plugin_oauth_token(plugin_id, force=True):
            token = str(plugin_secrets().get(plugin_id) or "")
            response = await client.request(
                method, GOOGLE_CALENDAR_API_BASE + path, params=params, json=json_body,
                headers={"Authorization": f"Bearer {token}"},
            )
    if response.is_redirect:
        raise RuntimeError("Google Calendar API redirects are blocked")
    if response.is_error:
        error = RuntimeError(_google_calendar_error(response))
        setattr(error, "status_code", response.status_code)
        raise error
    if allow_empty and not response.content:
        return {}
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Google Calendar API returned an invalid response")
    return payload

async def google_calendar_list_calendars() -> dict[str, Any]:
    payload = await _google_calendar_request("GET", "/users/me/calendarList", params={"maxResults": 250})
    calendars = []
    for item in (payload.get("items") or [])[:250]:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        calendars.append({
            "id": str(item.get("id"))[:1024],
            "name": str(item.get("summaryOverride") or item.get("summary") or item.get("id"))[:300],
            "primary": bool(item.get("primary")),
            "access_role": str(item.get("accessRole") or ""),
        })
    return {"calendars": calendars, "count": len(calendars)}

def _google_event_times(event: dict[str, Any]) -> tuple[str, float, float, int]:
    from datetime import datetime, timedelta

    start = event.get("start") or {}
    end = event.get("end") or {}
    raw_start = str(start.get("dateTime") or "")
    all_day = not raw_start and bool(start.get("date"))
    if all_day:
        raw_start = str(start.get("date") or "") + "T00:00:00"
    parsed = datetime.fromisoformat(raw_start.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    raw_end = str(end.get("dateTime") or "")
    if all_day:
        raw_end = str(end.get("date") or "") + "T00:00:00"
    try:
        parsed_end = datetime.fromisoformat(raw_end.replace("Z", "+00:00"))
        if parsed_end.tzinfo is None:
            parsed_end = parsed_end.astimezone()
    except ValueError:
        parsed_end = parsed + timedelta(minutes=60)
    duration = max(5, min(10080, round((parsed_end.timestamp() - parsed.timestamp()) / 60)))
    return parsed.isoformat(), parsed.timestamp(), parsed_end.timestamp(), duration

def _google_event_to_local(event: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any] | None:
    import secrets

    if not event.get("id") or event.get("status") == "cancelled":
        return None
    try:
        start_at, start_timestamp, end_timestamp, duration = _google_event_times(event)
    except (TypeError, ValueError):
        return None
    now = time.time()
    local = dict(existing or {})
    local.update({
        "id": str(local.get("id") or secrets.token_hex(12)),
        "title": str(event.get("summary") or "Untitled Google Calendar event")[:160],
        "start_at": start_at,
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "duration_minutes": duration,
        "location": str(event.get("location") or "")[:300],
        "notes": str(event.get("description") or "")[:3000],
        "status": "scheduled" if end_timestamp >= now else "completed",
        "source": "google_calendar",
        "updated_at": now,
        "google_event_id": str(event.get("id"))[:1024],
        "google_etag": str(event.get("etag") or "")[:500],
        "google_updated": str(event.get("updated") or "")[:100],
        "google_html_link": str(event.get("htmlLink") or "")[:2000],
        "google_sync_state": "synced",
    })
    local.setdefault("created_at", now)
    local.setdefault("destination", "")
    local.setdefault("reminders", [])
    return local

def _local_to_google_event(appointment: dict[str, Any]) -> dict[str, Any]:
    from datetime import datetime

    start = datetime.fromtimestamp(float(appointment.get("start_timestamp") or 0)).astimezone()
    end = datetime.fromtimestamp(float(appointment.get("end_timestamp") or 0)).astimezone()
    return {
        "summary": str(appointment.get("title") or "Untitled appointment")[:160],
        "description": str(appointment.get("notes") or "")[:3000],
        "location": str(appointment.get("location") or "")[:300],
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": end.isoformat()},
        "extendedProperties": {"private": {"zbrano_id": str(appointment.get("id") or "")[:255]}},
    }

async def _google_calendar_event_pages(calendar_id: str, sync_token: str = "") -> tuple[list[dict[str, Any]], str]:
    from datetime import datetime, timedelta, timezone
    from urllib.parse import quote

    path = f"/calendars/{quote(calendar_id, safe='')}/events"
    params: dict[str, Any] = {"maxResults": 2500, "showDeleted": "true", "singleEvents": "true"}
    if sync_token:
        params = {"maxResults": 2500, "showDeleted": "true", "syncToken": sync_token}
    else:
        params["timeMin"] = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        params["timeMax"] = (datetime.now(timezone.utc) + timedelta(days=730)).isoformat()
        params["orderBy"] = "startTime"
    events: list[dict[str, Any]] = []
    next_sync_token = ""
    for _ in range(10):
        payload = await _google_calendar_request("GET", path, params=params)
        events.extend(item for item in (payload.get("items") or []) if isinstance(item, dict))
        page_token = str(payload.get("nextPageToken") or "")
        next_sync_token = str(payload.get("nextSyncToken") or next_sync_token)
        if not page_token:
            break
        params["pageToken"] = page_token
    return events[:10000], next_sync_token

async def google_calendar_preview() -> dict[str, Any]:
    state = google_calendar_sync_store()
    calendar_id = state["calendar_id"]
    events, _ = await _google_calendar_event_pages(calendar_id)
    local = calendar_store()["appointments"]
    external_ids = {str(item.get("google_event_id") or "") for item in local if item.get("google_event_id")}
    importable = [item for item in events if item.get("status") != "cancelled" and str(item.get("id") or "") not in external_ids]
    uploadable = [
        item for item in local
        if item.get("status") == "scheduled" and not item.get("google_event_id")
        and float(item.get("end_timestamp") or 0) >= time.time()
    ]
    preview = {
        "google_events_seen": len(events), "would_import": len(importable),
        "would_upload": len(uploadable), "existing_links": len(external_ids),
        "sample_import_titles": [str(item.get("summary") or "Untitled")[:100] for item in importable[:5]],
    }
    state.update({"previewed_at": time.time(), "preview": preview, "last_error": ""})
    _google_calendar_sync_save(state)
    return preview

async def google_calendar_sync_once() -> dict[str, Any]:
    async with GOOGLE_CALENDAR_SYNC_LOCK:
        state = google_calendar_sync_store()
        if not google_calendar_connected():
            raise PermissionError("Connect Google Calendar Direct before synchronizing")
        calendar_id = state["calendar_id"]
        data = calendar_store()
        created = deleted = imported = updated = cancelled = 0

        # Propagate local cancellations before pulling remote changes.
        from urllib.parse import quote
        for appointment in data["appointments"]:
            event_id = str(appointment.get("google_event_id") or "")
            if appointment.get("google_sync_state") == "pending_delete" and event_id:
                try:
                    await _google_calendar_request(
                        "DELETE", f"/calendars/{quote(calendar_id, safe='')}/events/{quote(event_id, safe='')}",
                        allow_empty=True,
                    )
                except RuntimeError as exc:
                    if getattr(exc, "status_code", 0) not in {404, 410}:
                        raise
                appointment["google_sync_state"] = "deleted"
                deleted += 1
        _google_calendar_merge_concurrent_local_changes(data)
        _calendar_save(data)

        try:
            events, next_token = await _google_calendar_event_pages(calendar_id, state.get("sync_token") or "")
        except RuntimeError as exc:
            if getattr(exc, "status_code", 0) != 410:
                raise
            events, next_token = await _google_calendar_event_pages(calendar_id)
            state["sync_token"] = ""

        data = calendar_store()
        by_google = {str(item.get("google_event_id")): item for item in data["appointments"] if item.get("google_event_id")}
        for event in events:
            event_id = str(event.get("id") or "")
            existing = by_google.get(event_id)
            if event.get("status") == "cancelled":
                if existing and existing.get("status") != "cancelled":
                    existing["status"] = "cancelled"
                    existing["google_sync_state"] = "deleted"
                    existing["updated_at"] = time.time()
                    for reminder in existing.get("reminders") or []:
                        if reminder.get("status") == "scheduled":
                            reminder["status"] = "cancelled"
                    cancelled += 1
                continue
            mapped = _google_event_to_local(event, existing)
            if not mapped:
                continue
            if existing:
                existing.clear(); existing.update(mapped); updated += 1
            else:
                # First-sync duplicate protection links matching title/start instead of creating a second appointment.
                duplicate = next((item for item in data["appointments"] if item.get("status") != "cancelled" and not item.get("google_event_id") and str(item.get("title") or "").casefold() == str(mapped.get("title") or "").casefold() and abs(float(item.get("start_timestamp") or 0) - float(mapped.get("start_timestamp") or 0)) < 60), None)
                if duplicate:
                    preserved = {"id": duplicate.get("id"), "destination": duplicate.get("destination", ""), "reminders": duplicate.get("reminders", []), "created_at": duplicate.get("created_at", time.time())}
                    duplicate.clear(); duplicate.update(mapped); duplicate.update(preserved)
                else:
                    data["appointments"].append(mapped); imported += 1

        # Upload future ZBRANO-created appointments after import/deduplication.
        for appointment in data["appointments"]:
            if appointment.get("status") != "scheduled" or appointment.get("google_event_id") or float(appointment.get("end_timestamp") or 0) < time.time():
                continue
            payload = await _google_calendar_request(
                "POST", f"/calendars/{quote(calendar_id, safe='')}/events",
                json_body=_local_to_google_event(appointment),
            )
            appointment["google_event_id"] = str(payload.get("id") or "")[:1024]
            appointment["google_etag"] = str(payload.get("etag") or "")[:500]
            appointment["google_updated"] = str(payload.get("updated") or "")[:100]
            appointment["google_html_link"] = str(payload.get("htmlLink") or "")[:2000]
            appointment["google_sync_state"] = "synced"
            created += 1
        _google_calendar_merge_concurrent_local_changes(data)
        _calendar_save(data)
        result = {"imported": imported, "updated": updated, "cancelled": cancelled, "uploaded": created, "deleted": deleted}
        state.update({
            "sync_token": next_token or state.get("sync_token") or "",
            "initial_sync_complete": True, "last_sync_at": time.time(),
            "last_success_at": time.time(), "last_error": "", "last_result": result,
        })
        _google_calendar_sync_save(state)
        return result

def google_calendar_sync_status() -> dict[str, Any]:
    state = google_calendar_sync_store()
    plugin = plugin_registry().get(_google_calendar_plugin_id()) or {}
    pending = sum(1 for item in calendar_store()["appointments"] if item.get("google_sync_state") in {"pending_create", "pending_delete"})
    return {
        **state, "connected": google_calendar_connected(), "account": str(plugin.get("oauth_account") or ""),
        "pending_local_changes": pending, "worker_active": google_calendar_worker_active(),
        "required_scopes": list(GOOGLE_CALENDAR_OAUTH_SCOPES),
    }

async def google_calendar_sync_worker() -> None:
    while True:
        await asyncio.sleep(60.0)
        state = google_calendar_sync_store()
        if not state["enabled"] or not google_calendar_connected():
            continue
        try:
            await google_calendar_sync_once()
        except (PermissionError, RuntimeError, ValueError, httpx.HTTPError, OSError) as exc:
            fresh = google_calendar_sync_store()
            fresh.update({"last_sync_at": time.time(), "last_error": str(exc)[:1000]})
            _google_calendar_sync_save(fresh)
