from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.87 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.87 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    frontend = replace_once(
        frontend,
        '''        <article class="calendar-card">
          <div class="calendar-card-head"><div><h3>Calendar reminders</h3><p>Scheduled and delivered reminders for your appointments.</p></div></div>
          <div id="calendar-reminders" class="calendar-reminder-list"></div>
        </article>''',
        '''        <article class="calendar-card">
          <div class="calendar-card-head"><div><h3>Calendar reminders</h3><p>Pending delivery and completed reminder history.</p></div></div>
          <div class="calendar-reminder-status" role="status" aria-live="polite">
            <button type="button" class="active" data-reminder-filter="all"><span>All</span><strong id="calendar-reminder-all-count">0</strong></button>
            <button type="button" data-reminder-filter="pending"><span>Pending</span><strong id="calendar-reminder-pending-count">0</strong></button>
            <button type="button" data-reminder-filter="completed"><span>Completed</span><strong id="calendar-reminder-completed-count">0</strong></button>
            <button type="button" data-reminder-filter="attention"><span>Attention</span><strong id="calendar-reminder-attention-count">0</strong></button>
          </div>
          <p id="calendar-reminder-summary" class="calendar-reminder-summary">Loading reminder status…</p>
          <div id="calendar-reminders" class="calendar-reminder-list"></div>
        </article>''',
        "reminder status dashboard",
    )

    frontend = replace_once(
        frontend,
        '''    .calendar-reminder-badge[data-status="delivered"] { color:#39d6a1; }
    .calendar-reminder-badge[data-status="failed"],.calendar-reminder-badge[data-status="missed"] { color:#ef765f; }''',
        '''    .calendar-reminder-badge[data-status="delivered"] { color:#39d6a1; }
    .calendar-reminder-badge[data-status="failed"],.calendar-reminder-badge[data-status="missed"],.calendar-reminder-badge[data-status="suppressed"] { color:#ef765f; }
    .calendar-reminder-status { display:grid; grid-template-columns:repeat(4,minmax(100px,1fr)); gap:.5rem; margin-top:.85rem; }
    .calendar-reminder-status button { display:flex; align-items:center; justify-content:space-between; gap:.5rem; min-height:42px; padding:.5rem .65rem; text-align:left; }
    .calendar-reminder-status button strong { font-size:1rem; font-weight:650; }
    .calendar-reminder-status button[data-reminder-filter="pending"] strong { color:#e7a449; }
    .calendar-reminder-status button[data-reminder-filter="completed"] strong { color:#39d6a1; }
    .calendar-reminder-status button[data-reminder-filter="attention"] strong { color:#ef765f; }
    .calendar-reminder-status button.active { border-color:var(--cyan); box-shadow:0 0 0 1px color-mix(in srgb,var(--cyan) 28%,transparent); }
    .calendar-reminder-summary { margin:.65rem 0 0; color:var(--text-muted); }
    .calendar-reminder-state { text-transform:capitalize; }
    .calendar-reminder-state[data-state="pending"] { color:#e7a449; }
    .calendar-reminder-state[data-state="completed"] { color:#39d6a1; }
    .calendar-reminder-state[data-state="attention"] { color:#ef765f; }
    @media (max-width:620px) { .calendar-reminder-status { grid-template-columns:repeat(2,minmax(0,1fr)); } }''',
        "reminder status styles",
    )

    frontend = replace_once(
        frontend,
        '''  let state = {appointments:[], default_destination:""};''',
        '''  let state = {appointments:[], default_destination:""};
  let reminderFilter = "all";''',
        "reminder filter state",
    )

    frontend = replace_once(
        frontend,
        '''  function renderReminders() {
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
      node.innerHTML = `<div class="calendar-appointment-head"><div><div class="calendar-appointment-title">${esc(appointment.title)}</div><div class="calendar-appointment-time">${esc(reminder.label || "Reminder")}</div></div><button class="calendar-edit-reminders" type="button" data-calendar-edit-reminders="${esc(appointment.id)}">Edit</button></div><div class="calendar-meta"><span>Due ${esc(formatDate(reminder.due_at))}</span><span>${esc(reminder.status || "scheduled")}</span><span>${esc(appointment.destination || state.default_destination || "No destination")}</span></div>`;
      root.appendChild(node);
    }
  }''',
        '''  function reminderState(reminder) {
    const status = String(reminder.status || "scheduled").toLowerCase();
    if (status === "delivered") return "completed";
    if (status === "scheduled") return "pending";
    return "attention";
  }

  function renderReminders() {
    const root = $("calendar-reminders");
    const reminders = [];
    for (const appointment of state.allAppointments || state.appointments || []) {
      for (const reminder of appointment.reminders || []) reminders.push({appointment, reminder, state:reminderState(reminder)});
    }
    const counts = {
      all: reminders.length,
      pending: reminders.filter(item => item.state === "pending").length,
      completed: reminders.filter(item => item.state === "completed").length,
      attention: reminders.filter(item => item.state === "attention").length,
    };
    for (const name of ["all", "pending", "completed", "attention"]) {
      $(`calendar-reminder-${name}-count`).textContent = String(counts[name]);
    }
    const visible = reminders.filter(item => reminderFilter === "all" || item.state === reminderFilter);
    visible.sort((a,b) => {
      if (a.state === "completed" && b.state === "completed") return Number(b.reminder.delivered_at || b.reminder.due_at || 0) - Number(a.reminder.delivered_at || a.reminder.due_at || 0);
      if (a.state === "pending" && b.state === "pending") return Number(a.reminder.due_at || 0) - Number(b.reminder.due_at || 0);
      return ({pending:0, attention:1, completed:2})[a.state] - ({pending:0, attention:1, completed:2})[b.state];
    });
    $("calendar-reminder-summary").textContent = `${counts.pending} pending · ${counts.completed} completed${counts.attention ? ` · ${counts.attention} need attention` : ""}`;
    root.replaceChildren();
    if (!visible.length) {
      root.innerHTML = `<div class="calendar-empty">No ${reminderFilter === "all" ? "calendar" : reminderFilter} reminders.</div>`;
      return;
    }
    for (const {appointment, reminder, state:displayState} of visible) {
      const node = document.createElement("div");
      node.className = "calendar-reminder";
      node.dataset.reminderState = displayState;
      const canEdit = displayState === "pending" && Number(appointment.end_timestamp || appointment.start_timestamp || 0) >= Date.now() / 1000;
      const action = canEdit ? `<button class="calendar-edit-reminders" type="button" data-calendar-edit-reminders="${esc(appointment.id)}">Edit</button>` : "";
      const completedAt = displayState === "completed" && reminder.delivered_at ? `<span>Delivered ${esc(formatDate(reminder.delivered_at))}</span>` : "";
      const error = reminder.last_error ? `<div class="calendar-reminder-error">${esc(reminder.last_error)}</div>` : "";
      node.innerHTML = `<div class="calendar-appointment-head"><div><div class="calendar-appointment-title">${esc(appointment.title)}</div><div class="calendar-appointment-time">${esc(reminder.label || "Reminder")}</div></div>${action}</div><div class="calendar-meta"><span>Due ${esc(formatDate(reminder.due_at))}</span><span class="calendar-reminder-state" data-state="${displayState}">${esc(displayState)}</span><span>${esc(appointment.destination || state.default_destination || "No destination")}</span>${completedAt}</div>${error}`;
      root.appendChild(node);
    }
  }''',
        "reminder status renderer",
    )

    frontend = replace_once(
        frontend,
        '''  $("calendar-reminders").addEventListener("click", event => {
    const edit = event.target.closest("[data-calendar-edit-reminders]");
    if (edit) openReminderEditor(edit.dataset.calendarEditReminders);
  });''',
        '''  $("calendar-reminders").addEventListener("click", event => {
    const edit = event.target.closest("[data-calendar-edit-reminders]");
    if (edit) openReminderEditor(edit.dataset.calendarEditReminders);
  });
  panel.querySelector(".calendar-reminder-status").addEventListener("click", event => {
    const button = event.target.closest("[data-reminder-filter]");
    if (!button) return;
    reminderFilter = button.dataset.reminderFilter || "all";
    for (const item of panel.querySelectorAll("[data-reminder-filter]")) item.classList.toggle("active", item === button);
    renderReminders();
  });''',
        "reminder status filter controller",
    )

    backend = backend.replace('version="0.12.86"', 'version="0.12.87"')
    backend = backend.replace('"version": "0.12.86"', '"version": "0.12.87"')
    frontend = frontend.replace("HUD 0.12.86", "HUD 0.12.87")

    for marker, label in [
        ('version="0.12.87"', "backend version"),
        ("HUD 0.12.87", "frontend version"),
        ('id="calendar-reminder-pending-count"', "pending counter"),
        ('id="calendar-reminder-completed-count"', "completed counter"),
        ('data-reminder-filter="attention"', "attention filter"),
        ('function reminderState(reminder)', "status classification"),
        ('state.allAppointments || state.appointments', "completed reminder history"),
    ]:
        require(backend if label == "backend version" else frontend, marker, label)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
