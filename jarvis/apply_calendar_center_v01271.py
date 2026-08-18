import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.71 expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.71 patch missing: {label}")


def patch_backend(backend: str) -> str:
    models = r'''class CalendarAppointmentRequest(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    start_at: str = Field(min_length=10, max_length=64)
    duration_minutes: int = Field(default=60, ge=5, le=10080)
    location: str = Field(default="", max_length=300)
    notes: str = Field(default="", max_length=3000)
    destination: str = Field(default="", max_length=255, pattern=r"^(|notify\.[a-z0-9_]+)$")
    reminder_offsets_minutes: list[int] = Field(default_factory=list, max_length=8)


'''
    backend = replace_once(
        backend,
        "class SettingsRestoreRequest(BaseModel):\n",
        models + "class SettingsRestoreRequest(BaseModel):\n",
        "calendar request model",
    )

    calendar_tools = r'''    {
        "type": "function",
        "name": "create_calendar_appointment",
        "description": (
            "Create a ZBRANO calendar appointment after the user explicitly asks for it and all essential "
            "details are known. If the date, start time, or reminder preference is missing, ask one concise "
            "follow-up question before calling this tool. DD.MM.YYYY means day-month-year and HH.MM means "
            "local 24-hour time. The explicit request authorizes creation without another approval prompt."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short appointment title."},
                "start_at": {"type": "string", "description": "ISO-8601 appointment start, preferably with the user's local UTC offset."},
                "duration_minutes": {"type": "integer", "description": "Duration in minutes; use 60 when the user accepts the default."},
                "location": {"type": "string", "description": "Optional location, or an empty string."},
                "notes": {"type": "string", "description": "Optional notes, or an empty string."},
                "destination": {"type": "string", "description": "Optional notify entity; blank uses Notification Center default."},
                "reminder_offsets_minutes": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Minutes before start. Same day defaults to 120, day before to 1440, both to [1440,120], and [] means no reminder."
                }
            },
            "required": ["title", "start_at", "duration_minutes", "location", "notes", "destination", "reminder_offsets_minutes"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "list_calendar_appointments",
        "description": "List ZBRANO calendar appointments and reminder delivery state. Use this before answering schedule questions or cancelling an appointment.",
        "parameters": {
            "type": "object",
            "properties": {"include_past": {"type": "boolean", "description": "Include completed past appointments when true."}},
            "required": ["include_past"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "cancel_calendar_appointment",
        "description": "Cancel one ZBRANO calendar appointment by exact ID after the user explicitly asks to cancel or delete it. List appointments first if the ID is unknown or the title is ambiguous.",
        "parameters": {
            "type": "object",
            "properties": {"appointment_id": {"type": "string", "description": "Exact appointment ID returned by list_calendar_appointments."}},
            "required": ["appointment_id"],
            "additionalProperties": False
        },
        "strict": True
    },
'''
    backend = replace_once(
        backend,
        "WORKSHOP_TOOLS: list[dict[str, Any]] = [\n",
        "WORKSHOP_TOOLS: list[dict[str, Any]] = [\n" + calendar_tools,
        "calendar chat tools",
    )

    calendar_backend = r'''CALENDAR_STORAGE_PATH = Path("/data/zbrano_calendar.json")
CALENDAR_REMINDER_TASK: asyncio.Task[Any] | None = None
CALENDAR_MAX_APPOINTMENTS = 500
CALENDAR_REMINDER_OFFSETS = {
    0: "At appointment time",
    30: "30 minutes before",
    120: "Same day · 2 hours before",
    1440: "One day before",
    10080: "One week before",
}


def calendar_store() -> dict[str, Any]:
    data = _plugin_load(CALENDAR_STORAGE_PATH) or {}
    appointments = data.get("appointments") if isinstance(data.get("appointments"), list) else []
    return {"version": 1, "appointments": appointments[:CALENDAR_MAX_APPOINTMENTS]}


def _calendar_save(data: dict[str, Any]) -> None:
    appointments = list(data.get("appointments") or [])[:CALENDAR_MAX_APPOINTMENTS]
    appointments.sort(key=lambda item: float(item.get("start_timestamp") or 0))
    _plugin_save(CALENDAR_STORAGE_PATH, {"version": 1, "appointments": appointments})


def _calendar_start(value: str) -> tuple[Any, float]:
    from datetime import datetime

    raw = str(value or "").strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Appointment start must be a valid ISO-8601 date and time") from exc
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    timestamp = parsed.timestamp()
    if timestamp < time.time() - 60:
        raise HTTPException(status_code=400, detail="Appointment start must be in the future")
    return parsed, timestamp


def _calendar_public(appointment: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in appointment.items()
        if key not in {"last_error"} or value
    }


def list_calendar_appointments(include_past: bool = False) -> dict[str, Any]:
    now = time.time()
    appointments = [
        _calendar_public(item) for item in calendar_store()["appointments"]
        if item.get("status") != "cancelled"
        and (include_past or float(item.get("end_timestamp") or item.get("start_timestamp") or 0) >= now)
    ]
    appointments.sort(key=lambda item: float(item.get("start_timestamp") or 0))
    return {"appointments": appointments, "count": len(appointments), "generated_at": now}


async def _create_calendar_appointment(request: CalendarAppointmentRequest, source: str = "interface") -> dict[str, Any]:
    import secrets

    parsed, start_timestamp = _calendar_start(request.start_at)
    offsets = sorted({int(value) for value in request.reminder_offsets_minutes}, reverse=True)
    if any(value < 0 or value > 525600 for value in offsets):
        raise HTTPException(status_code=400, detail="Reminder offsets must be between 0 and 525600 minutes")
    destination = request.destination.strip().lower() or str(notification_store()["settings"].get("default_channel") or "")
    if offsets:
        channels = await notification_channels()
        if not destination:
            raise HTTPException(status_code=400, detail="Choose a default Notification Center channel before adding reminders")
        if not any(item["entity_id"] == destination for item in channels):
            raise HTTPException(status_code=400, detail="Calendar reminder destination is unavailable")

    data = calendar_store()
    normalized_title = " ".join(request.title.split())
    duplicate = next((
        item for item in data["appointments"]
        if item.get("status") != "cancelled"
        and str(item.get("title") or "").casefold() == normalized_title.casefold()
        and abs(float(item.get("start_timestamp") or 0) - start_timestamp) < 60
    ), None)
    if duplicate:
        return {"created": False, "deduplicated": True, "appointment": _calendar_public(duplicate)}

    now = time.time()
    appointment_id = secrets.token_hex(12)
    reminders = [
        {
            "id": secrets.token_hex(8),
            "offset_minutes": offset,
            "label": CALENDAR_REMINDER_OFFSETS.get(offset, f"{offset} minutes before"),
            "due_at": start_timestamp - offset * 60,
            "status": "scheduled",
            "last_attempt_at": 0.0,
            "delivered_at": 0.0,
        }
        for offset in offsets
    ]
    appointment = {
        "id": appointment_id,
        "title": normalized_title,
        "start_at": parsed.isoformat(),
        "start_timestamp": start_timestamp,
        "end_timestamp": start_timestamp + request.duration_minutes * 60,
        "duration_minutes": request.duration_minutes,
        "location": request.location.strip(),
        "notes": request.notes.strip(),
        "destination": destination,
        "status": "scheduled",
        "source": source,
        "created_at": now,
        "updated_at": now,
        "reminders": reminders,
    }
    data["appointments"].append(appointment)
    _calendar_save(data)
    return {"created": True, "deduplicated": False, "appointment": _calendar_public(appointment)}


def _cancel_calendar_appointment(appointment_id: str) -> dict[str, Any]:
    data = calendar_store()
    appointment = next((item for item in data["appointments"] if item.get("id") == appointment_id), None)
    if not appointment:
        raise HTTPException(status_code=404, detail="Calendar appointment not found")
    appointment["status"] = "cancelled"
    appointment["updated_at"] = time.time()
    for reminder in appointment.get("reminders") or []:
        if reminder.get("status") == "scheduled":
            reminder["status"] = "cancelled"
    _calendar_save(data)
    return {"cancelled": True, "appointment": _calendar_public(appointment)}


def _calendar_reminder_message(appointment: dict[str, Any], reminder: dict[str, Any]) -> str:
    from datetime import datetime

    local_start = datetime.fromtimestamp(float(appointment.get("start_timestamp") or 0)).astimezone()
    when = local_start.strftime("%A, %d %B %Y at %H:%M")
    parts = [f"{appointment.get('title')}", f"When: {when}"]
    if appointment.get("location"):
        parts.append(f"Where: {appointment['location']}")
    if reminder.get("label"):
        parts.append(f"Reminder: {reminder['label']}")
    return "\n".join(parts)


async def calendar_reminder_worker() -> None:
    while True:
        await asyncio.sleep(15.0)
        data = calendar_store()
        now = time.time()
        changed = False
        pending_deliveries: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = []
        for appointment in data["appointments"]:
            if appointment.get("status") != "scheduled":
                continue
            if now >= float(appointment.get("end_timestamp") or 0):
                appointment["status"] = "completed"
                appointment["updated_at"] = now
                for reminder in appointment.get("reminders") or []:
                    if reminder.get("status") == "scheduled":
                        reminder["status"] = "missed"
                changed = True
                continue
            for reminder in appointment.get("reminders") or []:
                if reminder.get("status") != "scheduled" or now < float(reminder.get("due_at") or 0):
                    continue
                due_at = float(reminder.get("due_at") or 0)
                if now - due_at > 86400:
                    reminder["status"] = "missed"
                    changed = True
                    continue
                if now - float(reminder.get("last_attempt_at") or 0) < 60:
                    continue
                reminder["last_attempt_at"] = now
                changed = True
                if _notification_quiet_now("information", now):
                    reminder["status"] = "suppressed"
                    continue
                appointment["updated_at"] = time.time()
                pending_deliveries.append((
                    str(appointment.get("id") or ""), str(reminder.get("id") or ""),
                    dict(appointment), dict(reminder),
                ))
        if changed:
            _calendar_save(data)
        for appointment_id, reminder_id, appointment, reminder in pending_deliveries:
            delivered = False
            error = ""
            try:
                await test_notification_channel(NotificationTestRequest(
                    target=str(appointment.get("destination") or ""),
                    severity="information",
                    title=f"Calendar · {appointment.get('title')}",
                    message=_calendar_reminder_message(appointment, reminder),
                ))
                delivered = True
            except (HTTPException, RuntimeError, OSError, ValueError) as exc:
                error = str(getattr(exc, "detail", exc))[:500]
            fresh = calendar_store()
            fresh_appointment = next((item for item in fresh["appointments"] if item.get("id") == appointment_id), None)
            fresh_reminder = next((
                item for item in (fresh_appointment.get("reminders") or [])
                if item.get("id") == reminder_id
            ), None) if fresh_appointment else None
            if not fresh_reminder:
                continue
            if delivered:
                fresh_reminder["status"] = "delivered"
                fresh_reminder["delivered_at"] = time.time()
                fresh_reminder.pop("last_error", None)
            else:
                fresh_reminder["status"] = "scheduled"
                fresh_reminder["last_error"] = error
            fresh_appointment["updated_at"] = time.time()
            _calendar_save(fresh)


@app.get("/api/calendar")
async def read_calendar(include_past: bool = False) -> dict[str, Any]:
    result = list_calendar_appointments(include_past)
    settings = notification_store()["settings"]
    result["default_destination"] = str(settings.get("default_channel") or "")
    result["reminder_presets"] = [
        {"offset_minutes": value, "label": label}
        for value, label in sorted(CALENDAR_REMINDER_OFFSETS.items(), reverse=True)
    ]
    return result


@app.post("/api/calendar")
async def create_calendar_appointment(request: CalendarAppointmentRequest) -> dict[str, Any]:
    return await _create_calendar_appointment(request)


@app.delete("/api/calendar/{appointment_id}")
async def cancel_calendar_appointment(appointment_id: str) -> dict[str, Any]:
    return _cancel_calendar_appointment(appointment_id)


'''
    backend = replace_once(
        backend,
        "NOTIFICATION_WATCH_TASK: asyncio.Task[Any] | None = None\n",
        calendar_backend + "NOTIFICATION_WATCH_TASK: asyncio.Task[Any] | None = None\n",
        "calendar backend",
    )

    backend = replace_once(
        backend,
        '''                if name == "get_grinder_diagnostic_status":
                    result = grinder_monitor_status()''',
        '''                if name == "create_calendar_appointment":
                    result = await _create_calendar_appointment(CalendarAppointmentRequest(**arguments), source="chat")
                elif name == "list_calendar_appointments":
                    result = list_calendar_appointments(bool(arguments.get("include_past")))
                elif name == "cancel_calendar_appointment":
                    result = _cancel_calendar_appointment(str(arguments.get("appointment_id") or ""))
                elif name == "get_grinder_diagnostic_status":
                    result = grinder_monitor_status()''',
        "calendar tool execution",
    )

    calendar_instructions = r'''CALENDAR_INTENT_TERMS = (
    "calendar", "appointment", "dentist", "doctor", "meeting", "reservation",
    "schedule", "reschedule", "agenda", "remind me on", "remind me at",
)


def is_calendar_intent(message: str) -> bool:
    normalized = " ".join(str(message or "").casefold().split())
    if any(term in normalized for term in CALENDAR_INTENT_TERMS):
        return True
    has_date = bool(re.search(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{4}\b", normalized))
    has_time = bool(re.search(r"\b(?:[01]?\d|2[0-3])[:.]\d{2}\b", normalized))
    return has_date and has_time


def calendar_priority_tools() -> list[dict[str, Any]]:
    names = {"create_calendar_appointment", "list_calendar_appointments", "cancel_calendar_appointment"}
    return [tool for tool in WORKSHOP_TOOLS if str(tool.get("name") or "") in names]


def calendar_system_instructions(base: str) -> str:
    return base + """

ZBRANO CALENDAR WORKFLOW.
When the user gives an appointment or dated event, collect only missing essentials before creating it: title,
calendar date, start time, and reminder preference. Treat DD.MM.YYYY as day-month-year and HH.MM as local
24-hour time. Treat a terse title plus date and time as an explicit request to add that appointment. Do not invent
a UTC offset when it is unknown; preserve the user's local wall-clock time. Duration defaults to 60 minutes and
location is optional; mention those defaults instead of asking unnecessary questions. If reminder timing is absent,
ask: same day (default two hours before), one day before,
both, custom timing, or none. Use offsets 120, 1440, [1440, 120], a user-specified minute offset, or []. Once the
user explicitly asks to add the appointment and the missing details are resolved, call create_calendar_appointment
without another approval prompt. Never claim it was saved unless the tool succeeds. Use list_calendar_appointments
for schedule questions and before cancelling an ambiguous event. Calendar reminders are delivered through the
Notification Center default channel, including Telegram when configured.
""".strip()


'''
    backend = replace_once(
        backend,
        "def priority_system_instructions(base: str, message: str) -> str:\n",
        calendar_instructions + '''def priority_system_instructions(base: str, message: str) -> str:
    if not developer_mode_enabled():
        base = calendar_system_instructions(base)
''',
        "calendar conversation instructions",
    )
    backend = replace_once(
        backend,
        '''    if is_grinder_diagnostic_intent(message):
        return grinder_priority_tools()
    if is_home_assistant_priority_intent(message):''',
        '''    if is_grinder_diagnostic_intent(message):
        return grinder_priority_tools()
    if is_calendar_intent(message):
        return calendar_priority_tools()
    if is_home_assistant_priority_intent(message):''',
        "calendar priority routing",
    )

    backend = replace_once(
        backend,
        '    global PLUGIN_OAUTH_REFRESH_TASK, NOTIFICATION_WATCH_TASK, GRINDER_MONITOR_TASK\n',
        '    global PLUGIN_OAUTH_REFRESH_TASK, NOTIFICATION_WATCH_TASK, GRINDER_MONITOR_TASK, CALENDAR_REMINDER_TASK\n',
        "calendar startup global",
    )
    backend = replace_once(
        backend,
        '''    schedule_release_sync()
    if GRINDER_MONITOR_ENABLED''',
        '''    schedule_release_sync()
    if CALENDAR_REMINDER_TASK is None or CALENDAR_REMINDER_TASK.done():
        CALENDAR_REMINDER_TASK = asyncio.create_task(calendar_reminder_worker(), name="zbrano-calendar-reminders")
    if GRINDER_MONITOR_ENABLED''',
        "calendar worker startup",
    )
    backend = replace_once(
        backend,
        '    global PLUGIN_OAUTH_REFRESH_TASK, RELEASE_SYNC_TASK, NOTIFICATION_WATCH_TASK, GRINDER_MONITOR_TASK\n',
        '    global PLUGIN_OAUTH_REFRESH_TASK, RELEASE_SYNC_TASK, NOTIFICATION_WATCH_TASK, GRINDER_MONITOR_TASK, CALENDAR_REMINDER_TASK\n',
        "calendar shutdown global",
    )
    backend = replace_once(
        backend,
        '''    if GRINDER_MONITOR_TASK is not None:
        GRINDER_MONITOR_TASK.cancel()''',
        '''    if CALENDAR_REMINDER_TASK is not None:
        CALENDAR_REMINDER_TASK.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await CALENDAR_REMINDER_TASK
        CALENDAR_REMINDER_TASK = None
    if GRINDER_MONITOR_TASK is not None:
        GRINDER_MONITOR_TASK.cancel()''',
        "calendar worker shutdown",
    )

    backend = replace_once(
        backend,
        '        "notifications": notification_store(),\n',
        '        "notifications": notification_store(),\n        "calendar": calendar_store(),\n',
        "calendar backup export",
    )
    backend = replace_once(
        backend,
        '    notifications = backup.get("notifications")\n',
        '    notifications = backup.get("notifications")\n    calendar = backup.get("calendar")\n',
        "calendar backup restore input",
    )
    backend = replace_once(
        backend,
        '''    if notifications is not None and (
        not isinstance(notifications, dict)
        or not isinstance(notifications.get("settings"), dict)
        or not isinstance(notifications.get("deliveries", []), list)
    ):
        raise HTTPException(status_code=400, detail="Backup notification data is malformed")''',
        '''    if notifications is not None and (
        not isinstance(notifications, dict)
        or not isinstance(notifications.get("settings"), dict)
        or not isinstance(notifications.get("deliveries", []), list)
    ):
        raise HTTPException(status_code=400, detail="Backup notification data is malformed")
    if calendar is not None and (
        not isinstance(calendar, dict)
        or not isinstance(calendar.get("appointments", []), list)
    ):
        raise HTTPException(status_code=400, detail="Backup calendar data is malformed")''',
        "calendar backup validation",
    )
    backend = replace_once(
        backend,
        '''    if notifications is not None:
        _notification_save(notifications)
    load_chat_sessions()''',
        '''    if notifications is not None:
        _notification_save(notifications)
    if calendar is not None:
        _calendar_save(calendar)
    load_chat_sessions()''',
        "calendar backup persistence",
    )

    backend = replace_once(
        backend,
        '            "notifications": _tab_activity_revision(NOTIFICATION_STORAGE_PATH),\n',
        '            "notifications": _tab_activity_revision(NOTIFICATION_STORAGE_PATH),\n            "calendar": _tab_activity_revision(CALENDAR_STORAGE_PATH),\n',
        "calendar tab activity revision",
    )

    diagnostic_marker = '''        await probe(
            "Notification Center API operational",
            "/api/notifications",
            lambda payload: (
                "operational" if isinstance(payload, dict) and isinstance(payload.get("channels"), list) else "failed",
                f"{len(payload.get('channels', [])) if isinstance(payload, dict) else 0} Home Assistant notify channels; {payload.get('telegram_channels', 0) if isinstance(payload, dict) else 0} Telegram; {len(payload.get('watches', [])) if isinstance(payload, dict) else 0} event-driven watches",
            ),
            "automations",
        )
'''
    require(backend, diagnostic_marker, "calendar diagnostics insertion")
    backend = backend.replace(
        diagnostic_marker,
        diagnostic_marker + '''
        await probe(
            "Calendar and reminders API operational",
            "/api/calendar",
            lambda payload: (
                "operational" if isinstance(payload, dict) and isinstance(payload.get("appointments"), list) else "failed",
                f"{len(payload.get('appointments', [])) if isinstance(payload, dict) else 0} upcoming appointments; reminder worker configured",
            ),
            "calendar",
        )
''',
        1,
    )
    backend = replace_once(
        backend,
        '''            "Notification Center frontend wired": ('data-auto-view="notifications"', 'id="notification-settings-form"', 'zbrano-v01243-notification-center'),''',
        '''            "Notification Center frontend wired": ('data-auto-view="notifications"', 'id="notification-settings-form"', 'zbrano-v01243-notification-center'),
            "Calendar frontend wired": ('id="calendar-tab"', 'id="calendar-panel"', 'zbrano-v01271-calendar-center'),''',
        "calendar frontend diagnostics",
    )

    backend = backend.replace('version="0.12.70"', 'version="0.12.71"')
    backend = backend.replace('"version": "0.12.70"', '"version": "0.12.71"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.70"', '"X-ZBRANO-Frontend-Version": "0.12.71"')
    backend = backend.replace(
        '"name": "ZBRANO Developer Mode", "version": "0.12.70"',
        '"name": "ZBRANO Developer Mode", "version": "0.12.71"',
    )
    return backend


