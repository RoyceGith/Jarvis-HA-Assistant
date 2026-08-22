from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.86 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.86 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        r'''class CalendarRemindersUpdateRequest(BaseModel):
    destination: str = Field(default="", max_length=255, pattern=r"^(|notify\.[a-z0-9_]+)$")
    reminder_offsets_minutes: list[int] = Field(default_factory=list, max_length=8)
''',
        r'''class CalendarRemindersUpdateRequest(BaseModel):
    destination: str = Field(default="", max_length=255, pattern=r"^(|notify\.[a-z0-9_]+)$")
    reminder_offsets_minutes: list[int] = Field(default_factory=list, max_length=8)


class GoogleCalendarSyncSettingsRequest(BaseModel):
    calendar_id: str = Field(default="primary", min_length=1, max_length=1024)
    enabled: bool = False
''',
        "Google Calendar settings model",
    )

    calendar_runtime = r'''
GOOGLE_CALENDAR_OAUTH_SCOPES = (
    "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
    "https://www.googleapis.com/auth/calendar.events",
)
GOOGLE_CALENDAR_RESOURCE_URL = "https://calendarmcp.googleapis.com/mcp/v1"
GOOGLE_CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
GOOGLE_CALENDAR_SYNC_PATH = Path("/data/zbrano_google_calendar_sync.json")
GOOGLE_CALENDAR_SYNC_TASK: asyncio.Task[Any] | None = None
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
        "pending_local_changes": pending, "worker_active": GOOGLE_CALENDAR_SYNC_TASK is not None and not GOOGLE_CALENDAR_SYNC_TASK.done(),
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


@app.get("/api/calendar/google/status")
async def read_google_calendar_sync_status() -> dict[str, Any]:
    return google_calendar_sync_status()


@app.get("/api/calendar/google/calendars")
async def read_google_calendars() -> dict[str, Any]:
    return await google_calendar_list_calendars()


@app.post("/api/calendar/google/preview")
async def preview_google_calendar_sync() -> dict[str, Any]:
    return await google_calendar_preview()


@app.put("/api/calendar/google/settings")
async def update_google_calendar_sync_settings(request: GoogleCalendarSyncSettingsRequest) -> dict[str, Any]:
    state = google_calendar_sync_store()
    if request.enabled:
        if not google_calendar_connected():
            raise HTTPException(status_code=409, detail="Connect Google Calendar Direct first")
        if time.time() - float(state.get("previewed_at") or 0) > 1800 or request.calendar_id != state.get("calendar_id"):
            raise HTTPException(status_code=409, detail="Preview this calendar before enabling synchronization")
    state["calendar_id"] = request.calendar_id
    state["enabled"] = request.enabled
    if request.calendar_id != google_calendar_sync_store().get("calendar_id"):
        state.update({"sync_token": "", "initial_sync_complete": False, "previewed_at": 0, "preview": {}})
    _google_calendar_sync_save(state)
    return google_calendar_sync_status()


@app.post("/api/calendar/google/sync")
async def run_google_calendar_sync() -> dict[str, Any]:
    if not google_calendar_sync_store()["enabled"]:
        raise HTTPException(status_code=409, detail="Enable Google Calendar synchronization first")
    return {"synchronized": True, "result": await google_calendar_sync_once(), "status": google_calendar_sync_status()}

'''
    backend = replace_once(
        backend,
        '\nCALENDAR_STORAGE_PATH = Path("/data/zbrano_calendar.json")\n',
        calendar_runtime + '\nCALENDAR_STORAGE_PATH = Path("/data/zbrano_calendar.json")\n',
        "Google Calendar sync runtime",
    )

    # Give Google Calendar its own OAuth identity and scopes; never reuse the Gmail grant.
    backend = replace_once(
        backend,
        '''async def _validate_gmail_oauth_grant(flow: dict[str, Any], token: dict[str, Any]) -> str:
    if not flow.get("google_connector"):
        return ""''',
        '''async def _validate_gmail_oauth_grant(flow: dict[str, Any], token: dict[str, Any]) -> str:
    if flow.get("google_service") != "gmail":
        return ""''',
        "Gmail validation isolation",
    )
    calendar_validation = r'''

async def _validate_google_calendar_oauth_grant(flow: dict[str, Any], token: dict[str, Any]) -> str:
    if flow.get("google_service") != "calendar":
        return ""
    required = set(GOOGLE_CALENDAR_OAUTH_SCOPES)
    granted = _oauth_scope_set(token.get("scope"))
    if not required.issubset(granted):
        await _revoke_rejected_oauth_token(flow, token)
        raise ValueError("Google Calendar authorization is missing required event or calendar-list access")
    access_token = str(token.get("access_token") or "")
    async with httpx.AsyncClient(timeout=PLUGIN_TIMEOUT, follow_redirects=False) as client:
        response = await client.get(
            "https://www.googleapis.com/calendar/v3/users/me/calendarList/primary",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.is_error:
        await _revoke_rejected_oauth_token(flow, token)
        raise ValueError(f"Google Calendar verification returned HTTP {response.status_code}")
    profile = _oauth_safe_json(response, "Google Calendar profile")
    return str(profile.get("summary") or profile.get("id") or "Google Calendar")[:320]
'''
    backend = replace_once(
        backend,
        "\n\nasync def enforce_stored_gmail_scope_policy() -> None:\n",
        calendar_validation + "\n\nasync def enforce_stored_gmail_scope_policy() -> None:\n",
        "Calendar OAuth validation",
    )
    backend = replace_once(
        backend,
        '''    google_connector = str(catalog_id) == "gmail-official" or str(plugin_id) == _gmail_plugin_id()
    if google_connector:
        resource_url = GMAIL_MCP_RESOURCE_URL''',
        '''    google_service = (
        "gmail" if str(catalog_id) == "gmail-official" or str(plugin_id) == _gmail_plugin_id()
        else "calendar" if str(catalog_id) == "google-calendar-official" or str(plugin_id) == _google_calendar_plugin_id()
        else ""
    )
    google_connector = bool(google_service)
    if google_connector:
        resource_url = GMAIL_MCP_RESOURCE_URL if google_service == "gmail" else GOOGLE_CALENDAR_RESOURCE_URL''',
        "Google service selection",
    )
    backend = replace_once(
        backend,
        '''        "google_connector": google_connector,
        "scope": (
            " ".join(GMAIL_MCP_OAUTH_SCOPES)
            if google_connector else''',
        '''        "google_connector": google_connector,
        "google_service": google_service,
        "scope": (
            " ".join(GMAIL_MCP_OAUTH_SCOPES if google_service == "gmail" else GOOGLE_CALENDAR_OAUTH_SCOPES)
            if google_connector else''',
        "Google service scopes",
    )
    backend = replace_once(
        backend,
        '''        oauth_account = await _validate_gmail_oauth_grant(flow, token)
        access_token = str(token["access_token"])
        if flow.get("google_connector"):
            tools = gmail_direct_tool_records()
            plugin_id = _gmail_plugin_id()''',
        '''        oauth_account = await _validate_gmail_oauth_grant(flow, token)
        if flow.get("google_service") == "calendar":
            oauth_account = await _validate_google_calendar_oauth_grant(flow, token)
        access_token = str(token["access_token"])
        if flow.get("google_service") == "gmail":
            tools = gmail_direct_tool_records()
            plugin_id = _gmail_plugin_id()
        elif flow.get("google_service") == "calendar":
            tools = []
            plugin_id = _google_calendar_plugin_id()''',
        "Calendar OAuth callback tools",
    )
    backend = replace_once(
        backend,
        '''            "name": "Gmail Direct" if flow.get("google_connector") else flow["name"],
            "url": "https://gmail.googleapis.com/gmail/v1" if flow.get("google_connector") else flow["resource_url"],
            "catalog_id": "gmail-official" if flow.get("google_connector") else str(flow.get("catalog_id") or ""),''',
        '''            "name": (
                "Gmail Direct" if flow.get("google_service") == "gmail"
                else "Google Calendar Direct" if flow.get("google_service") == "calendar"
                else flow["name"]
            ),
            "url": (
                "https://gmail.googleapis.com/gmail/v1" if flow.get("google_service") == "gmail"
                else GOOGLE_CALENDAR_API_BASE if flow.get("google_service") == "calendar"
                else flow["resource_url"]
            ),
            "catalog_id": (
                "gmail-official" if flow.get("google_service") == "gmail"
                else "google-calendar-official" if flow.get("google_service") == "calendar"
                else str(flow.get("catalog_id") or "")
            ),''',
        "Calendar OAuth registry identity",
    )

    backend = replace_once(
        backend,
        '''        "id": "google-calendar-official", "name": "com.google.workspace/calendar", "title": "Google Calendar",
        "description": "Official Google Calendar remote MCP server for calendars, events, scheduling, and responses.",
        "url": "https://calendarmcp.googleapis.com/mcp/v1", "category": "productivity", "verified": True,
        "auth_required": True, "auth_mode": "oauth", "installable": False, "publisher": "Google",
        "setup_label": "OAuth setup required", "availability": "Developer Preview",''',
        '''        "id": "google-calendar-official", "name": "zbrano.google-calendar-direct", "title": "Google Calendar Direct",
        "description": "Two-way synchronization between Google Calendar and ZBRANO's visual calendar while preserving local Telegram reminders.",
        "url": "https://calendarmcp.googleapis.com/mcp/v1", "category": "productivity", "verified": True,
        "auth_required": True, "auth_mode": "oauth", "installable": False, "oauth_connectable": True, "publisher": "ZBRANO + Google Calendar API",
        "setup_label": "Connect with Google", "availability": "Standard Calendar API",''',
        "Calendar catalog presentation",
    )
    backend = replace_once(
        backend,
        '''        if item.get("id") == "gmail-official":
            installed = plugin_registry().get(_gmail_plugin_id()) or installed''',
        '''        if item.get("id") == "gmail-official":
            installed = plugin_registry().get(_gmail_plugin_id()) or installed
        elif item.get("id") == "google-calendar-official":
            installed = plugin_registry().get(_google_calendar_plugin_id()) or installed''',
        "Calendar installed detection",
    )
    backend = replace_once(
        backend,
        '''        elif item.get("id") == "gmail-official":
            google_ready = bool(
                os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
                and os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
            )
            item["oauth_available"] = google_ready
            item["oauth_connectable"] = True
            item["setup_label"] = "Connect with Google" if google_ready else "Google OAuth setup required"''',
        '''        elif item.get("id") in {"gmail-official", "google-calendar-official"}:
            google_ready = bool(
                os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
                and os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
            )
            item["oauth_available"] = google_ready
            item["oauth_connectable"] = True
            item["setup_label"] = "Connect with Google" if google_ready else "Google OAuth setup required"''',
        "Calendar catalog readiness",
    )

    # New local appointments become pending uploads; cancellation propagates after the next sync.
    backend = replace_once(
        backend,
        '''        "source": source,
        "created_at": now,''',
        '''        "source": source,
        "google_sync_state": "pending_create" if google_calendar_sync_store()["enabled"] else "local_only",
        "created_at": now,''',
        "Calendar create sync state",
    )
    backend = replace_once(
        backend,
        '''    appointment["status"] = "cancelled"
    appointment["updated_at"] = time.time()''',
        '''    appointment["status"] = "cancelled"
    appointment["google_sync_state"] = "pending_delete" if appointment.get("google_event_id") and google_calendar_sync_store()["enabled"] else appointment.get("google_sync_state", "local_only")
    appointment["updated_at"] = time.time()''',
        "Calendar cancel sync state",
    )

    backend = replace_once(
        backend,
        '    global PLUGIN_OAUTH_REFRESH_TASK, NOTIFICATION_WATCH_TASK, GRINDER_MONITOR_TASK, CALENDAR_REMINDER_TASK\n',
        '    global PLUGIN_OAUTH_REFRESH_TASK, NOTIFICATION_WATCH_TASK, GRINDER_MONITOR_TASK, CALENDAR_REMINDER_TASK, GOOGLE_CALENDAR_SYNC_TASK\n',
        "Calendar sync startup global",
    )
    backend = replace_once(
        backend,
        '''    if CALENDAR_REMINDER_TASK is None or CALENDAR_REMINDER_TASK.done():
        CALENDAR_REMINDER_TASK = asyncio.create_task(calendar_reminder_worker(), name="zbrano-calendar-reminders")''',
        '''    if CALENDAR_REMINDER_TASK is None or CALENDAR_REMINDER_TASK.done():
        CALENDAR_REMINDER_TASK = asyncio.create_task(calendar_reminder_worker(), name="zbrano-calendar-reminders")
    if GOOGLE_CALENDAR_SYNC_TASK is None or GOOGLE_CALENDAR_SYNC_TASK.done():
        GOOGLE_CALENDAR_SYNC_TASK = asyncio.create_task(google_calendar_sync_worker(), name="zbrano-google-calendar-sync")''',
        "Calendar sync worker startup",
    )
    backend = replace_once(
        backend,
        '    global PLUGIN_OAUTH_REFRESH_TASK, RELEASE_SYNC_TASK, NOTIFICATION_WATCH_TASK, GRINDER_MONITOR_TASK, CALENDAR_REMINDER_TASK\n',
        '    global PLUGIN_OAUTH_REFRESH_TASK, RELEASE_SYNC_TASK, NOTIFICATION_WATCH_TASK, GRINDER_MONITOR_TASK, CALENDAR_REMINDER_TASK, GOOGLE_CALENDAR_SYNC_TASK\n',
        "Calendar sync shutdown global",
    )
    backend = replace_once(
        backend,
        '''    if CALENDAR_REMINDER_TASK is not None:
        CALENDAR_REMINDER_TASK.cancel()''',
        '''    if GOOGLE_CALENDAR_SYNC_TASK is not None:
        GOOGLE_CALENDAR_SYNC_TASK.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await GOOGLE_CALENDAR_SYNC_TASK
        GOOGLE_CALENDAR_SYNC_TASK = None
    if CALENDAR_REMINDER_TASK is not None:
        CALENDAR_REMINDER_TASK.cancel()''',
        "Calendar sync worker shutdown",
    )
    backend = replace_once(
        backend,
        '''        add(
            "Plugin OAuth engine operational",''',
        '''        calendar_sync = google_calendar_sync_status()
        add(
            "Google Calendar Direct synchronization",
            "operational" if calendar_sync["connected"] and not calendar_sync["last_error"] else "setup_required" if not calendar_sync["connected"] else "degraded",
            f"connected={calendar_sync['connected']}; enabled={calendar_sync['enabled']}; pending={calendar_sync['pending_local_changes']}; last_success={calendar_sync['last_success_at'] or 'never'}",
            "calendar",
            "Connect Google Calendar Direct, preview the selected calendar, then enable synchronization.",
        )
        add(
            "Plugin OAuth engine operational",''',
        "Calendar diagnostics",
    )

    # Frontend: a dedicated Sync view with connection, preview and explicit enable controls.
    frontend = replace_once(
        frontend,
        '''        <button type="button" data-calendar-view="reminders" role="tab" aria-selected="false">Reminders</button>''',
        '''        <button type="button" data-calendar-view="reminders" role="tab" aria-selected="false">Reminders</button>
        <button type="button" data-calendar-view="sync" role="tab" aria-selected="false">Google Sync</button>''',
        "Calendar Sync tab",
    )
    sync_panel = r'''
      <section data-calendar-panel="sync" class="hidden">
        <article class="calendar-card calendar-google-sync">
          <div class="calendar-card-head"><div><h3>Google Calendar Direct</h3><p>Synchronize appointments through the standard Google Calendar API. ZBRANO reminders and Telegram delivery stay local.</p></div><span id="google-calendar-connection" class="calendar-sync-badge">Checking…</span></div>
          <div class="calendar-sync-grid">
            <label>Google calendar<select id="google-calendar-select"><option value="primary">Primary calendar</option></select></label>
            <div><strong>Last successful sync</strong><p id="google-calendar-last-sync">Never</p></div>
            <div><strong>Pending local changes</strong><p id="google-calendar-pending">0</p></div>
          </div>
          <div class="calendar-form-actions">
            <button id="google-calendar-connect" type="button">Connect with Google</button>
            <button id="google-calendar-preview" type="button">Preview first sync</button>
            <button id="google-calendar-enable" type="button">Enable sync</button>
            <button id="google-calendar-sync-now" type="button">Sync now</button>
          </div>
          <div id="google-calendar-preview-result" class="calendar-sync-preview">A preview is required before synchronization can be enabled. No appointments are changed during preview.</div>
          <p id="google-calendar-status" role="status" aria-live="polite"></p>
        </article>
      </section>
'''
    frontend = replace_once(
        frontend,
        '''      </section>
    </div>
  </section>

  <section id="automations-panel"''',
        '''      </section>
''' + sync_panel + '''    </div>
  </section>

  <section id="automations-panel"''',
        "Calendar Sync panel",
    )
    frontend = replace_once(
        frontend,
        '''    .calendar-subtabs button.active { border-color:var(--cyan); color:var(--cyan); }''',
        '''    .calendar-subtabs button.active { border-color:var(--cyan); color:var(--cyan); }
    .calendar-sync-grid { display:grid; grid-template-columns:minmax(220px,2fr) repeat(2,minmax(150px,1fr)); gap:.75rem; margin:1rem 0; }
    .calendar-sync-grid > * { padding:.75rem; border:1px solid var(--line); border-radius:10px; background:rgba(0,0,0,.08); }
    .calendar-sync-grid p { margin:.25rem 0 0; }
    .calendar-sync-badge { padding:.3rem .55rem; border:1px solid var(--line); border-radius:999px; color:var(--muted); }
    .calendar-sync-badge[data-connected="true"] { color:var(--cyan); border-color:var(--cyan); }
    .calendar-sync-preview { margin-top:.8rem; padding:.75rem; border-left:3px solid var(--line); color:var(--muted); }
    @media (max-width:720px) { .calendar-sync-grid { grid-template-columns:1fr; } }''',
        "Calendar Sync styles",
    )
    frontend = replace_once(
        frontend,
        '''  document.addEventListener("click",async event=>{
    const catalogButton=event.target.closest?.("button[data-oauth-connect]");''',
        '''  window.zbranoStartPluginOAuth = startPluginOAuth;

  document.addEventListener("click",async event=>{
    const catalogButton=event.target.closest?.("button[data-oauth-connect]");''',
        "shared OAuth popup controller",
    )

    sync_js = r'''

  async function loadGoogleCalendarSync() {
    const sync = await api("api/calendar/google/status");
    const connection = $("google-calendar-connection");
    connection.textContent = sync.connected ? (sync.enabled ? "Connected · Sync on" : "Connected · Paused") : "Not connected";
    connection.dataset.connected = String(Boolean(sync.connected));
    $("google-calendar-connect").hidden = Boolean(sync.connected);
    $("google-calendar-preview").disabled = !sync.connected;
    $("google-calendar-enable").disabled = !sync.connected;
    $("google-calendar-enable").textContent = sync.enabled ? "Pause sync" : "Enable sync";
    $("google-calendar-sync-now").disabled = !sync.connected || !sync.enabled;
    $("google-calendar-last-sync").textContent = sync.last_success_at ? formatDate(sync.last_success_at) : "Never";
    $("google-calendar-pending").textContent = String(sync.pending_local_changes || 0);
    $("google-calendar-status").textContent = sync.last_error ? `Last sync error: ${sync.last_error}` : "";
    const preview = sync.preview || {};
    if (sync.previewed_at) {
      $("google-calendar-preview-result").textContent = `Preview: ${preview.would_import || 0} Google event(s) to import, ${preview.would_upload || 0} ZBRANO appointment(s) to upload, ${preview.existing_links || 0} already linked.`;
    }
    const select = $("google-calendar-select");
    select.value = sync.calendar_id || "primary";
    if (sync.connected && select.options.length < 2) {
      const calendars = await api("api/calendar/google/calendars");
      select.replaceChildren();
      for (const item of calendars.calendars || []) select.appendChild(new Option(`${item.name}${item.primary ? " · Primary" : ""}`, item.id));
      if (![...select.options].some(item => item.value === sync.calendar_id)) select.appendChild(new Option(sync.calendar_name || "Primary calendar", sync.calendar_id || "primary"));
      select.value = sync.calendar_id || "primary";
    }
    return sync;
  }

  async function startGoogleCalendarOAuth() {
    if (typeof window.zbranoStartPluginOAuth !== "function") throw new Error("The secure OAuth controller is unavailable; refresh ZBRANO and try again");
    await window.zbranoStartPluginOAuth("api/plugin-catalog/google-calendar-official/oauth/start");
    $("google-calendar-status").textContent = "Complete authorization in the Google window.";
  }

  $("google-calendar-connect").addEventListener("click", async () => {
    try { await startGoogleCalendarOAuth(); }
    catch (error) { $("google-calendar-status").textContent = `Connection failed: ${error.message || error}`; }
  });
  $("google-calendar-select").addEventListener("change", async event => {
    try {
      await api("api/calendar/google/settings", {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({calendar_id:event.target.value, enabled:false})});
      $("google-calendar-preview-result").textContent = "Calendar changed. Preview is required before enabling synchronization.";
      await loadGoogleCalendarSync();
    } catch (error) { $("google-calendar-status").textContent = error.message || String(error); }
  });
  $("google-calendar-preview").addEventListener("click", async event => {
    event.currentTarget.disabled = true; $("google-calendar-status").textContent = "Reading both calendars without changing appointments…";
    try {
      const preview = await api("api/calendar/google/preview", {method:"POST"});
      $("google-calendar-preview-result").textContent = `Preview: ${preview.would_import || 0} Google event(s) to import, ${preview.would_upload || 0} ZBRANO appointment(s) to upload, ${preview.existing_links || 0} already linked.`;
      $("google-calendar-status").textContent = "Preview complete. Review the counts, then enable sync.";
    } catch (error) { $("google-calendar-status").textContent = `Preview failed: ${error.message || error}`; }
    finally { event.currentTarget.disabled = false; }
  });
  $("google-calendar-enable").addEventListener("click", async event => {
    event.currentTarget.disabled = true;
    try {
      const current = await api("api/calendar/google/status");
      const next = !current.enabled;
      await api("api/calendar/google/settings", {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({calendar_id:$("google-calendar-select").value, enabled:next})});
      if (next) await api("api/calendar/google/sync", {method:"POST"});
      await Promise.all([loadGoogleCalendarSync(), loadCalendar()]);
    } catch (error) { $("google-calendar-status").textContent = `Could not change sync: ${error.message || error}`; }
    finally { event.currentTarget.disabled = false; }
  });
  $("google-calendar-sync-now").addEventListener("click", async event => {
    event.currentTarget.disabled = true; $("google-calendar-status").textContent = "Synchronizing…";
    try { await api("api/calendar/google/sync", {method:"POST"}); await Promise.all([loadGoogleCalendarSync(), loadCalendar()]); $("google-calendar-status").textContent = "Synchronization complete."; }
    catch (error) { $("google-calendar-status").textContent = `Sync failed: ${error.message || error}`; }
    finally { event.currentTarget.disabled = false; }
  });
  window.addEventListener("message", event => {
    if (event.origin !== window.location.origin || event.data?.type !== "zbrano-plugin-oauth") return;
    window.setTimeout(() => loadGoogleCalendarSync().catch(() => {}), 500);
  });
'''
    frontend = replace_once(
        frontend,
        '''  tab.addEventListener("click", event => { event.preventDefault(); event.stopImmediatePropagation(); showCalendar(); }, true);''',
        sync_js + '''

  tab.addEventListener("click", event => { event.preventDefault(); event.stopImmediatePropagation(); showCalendar(); }, true);''',
        "Calendar Sync controller",
    )
    frontend = replace_once(
        frontend,
        '''    loadChannels().catch(() => {});
  }''',
        '''    loadChannels().catch(() => {});
    loadGoogleCalendarSync().catch(error => { $("google-calendar-status").textContent = `Google Calendar unavailable: ${error.message || error}`; });
  }''',
        "Calendar Sync load",
    )

    backend = backend.replace('version="0.12.85"', 'version="0.12.86"')
    backend = backend.replace('"version": "0.12.85"', '"version": "0.12.86"')
    frontend = frontend.replace("HUD 0.12.85", "HUD 0.12.86")

    for marker, label in [
        ("GOOGLE_CALENDAR_OAUTH_SCOPES", "Calendar scopes"),
        ("google_calendar_sync_once", "Calendar sync engine"),
        ('/api/calendar/google/preview', "Calendar preview API"),
        ('data-calendar-view="sync"', "Calendar Sync tab"),
        ('id="google-calendar-connect"', "Calendar connect control"),
        ('version="0.12.86"', "backend version"),
        ("HUD 0.12.86", "frontend version"),
    ]:
        require(backend if label not in {"Calendar Sync tab", "Calendar connect control", "frontend version"} else frontend, marker, label)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
