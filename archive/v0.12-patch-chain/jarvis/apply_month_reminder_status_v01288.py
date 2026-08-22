from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.88 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.88 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    frontend = replace_once(
        frontend,
        '''    .calendar-day-event { display:block; min-width:0; padding:.18rem .25rem; overflow:hidden; border-left:2px solid var(--cyan); border-radius:3px; background:color-mix(in srgb,var(--cyan) 10%,transparent); font-size:.64rem; line-height:1.25; text-overflow:ellipsis; white-space:nowrap; }
    .calendar-day-event time { color:var(--cyan); font-variant-numeric:tabular-nums; }''',
        '''    .calendar-day-event { display:grid; grid-template-columns:auto minmax(0,1fr); gap:.1rem .28rem; min-width:0; padding:.18rem .25rem; overflow:hidden; border-left:2px solid var(--cyan); border-radius:3px; background:color-mix(in srgb,var(--cyan) 10%,transparent); font-size:.64rem; line-height:1.25; text-align:left; }
    .calendar-day-event time { color:var(--cyan); font-variant-numeric:tabular-nums; }
    .calendar-day-event-title { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .calendar-month-reminder-state { grid-column:1 / -1; width:max-content; max-width:100%; padding:.06rem .25rem; border:1px solid var(--line); border-radius:999px; font-size:.52rem; font-style:normal; font-weight:650; letter-spacing:.025em; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .calendar-month-reminder-state[data-state="pending"] { color:#e7a449; border-color:color-mix(in srgb,#e7a449 55%,var(--line)); }
    .calendar-month-reminder-state[data-state="completed"] { color:#39d6a1; border-color:color-mix(in srgb,#39d6a1 55%,var(--line)); }
    .calendar-month-reminder-state[data-state="attention"] { color:#ef765f; border-color:color-mix(in srgb,#ef765f 55%,var(--line)); }
    .calendar-month-reminder-state[data-state="none"] { color:var(--text-muted); }''',
        "month reminder marker styles",
    )

    frontend = replace_once(
        frontend,
        '''  function reminderBadge(reminder) {
    const status = reminder.status || "scheduled";
    return `<span class="calendar-reminder-badge" data-status="${esc(status)}">${esc(reminder.label || "Reminder")} · ${esc(status)}</span>`;
  }
''',
        '''  function reminderBadge(reminder) {
    const status = reminder.status || "scheduled";
    const display = reminderState(reminder);
    return `<span class="calendar-reminder-badge" data-status="${esc(status)}">${esc(reminder.label || "Reminder")} · ${esc(display)}</span>`;
  }

  function appointmentReminderSummary(appointment) {
    const counts = {pending:0, completed:0, attention:0};
    for (const reminder of appointment.reminders || []) counts[reminderState(reminder)] += 1;
    const total = counts.pending + counts.completed + counts.attention;
    if (!total) return {state:"none", label:"No reminder"};
    const parts = [];
    if (counts.pending) parts.push(`${counts.pending > 1 ? counts.pending + " " : ""}Pending`);
    if (counts.completed) parts.push(`${counts.completed > 1 ? counts.completed + " " : ""}Completed`);
    if (counts.attention) parts.push(`${counts.attention > 1 ? counts.attention + " " : ""}Attention`);
    return {state:counts.attention ? "attention" : counts.pending ? "pending" : "completed", label:parts.join(" · ")};
  }
''',
        "appointment reminder summary",
    )

    frontend = replace_once(
        frontend,
        '''      const meta = [item.location, `${Number(item.duration_minutes || 60)} minutes`].filter(Boolean);
      node.innerHTML = `<div class="calendar-appointment-head"><div><div class="calendar-appointment-title">${esc(item.title)}</div><div class="calendar-appointment-time">${esc(time)}</div></div><button class="calendar-edit-reminders" type="button" data-calendar-edit-reminders="${esc(item.id)}">Edit reminders</button></div><div class="calendar-meta">${meta.map(value => `<span>${esc(value)}</span>`).join("")}</div>${item.notes ? `<div>${esc(item.notes)}</div>` : ""}`;''',
        '''      const meta = [item.location, `${Number(item.duration_minutes || 60)} minutes`].filter(Boolean);
      const reminderSummary = appointmentReminderSummary(item);
      const canEdit = Number(item.end_timestamp || item.start_timestamp || 0) >= Date.now() / 1000;
      const editAction = canEdit ? `<button class="calendar-edit-reminders" type="button" data-calendar-edit-reminders="${esc(item.id)}">Edit reminders</button>` : "";
      node.innerHTML = `<div class="calendar-appointment-head"><div><div class="calendar-appointment-title">${esc(item.title)}</div><div class="calendar-appointment-time">${esc(time)}</div></div>${editAction}</div><div class="calendar-meta">${meta.map(value => `<span>${esc(value)}</span>`).join("")}<span class="calendar-reminder-state" data-state="${esc(reminderSummary.state)}">${esc(reminderSummary.label)}</span></div>${item.notes ? `<div>${esc(item.notes)}</div>` : ""}<div class="calendar-reminder-badges">${(item.reminders || []).map(reminderBadge).join("") || '<span class="muted">No reminders</span>'}</div>`;''',
        "selected-day reminder status",
    )

    frontend = replace_once(
        frontend,
        '''      const visible = appointments.slice(0, 3);
      cell.innerHTML = `<span class="calendar-day-number">${date.getDate()}</span><span class="calendar-day-events">${visible.map(item => `<span class="calendar-day-event"><time>${new Date(Number(item.start_timestamp) * 1000).toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"})}</time> ${esc(item.title)}</span>`).join("")}${appointments.length > 3 ? `<span class="calendar-day-more">+${appointments.length - 3} more</span>` : ""}</span>`;''',
        '''      const visible = appointments.slice(0, 3);
      cell.innerHTML = `<span class="calendar-day-number">${date.getDate()}</span><span class="calendar-day-events">${visible.map(item => { const reminder = appointmentReminderSummary(item); return `<span class="calendar-day-event"><time>${new Date(Number(item.start_timestamp) * 1000).toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"})}</time><span class="calendar-day-event-title">${esc(item.title)}</span><em class="calendar-month-reminder-state" data-state="${esc(reminder.state)}">${esc(reminder.label)}</em></span>`; }).join("")}${appointments.length > 3 ? `<span class="calendar-day-more">+${appointments.length - 3} more</span>` : ""}</span>`;''',
        "month-cell reminder status",
    )

    backend = backend.replace('version="0.12.87"', 'version="0.12.88"')
    backend = backend.replace('"version": "0.12.87"', '"version": "0.12.88"')
    frontend = frontend.replace("HUD 0.12.87", "HUD 0.12.88")

    for marker, label in [
        ('version="0.12.88"', "backend version"),
        ("HUD 0.12.88", "frontend version"),
        ("function appointmentReminderSummary", "appointment reminder summary"),
        ('class="calendar-month-reminder-state"', "month reminder state marker"),
        ('class="calendar-reminder-badges"', "selected-day reminder badges"),
        ('data-state="${esc(reminder.state)}"', "month state classification"),
    ]:
        require(backend if label == "backend version" else frontend, marker, label)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