def patch_frontend(frontend: str) -> str:
    calendar_icon = '''      <button id="calendar-quick-open" class="calendar-quick-open" type="button" aria-label="Open ZBRANO Calendar" title="Open Calendar">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 2v3M17 2v3M3.5 9h17M5.5 4h13a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z"/><path d="M8 13h3v3H8z"/></svg>
        <span id="calendar-quick-count" aria-label="No upcoming appointments">0</span>
      </button>
'''
    frontend = replace_once(
        frontend,
        '    <div class="runtime-status-stack">\n',
        '    <div class="runtime-status-stack">\n' + calendar_icon,
        "calendar header icon",
    )
    frontend = replace_once(
        frontend,
        '    <button id="entities-tab">Entities</button>\n    <button id="automations-tab">Automations</button>',
        '    <button id="entities-tab">Entities</button>\n    <button id="calendar-tab">Calendar</button>\n    <button id="automations-tab">Automations</button>',
        "calendar primary tab",
    )

    calendar_panel = r'''  <section id="calendar-panel" class="panel hidden">
    <div class="calendar-shell">
      <div class="calendar-heading">
        <div><h2>CALENDAR</h2><p>Appointments and Telegram-capable reminders managed by ZBRANO.</p></div>
        <button id="calendar-refresh" type="button">Refresh</button>
      </div>
      <div class="calendar-subtabs" role="tablist" aria-label="Calendar views">
        <button class="active" type="button" data-calendar-view="upcoming" role="tab" aria-selected="true">Upcoming</button>
        <button type="button" data-calendar-view="reminders" role="tab" aria-selected="false">Reminders</button>
      </div>
      <section data-calendar-panel="upcoming">
        <div class="calendar-layout">
          <article class="calendar-card calendar-editor-card">
            <h3>Add appointment</h3>
            <p>ZBRANO chat can collect these details conversationally, or you can add them here.</p>
            <form id="calendar-form">
              <label>Title<input id="calendar-title" maxlength="160" required placeholder="Dentist"></label>
              <div class="calendar-form-row">
                <label>Date<input id="calendar-date" type="date" required></label>
                <label>Time<input id="calendar-time" type="time" required></label>
                <label>Duration<input id="calendar-duration" type="number" min="5" max="10080" value="60"><span>minutes</span></label>
              </div>
              <label>Location<input id="calendar-location" maxlength="300" placeholder="Optional"></label>
              <label>Notes<textarea id="calendar-notes" rows="2" maxlength="3000" placeholder="Optional"></textarea></label>
              <fieldset class="calendar-reminder-options">
                <legend>Remind me</legend>
                <label><input type="checkbox" value="1440" checked> One day before</label>
                <label><input type="checkbox" value="120" checked> Same day · 2 hours before</label>
                <label><input type="checkbox" value="30"> 30 minutes before</label>
                <label><input type="checkbox" value="0"> At appointment time</label>
              </fieldset>
              <label>Notification channel<select id="calendar-destination"><option value="">Notification Center default</option></select></label>
              <div class="calendar-form-actions"><button type="submit">Add appointment</button><span id="calendar-form-status" role="status"></span></div>
            </form>
          </article>
          <article class="calendar-card calendar-upcoming-card">
            <div class="calendar-card-head"><div><h3>Upcoming appointments</h3><p id="calendar-summary">Loading calendar…</p></div></div>
            <div id="calendar-appointments" class="calendar-appointment-list"></div>
          </article>
        </div>
      </section>
      <section data-calendar-panel="reminders" class="hidden">
        <article class="calendar-card">
          <div class="calendar-card-head"><div><h3>Calendar reminders</h3><p>Scheduled and delivered reminders for your appointments.</p></div></div>
          <div id="calendar-reminders" class="calendar-reminder-list"></div>
        </article>
      </section>
    </div>
  </section>

'''
    frontend = replace_once(
        frontend,
        '  <section id="automations-panel" class="panel hidden">\n',
        calendar_panel + '  <section id="automations-panel" class="panel hidden">\n',
        "calendar panel",
    )

    calendar_css = r'''
    /* v0.12.71 calendar center. */
    .calendar-quick-open {
      position:relative; display:inline-grid; place-items:center; width:2rem; height:2rem; min-width:2rem;
      padding:0; border-radius:50%; color:var(--cyan); justify-self:end;
    }
    .calendar-quick-open svg { width:1.05rem; height:1.05rem; fill:none; stroke:currentColor; stroke-width:1.7; stroke-linecap:round; stroke-linejoin:round; }
    #calendar-quick-count { position:absolute; right:-.35rem; top:-.35rem; min-width:1.05rem; height:1.05rem; padding:0 .2rem; display:grid; place-items:center; border-radius:999px; background:#db8b31; color:#17120b; font-size:.58rem; font-weight:750; }
    #calendar-quick-count[data-empty="true"] { display:none; }
    #calendar-panel { min-height:0; overflow:auto; overscroll-behavior:contain; scrollbar-gutter:stable; }
    #calendar-panel::before { display:none; }
    .calendar-shell { display:grid; gap:.75rem; min-width:0; padding-bottom:1rem; }
    .calendar-heading,.calendar-card-head { display:flex; justify-content:space-between; align-items:flex-start; gap:.75rem; }
    .calendar-heading h2,.calendar-card h3 { margin:.05rem 0 .25rem; }
    .calendar-heading p,.calendar-card p { margin:.15rem 0; color:var(--text-muted); }
    .calendar-subtabs { display:flex; flex-wrap:wrap; gap:.4rem; padding-bottom:.55rem; border-bottom:1px solid var(--line); }
    .calendar-subtabs button.active { border-color:var(--cyan); color:var(--cyan); }
    [data-calendar-panel].hidden { display:none; }
    .calendar-layout { display:grid; grid-template-columns:minmax(18rem,.78fr) minmax(22rem,1.22fr); gap:.75rem; }
    .calendar-card { min-width:0; padding:.85rem; border:1px solid var(--line); border-radius:8px; background:color-mix(in srgb,var(--panel) 88%,transparent); }
    #calendar-form { display:grid; gap:.62rem; margin-top:.75rem; }
    #calendar-form label { display:grid; gap:.28rem; min-width:0; }
    #calendar-form input,#calendar-form select,#calendar-form textarea { width:100%; min-width:0; max-width:100%; }
    .calendar-form-row { display:grid; grid-template-columns:1fr 1fr .8fr; gap:.5rem; }
    .calendar-form-row label span { color:var(--text-muted); font-size:.68rem; }
    .calendar-reminder-options { display:grid; gap:.4rem; margin:0; padding:.65rem; border:1px solid var(--line); border-radius:7px; }
    .calendar-reminder-options label { display:flex !important; align-items:center; gap:.45rem; }
    .calendar-reminder-options input { width:auto !important; flex:0 0 auto; }
    .calendar-form-actions { display:flex; align-items:center; flex-wrap:wrap; gap:.65rem; }
    .calendar-appointment-list,.calendar-reminder-list { display:grid; gap:.55rem; margin-top:.75rem; }
    .calendar-appointment,.calendar-reminder { display:grid; gap:.42rem; min-width:0; padding:.7rem; border:1px solid var(--line); border-radius:7px; }
    .calendar-appointment-head { display:flex; justify-content:space-between; align-items:flex-start; gap:.6rem; }
    .calendar-appointment-title { min-width:0; font-weight:650; overflow-wrap:anywhere; }
    .calendar-appointment-time { color:var(--cyan); font-size:.82rem; }
    .calendar-meta,.calendar-reminder-badges { display:flex; flex-wrap:wrap; gap:.35rem; color:var(--text-muted); font-size:.72rem; }
    .calendar-reminder-badge { padding:.14rem .42rem; border:1px solid var(--line); border-radius:999px; }
    .calendar-reminder-badge[data-status="delivered"] { color:#39d6a1; }
    .calendar-reminder-badge[data-status="failed"],.calendar-reminder-badge[data-status="missed"] { color:#ef765f; }
    .calendar-cancel { flex:0 0 auto; padding:.32rem .5rem; font-size:.72rem; }
    .calendar-empty { padding:1rem; border:1px dashed var(--line); border-radius:7px; color:var(--text-muted); text-align:center; }
    @media(max-width:900px) { .calendar-layout { grid-template-columns:1fr; } }
    @media(max-width:620px) {
      .calendar-quick-open { width:1.75rem; height:1.75rem; min-width:1.75rem; }
      .calendar-form-row { grid-template-columns:1fr 1fr; }
      .calendar-form-row label:last-child { grid-column:1/-1; }
      .calendar-card { padding:.65rem; }
      .calendar-heading { align-items:center; }
    }
'''
    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.71 could not locate the stylesheet close")
    frontend = frontend[:style_close] + calendar_css + frontend[style_close:]

    frontend = replace_once(
        frontend,
        '''  const showAutomations = panel === "automations";
  chatPanel.classList.toggle("hidden", !showChat);''',
        '''  const showAutomations = panel === "automations";
  const showCalendar = panel === "calendar";
  chatPanel.classList.toggle("hidden", !showChat);''',
        "calendar showPanel state",
    )
    frontend = replace_once(
        frontend,
        '''  document.getElementById("automations-panel")?.classList.toggle("hidden", !showAutomations);
  chatTab.classList.toggle("active", showChat);''',
        '''  document.getElementById("automations-panel")?.classList.toggle("hidden", !showAutomations);
  document.getElementById("calendar-panel")?.classList.toggle("hidden", !showCalendar);
  chatTab.classList.toggle("active", showChat);''',
        "calendar panel toggle",
    )
    frontend = replace_once(
        frontend,
        '''  document.getElementById("automations-tab")?.classList.toggle("active", showAutomations);
}''',
        '''  document.getElementById("automations-tab")?.classList.toggle("active", showAutomations);
  document.getElementById("calendar-tab")?.classList.toggle("active", showCalendar);
}''',
        "calendar tab toggle",
    )

    frontend = frontend.replace(
        '["chat-panel", "entities-panel", "settings-panel", "plugins-panel", "files-panel"]',
        '["chat-panel", "entities-panel", "settings-panel", "plugins-panel", "files-panel", "calendar-panel"]',
    )
    frontend = frontend.replace(
        '["chat-tab", "entities-tab", "settings-tab", "plugins-tab", "files-tab"]',
        '["chat-tab", "entities-tab", "settings-tab", "plugins-tab", "files-tab", "calendar-tab"]',
    )
    frontend = frontend.replace(
        '["chat-panel", "entities-panel", "settings-panel", "plugins-panel", "files-panel", "developer-panel"]',
        '["chat-panel", "entities-panel", "settings-panel", "plugins-panel", "files-panel", "calendar-panel", "developer-panel"]',
    )
    frontend = frontend.replace(
        '["chat-tab", "entities-tab", "settings-tab", "plugins-tab", "files-tab", "developer-tab"]',
        '["chat-tab", "entities-tab", "settings-tab", "plugins-tab", "files-tab", "calendar-tab", "developer-tab"]',
    )
    frontend = frontend.replace(
        '["chat-panel","entities-panel","settings-panel","plugins-panel","files-panel","developer-panel","automations-panel"]',
        '["chat-panel","entities-panel","settings-panel","plugins-panel","files-panel","calendar-panel","developer-panel","automations-panel"]',
    )
    frontend = frontend.replace(
        '["chat-tab","entities-tab","settings-tab","plugins-tab","files-tab","developer-tab","automations-tab"]',
        '["chat-tab","entities-tab","settings-tab","plugins-tab","files-tab","calendar-tab","developer-tab","automations-tab"]',
    )
    frontend = frontend.replace(
        '"#chat-tab,#entities-tab,#settings-tab,#plugins-tab,#files-tab,#developer-tab"',
        '"#chat-tab,#entities-tab,#settings-tab,#plugins-tab,#files-tab,#calendar-tab,#developer-tab"',
    )
    frontend = frontend.replace(
        '["chat", "files", "plugins", "entities", "automations", "settings", "developer"]',
        '["chat", "files", "plugins", "entities", "calendar", "automations", "settings", "developer"]',
    )
    frontend = frontend.replace(
        '"#chat-tab,#files-tab,#plugins-tab,#entities-tab,#automations-tab,#settings-tab,#developer-tab,',
        '"#chat-tab,#files-tab,#plugins-tab,#entities-tab,#calendar-tab,#automations-tab,#settings-tab,#developer-tab,',
    )
    frontend = replace_once(
        frontend,
        '''    notifications: ["#automations-tab", '[data-auto-view="notifications"]', '[data-notification-view="logs"]'],
    settings: ["#settings-tab"],''',
        '''    notifications: ["#automations-tab", '[data-auto-view="notifications"]', '[data-notification-view="logs"]'],
    calendar: ["#calendar-tab"],
    settings: ["#settings-tab"],''',
        "calendar semantic activity target",
    )
    frontend = replace_once(
        frontend,
        '''        if (path.includes("/api/notifications")) {
          markIfUnseen(document.getElementById("automations-tab"));''',
        '''        if (path.includes("/api/calendar")) markIfUnseen(document.getElementById("calendar-tab"));
        if (path.includes("/api/notifications")) {
          markIfUnseen(document.getElementById("automations-tab"));''',
        "calendar write activity",
    )

    calendar_runtime = r'''
<script id="zbrano-v01271-calendar-center">
(() => {
  const tab = document.getElementById("calendar-tab");
  const panel = document.getElementById("calendar-panel");
  const quick = document.getElementById("calendar-quick-open");
  if (!tab || !panel || !quick) return;
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"})[char]);
  let state = {appointments:[], default_destination:""};

  async function api(path, options={}) {
    const response = await fetch(path, {cache:"no-store", ...options});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    return data;
  }

  function formatDate(timestamp) {
    return new Date(Number(timestamp) * 1000).toLocaleString([], {weekday:"short", year:"numeric", month:"short", day:"numeric", hour:"2-digit", minute:"2-digit"});
  }

  function reminderBadge(reminder) {
    const status = reminder.status || "scheduled";
    return `<span class="calendar-reminder-badge" data-status="${esc(status)}">${esc(reminder.label || "Reminder")} · ${esc(status)}</span>`;
  }

  function renderAppointments() {
    const root = $("calendar-appointments");
    const appointments = state.appointments || [];
    root.replaceChildren();
    $("calendar-summary").textContent = `${appointments.length} upcoming appointment${appointments.length === 1 ? "" : "s"}`;
    if (!appointments.length) {
      root.innerHTML = '<div class="calendar-empty">No upcoming appointments. Ask ZBRANO to add one or use the form.</div>';
      return;
    }
    for (const item of appointments) {
      const node = document.createElement("div");
      node.className = "calendar-appointment";
      const meta = [item.location, `${Number(item.duration_minutes || 60)} minutes`].filter(Boolean);
      node.innerHTML = `<div class="calendar-appointment-head"><div><div class="calendar-appointment-title">${esc(item.title)}</div><div class="calendar-appointment-time">${esc(formatDate(item.start_timestamp))}</div></div><button class="calendar-cancel" type="button" data-calendar-cancel="${esc(item.id)}">Cancel</button></div><div class="calendar-meta">${meta.map(value => `<span>${esc(value)}</span>`).join("")}</div>${item.notes ? `<div>${esc(item.notes)}</div>` : ""}<div class="calendar-reminder-badges">${(item.reminders || []).map(reminderBadge).join("") || '<span class="muted">No reminders</span>'}</div>`;
      root.appendChild(node);
    }
  }

  function renderReminders() {
    const root = $("calendar-reminders");
    const reminders = [];
    for (const appointment of state.appointments || []) {
      for (const reminder of appointment.reminders || []) reminders.push({appointment, reminder});
    }
    reminders.sort((a,b) => Number(a.reminder.due_at || 0) - Number(b.reminder.due_at || 0));
    root.replaceChildren();
    if (!reminders.length) {
      root.innerHTML = '<div class="calendar-empty">No calendar reminders scheduled.</div>';
      return;
    }
    for (const {appointment, reminder} of reminders) {
      const node = document.createElement("div");
      node.className = "calendar-reminder";
      node.innerHTML = `<div class="calendar-appointment-title">${esc(appointment.title)}</div><div class="calendar-appointment-time">${esc(reminder.label || "Reminder")}</div><div class="calendar-meta"><span>Due ${esc(formatDate(reminder.due_at))}</span><span>${esc(reminder.status || "scheduled")}</span><span>${esc(appointment.destination || state.default_destination || "No destination")}</span></div>`;
      root.appendChild(node);
    }
  }

  function renderBadge() {
    const count = (state.appointments || []).length;
    const badge = $("calendar-quick-count");
    badge.textContent = count > 99 ? "99+" : String(count);
    badge.dataset.empty = count ? "false" : "true";
    badge.setAttribute("aria-label", `${count} upcoming appointment${count === 1 ? "" : "s"}`);
  }

  async function loadChannels() {
    const select = $("calendar-destination");
    const notification = await api("api/notifications");
    select.replaceChildren(new Option("Notification Center default", ""));
    for (const channel of notification.channels || []) {
      const label = `${channel.platform === "telegram" ? "Telegram · " : ""}${channel.friendly_name}`;
      select.appendChild(new Option(label, channel.entity_id));
    }
  }

  async function loadCalendar() {
    state = await api("api/calendar");
    renderAppointments();
    renderReminders();
    renderBadge();
    window.zbranoClearTabChanged?.("calendar-tab");
  }

  function showCalendar() {
    if (typeof showPanel === "function") showPanel("calendar");
    else {
      for (const node of document.querySelectorAll("main > section.panel")) node.classList.toggle("hidden", node !== panel);
      for (const node of document.querySelectorAll("nav > button")) node.classList.toggle("active", node === tab);
    }
    loadCalendar().catch(error => { $("calendar-summary").textContent = `Calendar unavailable: ${error.message || error}`; });
    loadChannels().catch(() => {});
  }

  function showView(name) {
    for (const button of panel.querySelectorAll("[data-calendar-view]")) {
      const active = button.dataset.calendarView === name;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
    }
    for (const view of panel.querySelectorAll("[data-calendar-panel]")) view.classList.toggle("hidden", view.dataset.calendarPanel !== name);
  }

  tab.addEventListener("click", event => { event.preventDefault(); event.stopImmediatePropagation(); showCalendar(); }, true);
  quick.addEventListener("click", showCalendar);
  $("calendar-refresh").addEventListener("click", () => loadCalendar().catch(error => { $("calendar-summary").textContent = error.message || String(error); }));
  panel.querySelector(".calendar-subtabs").addEventListener("click", event => {
    const button = event.target.closest("[data-calendar-view]");
    if (button) showView(button.dataset.calendarView);
  });

  $("calendar-form").addEventListener("submit", async event => {
    event.preventDefault();
    const status = $("calendar-form-status");
    const localStart = new Date(`${$("calendar-date").value}T${$("calendar-time").value}:00`);
    if (!Number.isFinite(localStart.getTime())) { status.textContent = "Choose a valid date and time."; return; }
    const offsets = [...panel.querySelectorAll('.calendar-reminder-options input:checked')].map(node => Number(node.value));
    const body = {
      title: $("calendar-title").value.trim(), start_at: localStart.toISOString(),
      duration_minutes: Number($("calendar-duration").value || 60), location: $("calendar-location").value.trim(),
      notes: $("calendar-notes").value.trim(), destination: $("calendar-destination").value,
      reminder_offsets_minutes: offsets,
    };
    status.textContent = "Adding appointment…";
    try {
      const result = await api("api/calendar", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
      status.textContent = result.deduplicated ? "This appointment already exists." : "Appointment and reminders added.";
      event.currentTarget.reset();
      $("calendar-duration").value = "60";
      for (const input of panel.querySelectorAll('.calendar-reminder-options input')) input.checked = [1440,120].includes(Number(input.value));
      await loadCalendar();
    } catch (error) { status.textContent = `Could not add appointment: ${error.message || error}`; }
  });

  $("calendar-appointments").addEventListener("click", async event => {
    const button = event.target.closest("[data-calendar-cancel]");
    if (!button || !confirm("Cancel this appointment and its pending reminders?")) return;
    button.disabled = true;
    try { await api(`api/calendar/${encodeURIComponent(button.dataset.calendarCancel)}`, {method:"DELETE"}); await loadCalendar(); }
    catch (error) { $("calendar-summary").textContent = `Cancel failed: ${error.message || error}`; }
    finally { button.disabled = false; }
  });

  document.addEventListener("click", event => {
    const other = event.target.closest?.("#chat-tab,#files-tab,#plugins-tab,#entities-tab,#automations-tab,#settings-tab,#developer-tab");
    if (other) { panel.classList.add("hidden"); tab.classList.remove("active"); }
  }, true);
  loadCalendar().catch(() => {});
  window.setInterval(() => { if (!document.hidden) loadCalendar().catch(() => {}); }, 60000);
  window.zbranoCalendar = {ready:true, open:showCalendar, refresh:loadCalendar};
})();
</script>
'''
    frontend = replace_once(
        frontend,
        "\n</body>\n</html>",
        calendar_runtime + "\n</body>\n</html>",
        "calendar runtime",
    )

    frontend = frontend.replace("HUD 0.12.70", "HUD 0.12.71")
    return frontend


