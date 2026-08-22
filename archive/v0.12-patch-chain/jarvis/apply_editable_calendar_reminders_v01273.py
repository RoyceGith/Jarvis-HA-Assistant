import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.73 expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.73 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    model = r'''class CalendarRemindersUpdateRequest(BaseModel):
    destination: str = Field(default="", max_length=255, pattern=r"^(|notify\.[a-z0-9_]+)$")
    reminder_offsets_minutes: list[int] = Field(default_factory=list, max_length=8)


'''
    backend = replace_once(
        backend,
        "class SettingsRestoreRequest(BaseModel):\n",
        model + "class SettingsRestoreRequest(BaseModel):\n",
        "calendar reminder update model",
    )

    tool = r'''    {
        "type": "function",
        "name": "update_calendar_reminders",
        "description": (
            "Replace the reminder schedule and optional notification destination for one existing ZBRANO "
            "calendar appointment. List appointments first when its exact ID is unknown or the title is "
            "ambiguous. The user's explicit request to change reminders authorizes this update."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {"type": "string", "description": "Exact appointment ID."},
                "destination": {"type": "string", "description": "Optional notify entity; blank uses the Notification Center default."},
                "reminder_offsets_minutes": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Complete replacement list of minutes before start; [] removes all reminders."
                }
            },
            "required": ["appointment_id", "destination", "reminder_offsets_minutes"],
            "additionalProperties": False
        },
        "strict": True
    },
'''
    backend = replace_once(
        backend,
        "WORKSHOP_TOOLS: list[dict[str, Any]] = [\n",
        "WORKSHOP_TOOLS: list[dict[str, Any]] = [\n" + tool,
        "calendar reminder update tool",
    )

    reminder_update = r'''async def _update_calendar_reminders(
    appointment_id: str, request: CalendarRemindersUpdateRequest, source: str = "interface",
) -> dict[str, Any]:
    import secrets

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
    appointment = next((item for item in data["appointments"] if item.get("id") == appointment_id), None)
    if not appointment or appointment.get("status") == "cancelled":
        raise HTTPException(status_code=404, detail="Calendar appointment not found")
    if float(appointment.get("end_timestamp") or 0) < time.time():
        raise HTTPException(status_code=400, detail="Past appointment reminders cannot be edited")

    existing = {
        int(item.get("offset_minutes") or 0): item
        for item in appointment.get("reminders") or []
    }
    start_timestamp = float(appointment.get("start_timestamp") or 0)
    now = time.time()
    reminders = []
    for offset in offsets:
        previous = existing.get(offset)
        due_at = start_timestamp - offset * 60
        if previous:
            reminder = dict(previous)
            reminder["due_at"] = due_at
            reminder["label"] = CALENDAR_REMINDER_OFFSETS.get(offset, f"{offset} minutes before")
        else:
            reminder = {
                "id": secrets.token_hex(8),
                "offset_minutes": offset,
                "label": CALENDAR_REMINDER_OFFSETS.get(offset, f"{offset} minutes before"),
                "due_at": due_at,
                "status": "scheduled" if due_at >= now else "missed",
                "last_attempt_at": 0.0,
                "delivered_at": 0.0,
            }
        reminders.append(reminder)

    appointment["destination"] = destination
    appointment["reminders"] = reminders
    appointment["updated_at"] = now
    appointment["reminders_updated_by"] = source
    _calendar_save(data)
    return {"updated": True, "appointment": _calendar_public(appointment)}


'''
    backend = replace_once(
        backend,
        "def _cancel_calendar_appointment(appointment_id: str) -> dict[str, Any]:\n",
        reminder_update + "def _cancel_calendar_appointment(appointment_id: str) -> dict[str, Any]:\n",
        "calendar reminder update backend",
    )

    backend = replace_once(
        backend,
        '''                if name == "create_calendar_appointment":
                    result = await _create_calendar_appointment(CalendarAppointmentRequest(**arguments), source="chat")
                elif name == "list_calendar_appointments":''',
        '''                if name == "create_calendar_appointment":
                    result = await _create_calendar_appointment(CalendarAppointmentRequest(**arguments), source="chat")
                elif name == "update_calendar_reminders":
                    result = await _update_calendar_reminders(
                        str(arguments.get("appointment_id") or ""),
                        CalendarRemindersUpdateRequest(
                            destination=str(arguments.get("destination") or ""),
                            reminder_offsets_minutes=arguments.get("reminder_offsets_minutes") or [],
                        ),
                        source="chat",
                    )
                elif name == "list_calendar_appointments":''',
        "calendar reminder tool execution",
    )

    backend = replace_once(
        backend,
        '''@app.delete("/api/calendar/{appointment_id}")
async def cancel_calendar_appointment(appointment_id: str) -> dict[str, Any]:''',
        '''@app.put("/api/calendar/{appointment_id}/reminders")
async def update_calendar_reminders(
    appointment_id: str, request: CalendarRemindersUpdateRequest,
) -> dict[str, Any]:
    return await _update_calendar_reminders(appointment_id, request)


@app.delete("/api/calendar/{appointment_id}")
async def cancel_calendar_appointment(appointment_id: str) -> dict[str, Any]:''',
        "calendar reminder update API",
    )

    backend = replace_once(
        backend,
        '''def calendar_priority_tools() -> list[dict[str, Any]]:
    names = {"create_calendar_appointment", "list_calendar_appointments", "cancel_calendar_appointment"}''',
        '''def calendar_priority_tools() -> list[dict[str, Any]]:
    names = {
        "create_calendar_appointment", "list_calendar_appointments",
        "update_calendar_reminders", "cancel_calendar_appointment",
    }''',
        "calendar reminder priority routing",
    )
    backend = replace_once(
        backend,
        '''for schedule questions and before cancelling an ambiguous event. Calendar reminders are delivered through the
Notification Center default channel, including Telegram when configured.''',
        '''for schedule questions and before cancelling an ambiguous event. When the user asks to change reminder timing,
list the appointments if necessary, then call update_calendar_reminders with the complete replacement schedule. An empty
offset list removes all reminders. Preserve delivered reminders at an unchanged offset so they are never resent accidentally.
Calendar reminders are delivered through the Notification Center default channel, including Telegram when configured.''',
        "editable reminder instructions",
    )

    editor = r'''        <article id="calendar-reminder-editor" class="calendar-card calendar-reminder-editor" hidden>
          <div class="calendar-card-head"><div><h3>Edit reminders</h3><p id="calendar-reminder-editor-title">Choose an appointment.</p></div><button id="calendar-reminder-editor-close" type="button" aria-label="Close reminder editor">×</button></div>
          <form id="calendar-reminder-form">
            <input id="calendar-reminder-appointment-id" type="hidden">
            <fieldset class="calendar-reminder-options calendar-edit-reminder-options">
              <legend>Reminder schedule</legend>
              <label><input type="checkbox" value="1440"> One day before</label>
              <label><input type="checkbox" value="120"> Same day · 2 hours before</label>
              <label><input type="checkbox" value="30"> 30 minutes before</label>
              <label><input type="checkbox" value="0"> At appointment time</label>
            </fieldset>
            <label>Custom minutes before<input id="calendar-reminder-custom" inputmode="numeric" placeholder="Example: 60, 2880"><span>Separate multiple values with commas. Leave empty for presets only.</span></label>
            <label>Notification channel<select id="calendar-reminder-destination"><option value="">Notification Center default</option></select></label>
            <div class="calendar-form-actions"><button type="submit">Save reminders</button><button id="calendar-reminder-remove-all" type="button">Remove all</button><span id="calendar-reminder-form-status" role="status"></span></div>
          </form>
        </article>
'''
    frontend = replace_once(
        frontend,
        '''      <section data-calendar-panel="reminders" class="hidden">
        <article class="calendar-card">''',
        '''      <section data-calendar-panel="reminders" class="hidden">
''' + editor + '''        <article class="calendar-card">''',
        "calendar reminder editor",
    )

    frontend = replace_once(
        frontend,
        '''<button class="calendar-cancel" type="button" data-calendar-cancel="${esc(item.id)}">Cancel</button>''',
        '''<div class="calendar-appointment-actions"><button class="calendar-edit-reminders" type="button" data-calendar-edit-reminders="${esc(item.id)}">Edit reminders</button><button class="calendar-cancel" type="button" data-calendar-cancel="${esc(item.id)}">Cancel</button></div>''',
        "appointment reminder edit action",
    )
    frontend = replace_once(
        frontend,
        '''node.innerHTML = `<div class="calendar-appointment-title">${esc(appointment.title)}</div><div class="calendar-appointment-time">${esc(reminder.label || "Reminder")}</div><div class="calendar-meta"><span>Due ${esc(formatDate(reminder.due_at))}</span><span>${esc(reminder.status || "scheduled")}</span><span>${esc(appointment.destination || state.default_destination || "No destination")}</span></div>`;''',
        '''node.innerHTML = `<div class="calendar-appointment-head"><div><div class="calendar-appointment-title">${esc(appointment.title)}</div><div class="calendar-appointment-time">${esc(reminder.label || "Reminder")}</div></div><button class="calendar-edit-reminders" type="button" data-calendar-edit-reminders="${esc(appointment.id)}">Edit</button></div><div class="calendar-meta"><span>Due ${esc(formatDate(reminder.due_at))}</span><span>${esc(reminder.status || "scheduled")}</span><span>${esc(appointment.destination || state.default_destination || "No destination")}</span></div>`;''',
        "reminder row edit action",
    )

    frontend = replace_once(
        frontend,
        '''  async function loadChannels() {
    const select = $("calendar-destination");
    const notification = await api("api/notifications");
    select.replaceChildren(new Option("Notification Center default", ""));
    for (const channel of notification.channels || []) {
      const label = `${channel.platform === "telegram" ? "Telegram · " : ""}${channel.friendly_name}`;
      select.appendChild(new Option(label, channel.entity_id));
    }
  }''',
        '''  async function loadChannels() {
    const notification = await api("api/notifications");
    for (const select of [$("calendar-destination"), $("calendar-reminder-destination")]) {
      select.replaceChildren(new Option("Notification Center default", ""));
      for (const channel of notification.channels || []) {
        const label = `${channel.platform === "telegram" ? "Telegram · " : ""}${channel.friendly_name}`;
        select.appendChild(new Option(label, channel.entity_id));
      }
    }
  }''',
        "reminder editor channel options",
    )

    reminder_runtime = r'''

  async function openReminderEditor(appointmentId) {
    const appointment = (state.appointments || []).find(item => item.id === appointmentId);
    if (!appointment) return;
    $("calendar-reminder-appointment-id").value = appointment.id;
    $("calendar-reminder-editor-title").textContent = `${appointment.title} · ${formatDate(appointment.start_timestamp)}`;
    const offsets = new Set((appointment.reminders || []).map(item => Number(item.offset_minutes)));
    for (const input of panel.querySelectorAll(".calendar-edit-reminder-options input")) input.checked = offsets.has(Number(input.value));
    const presets = new Set([1440, 120, 30, 0]);
    $("calendar-reminder-custom").value = [...offsets].filter(value => !presets.has(value)).sort((a,b) => b-a).join(", ");
    $("calendar-reminder-editor").hidden = false;
    showView("reminders");
    $("calendar-reminder-editor").scrollIntoView({behavior:"smooth", block:"start"});
    $("calendar-reminder-destination").disabled = true;
    $("calendar-reminder-form-status").textContent = "Loading notification channels…";
    try {
      await loadChannels();
      $("calendar-reminder-destination").value = appointment.destination || "";
      $("calendar-reminder-destination").disabled = false;
      $("calendar-reminder-form-status").textContent = "";
    } catch (error) {
      $("calendar-reminder-form-status").textContent = `Notification channels unavailable: ${error.message || error}`;
    }
  }

  function closeReminderEditor() {
    $("calendar-reminder-editor").hidden = true;
    $("calendar-reminder-appointment-id").value = "";
  }

  function reminderEditorOffsets() {
    const preset = [...panel.querySelectorAll(".calendar-edit-reminder-options input:checked")].map(node => Number(node.value));
    const customText = $("calendar-reminder-custom").value.trim();
    const custom = customText ? customText.split(",").map(value => Number(value.trim())) : [];
    if (custom.some(value => !Number.isInteger(value) || value < 0 || value > 525600)) throw new Error("Custom reminders must be whole minutes between 0 and 525600.");
    return [...new Set([...preset, ...custom])].sort((a,b) => b-a);
  }

  async function saveReminderEditor(removeAll = false) {
    const appointmentId = $("calendar-reminder-appointment-id").value;
    if (!appointmentId) return;
    const status = $("calendar-reminder-form-status");
    let offsets;
    try { offsets = removeAll ? [] : reminderEditorOffsets(); }
    catch (error) { status.textContent = error.message || String(error); return; }
    status.textContent = removeAll ? "Removing reminders…" : "Saving reminders…";
    try {
      await api(`api/calendar/${encodeURIComponent(appointmentId)}/reminders`, {
        method:"PUT", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({destination:$("calendar-reminder-destination").value, reminder_offsets_minutes:offsets}),
      });
      status.textContent = removeAll ? "All reminders removed." : "Reminder schedule saved.";
      await loadCalendar();
      if (removeAll) closeReminderEditor();
      else await openReminderEditor(appointmentId);
    } catch (error) { status.textContent = `Could not update reminders: ${error.message || error}`; }
  }
'''
    frontend = replace_once(
        frontend,
        '''  function showCalendar() {
''',
        reminder_runtime + '''
  function showCalendar() {
''',
        "calendar reminder editor runtime",
    )

    frontend = replace_once(
        frontend,
        '''  $("calendar-appointments").addEventListener("click", async event => {
    const button = event.target.closest("[data-calendar-cancel]");
    if (!button || !confirm("Cancel this appointment and its pending reminders?")) return;''',
        '''  $("calendar-appointments").addEventListener("click", async event => {
    const edit = event.target.closest("[data-calendar-edit-reminders]");
    if (edit) { openReminderEditor(edit.dataset.calendarEditReminders); return; }
    const button = event.target.closest("[data-calendar-cancel]");
    if (!button || !confirm("Cancel this appointment and its pending reminders?")) return;''',
        "appointment reminder edit handler",
    )
    frontend = replace_once(
        frontend,
        '''  document.addEventListener("click", event => {
    const other = event.target.closest?.("#chat-tab,#files-tab,#plugins-tab,#entities-tab,#automations-tab,#settings-tab,#developer-tab");''',
        '''  $("calendar-reminders").addEventListener("click", event => {
    const edit = event.target.closest("[data-calendar-edit-reminders]");
    if (edit) openReminderEditor(edit.dataset.calendarEditReminders);
  });
  $("calendar-reminder-form").addEventListener("submit", event => { event.preventDefault(); saveReminderEditor(false); });
  $("calendar-reminder-remove-all").addEventListener("click", () => saveReminderEditor(true));
  $("calendar-reminder-editor-close").addEventListener("click", closeReminderEditor);

  document.addEventListener("click", event => {
    const other = event.target.closest?.("#chat-tab,#files-tab,#plugins-tab,#entities-tab,#automations-tab,#settings-tab,#developer-tab");''',
        "reminder editor event handlers",
    )

    css = r'''
    .calendar-appointment-actions { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:.35rem; }
    .calendar-edit-reminders { flex:0 0 auto; padding:.32rem .5rem; font-size:.72rem; }
    .calendar-reminder-editor { margin-bottom:.75rem; border-color:color-mix(in srgb,var(--cyan) 46%,var(--line)); }
    .calendar-reminder-editor[hidden] { display:none; }
    #calendar-reminder-form { display:grid; gap:.62rem; margin-top:.7rem; }
    #calendar-reminder-form > label { display:grid; gap:.28rem; }
    #calendar-reminder-form input:not([type="checkbox"]),#calendar-reminder-form select { width:100%; min-width:0; max-width:100%; }
    #calendar-reminder-form label span { color:var(--text-muted); font-size:.68rem; }
    #calendar-reminder-remove-all { border-color:rgba(239,118,95,.42); color:#ef765f; }
'''
    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.73 could not locate stylesheet close")
    frontend = frontend[:style_close] + css + frontend[style_close:]

    backend = backend.replace('version="0.12.72"', 'version="0.12.73"')
    backend = backend.replace('"version": "0.12.72"', '"version": "0.12.73"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.72"', '"X-ZBRANO-Frontend-Version": "0.12.73"')
    backend = backend.replace(
        '"name": "ZBRANO Developer Mode", "version": "0.12.72"',
        '"name": "ZBRANO Developer Mode", "version": "0.12.73"',
    )
    frontend = frontend.replace("HUD 0.12.72", "HUD 0.12.73")

    backend_markers = (
        'version="0.12.73"', "class CalendarRemindersUpdateRequest",
        '"name": "update_calendar_reminders"', "async def _update_calendar_reminders(",
        '@app.put("/api/calendar/{appointment_id}/reminders")',
        '"update_calendar_reminders", "cancel_calendar_appointment"',
        "Preserve delivered reminders at an unchanged offset",
    )
    frontend_markers = (
        "HUD 0.12.73", 'id="calendar-reminder-editor"', 'id="calendar-reminder-form"',
        'data-calendar-edit-reminders="${esc(item.id)}"', "function openReminderEditor(",
        "function reminderEditorOffsets()", "async function saveReminderEditor(",
        'method:"PUT"', 'id="zbrano-v01271-calendar-center"',
        "speech.chunks.forEach(chunk => queueSpeech(chunk));",
    )
    missing = [marker for marker in backend_markers if marker not in backend]
    missing += [marker for marker in frontend_markers if marker not in frontend]
    if missing:
        raise RuntimeError("ZBRANO v0.12.73 verification failed: " + ", ".join(missing))

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