def verify(backend: str, frontend: str) -> None:
    backend_markers = (
        'version="0.12.71"',
        "class CalendarAppointmentRequest",
        '"name": "create_calendar_appointment"',
        '"name": "list_calendar_appointments"',
        '"name": "cancel_calendar_appointment"',
        'CALENDAR_STORAGE_PATH = Path("/data/zbrano_calendar.json")',
        "async def calendar_reminder_worker()",
        '@app.get("/api/calendar")',
        '@app.post("/api/calendar")',
        'name="zbrano-calendar-reminders"',
        "ZBRANO CALENDAR WORKFLOW",
        "return calendar_priority_tools()",
        '"calendar": calendar_store()',
        '"calendar": _tab_activity_revision(CALENDAR_STORAGE_PATH)',
        "Calendar and reminders API operational",
    )
    frontend_markers = (
        "HUD 0.12.71",
        'id="calendar-quick-open"',
        'id="calendar-tab"',
        'id="calendar-panel"',
        'data-calendar-view="upcoming"',
        'data-calendar-view="reminders"',
        'id="calendar-form"',
        'id="zbrano-v01271-calendar-center"',
        'showPanel("calendar")',
        'window.zbranoCalendar = {ready:true',
        'calendar: ["#calendar-tab"]',
    )
    missing = [marker for marker in backend_markers if marker not in backend]
    missing += [marker for marker in frontend_markers if marker not in frontend]
    if missing:
        raise RuntimeError("ZBRANO v0.12.71 verification failed: " + ", ".join(missing))


def main() -> None:
    backend = patch_backend(MAIN.read_text(encoding="utf-8"))
    frontend = patch_frontend(INDEX.read_text(encoding="utf-8"))
    verify(backend, frontend)
    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
