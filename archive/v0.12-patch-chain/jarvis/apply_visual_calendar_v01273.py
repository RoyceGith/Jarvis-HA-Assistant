import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.73 visual calendar expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    frontend = replace_once(
        frontend,
        '''        <button class="active" type="button" data-calendar-view="upcoming" role="tab" aria-selected="true">Upcoming</button>
        <button type="button" data-calendar-view="reminders" role="tab" aria-selected="false">Reminders</button>
      </div>
      <section data-calendar-panel="upcoming">''',
        '''        <button class="active" type="button" data-calendar-view="month" role="tab" aria-selected="true">Month</button>
        <button type="button" data-calendar-view="upcoming" role="tab" aria-selected="false">Upcoming</button>
        <button type="button" data-calendar-view="reminders" role="tab" aria-selected="false">Reminders</button>
      </div>
      <section data-calendar-panel="month">
        <div class="calendar-month-layout">
          <article class="calendar-card calendar-month-card">
            <div class="calendar-month-toolbar">
              <button id="calendar-month-previous" type="button" aria-label="Previous month">&#8249;</button>
              <div><h3 id="calendar-month-title">Month</h3><p id="calendar-month-summary">Loading appointments&hellip;</p></div>
              <div class="calendar-month-actions"><button id="calendar-month-today" type="button">Today</button><button id="calendar-month-next" type="button" aria-label="Next month">&#8250;</button></div>
            </div>
            <div class="calendar-weekdays" aria-hidden="true"><span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span></div>
            <div id="calendar-month-grid" class="calendar-month-grid" role="grid" aria-labelledby="calendar-month-title"></div>
          </article>
          <article class="calendar-card calendar-day-card">
            <div class="calendar-card-head"><div><h3 id="calendar-day-title">Selected day</h3><p id="calendar-day-summary">Choose a day to inspect its appointments.</p></div></div>
            <div id="calendar-day-appointments" class="calendar-appointment-list"></div>
          </article>
        </div>
      </section>
      <section data-calendar-panel="upcoming" class="hidden">''',
        "visual month panel",
    )

    month_runtime = r'''
  let monthCursor = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
  let selectedCalendarDay = new Date();

  function localDayKey(value) {
    const date = value instanceof Date ? value : new Date(Number(value) * 1000);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function appointmentsForDay(date) {
    const key = localDayKey(date);
    return (state.allAppointments || state.appointments || []).filter(item => localDayKey(item.start_timestamp) === key);
  }

  function renderSelectedCalendarDay() {
    const root = $("calendar-day-appointments");
    const appointments = appointmentsForDay(selectedCalendarDay);
    $("calendar-day-title").textContent = selectedCalendarDay.toLocaleDateString([], {weekday:"long", year:"numeric", month:"long", day:"numeric"});
    $("calendar-day-summary").textContent = `${appointments.length} appointment${appointments.length === 1 ? "" : "s"}`;
    root.replaceChildren();
    if (!appointments.length) {
      root.innerHTML = '<div class="calendar-empty">No appointments on this day.</div>';
      return;
    }
    for (const item of appointments) {
      const node = document.createElement("div");
      node.className = "calendar-appointment";
      const time = new Date(Number(item.start_timestamp) * 1000).toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"});
      const meta = [item.location, `${Number(item.duration_minutes || 60)} minutes`].filter(Boolean);
      node.innerHTML = `<div class="calendar-appointment-head"><div><div class="calendar-appointment-title">${esc(item.title)}</div><div class="calendar-appointment-time">${esc(time)}</div></div><button class="calendar-edit-reminders" type="button" data-calendar-edit-reminders="${esc(item.id)}">Edit reminders</button></div><div class="calendar-meta">${meta.map(value => `<span>${esc(value)}</span>`).join("")}</div>${item.notes ? `<div>${esc(item.notes)}</div>` : ""}`;
      root.appendChild(node);
    }
  }

  function renderMonthCalendar() {
    const grid = $("calendar-month-grid");
    const year = monthCursor.getFullYear();
    const month = monthCursor.getMonth();
    const first = new Date(year, month, 1);
    const gridStart = new Date(year, month, 1 - ((first.getDay() + 6) % 7));
    const todayKey = localDayKey(new Date());
    const selectedKey = localDayKey(selectedCalendarDay);
    const monthAppointments = (state.allAppointments || state.appointments || []).filter(item => {
      const date = new Date(Number(item.start_timestamp) * 1000);
      return date.getFullYear() === year && date.getMonth() === month;
    });
    $("calendar-month-title").textContent = first.toLocaleDateString([], {month:"long", year:"numeric"});
    $("calendar-month-summary").textContent = `${monthAppointments.length} appointment${monthAppointments.length === 1 ? "" : "s"} this month`;
    grid.replaceChildren();
    for (let index = 0; index < 42; index += 1) {
      const date = new Date(gridStart.getFullYear(), gridStart.getMonth(), gridStart.getDate() + index);
      const key = localDayKey(date);
      const appointments = appointmentsForDay(date);
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = "calendar-day";
      cell.dataset.calendarDay = key;
      cell.dataset.outsideMonth = String(date.getMonth() !== month);
      cell.dataset.today = String(key === todayKey);
      cell.dataset.selected = String(key === selectedKey);
      cell.setAttribute("role", "gridcell");
      cell.setAttribute("aria-label", `${date.toLocaleDateString([], {weekday:"long", month:"long", day:"numeric", year:"numeric"})}; ${appointments.length} appointment${appointments.length === 1 ? "" : "s"}`);
      const visible = appointments.slice(0, 3);
      cell.innerHTML = `<span class="calendar-day-number">${date.getDate()}</span><span class="calendar-day-events">${visible.map(item => `<span class="calendar-day-event"><time>${new Date(Number(item.start_timestamp) * 1000).toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"})}</time> ${esc(item.title)}</span>`).join("")}${appointments.length > 3 ? `<span class="calendar-day-more">+${appointments.length - 3} more</span>` : ""}</span>`;
      grid.appendChild(cell);
    }
    renderSelectedCalendarDay();
  }
'''
    frontend = replace_once(
        frontend,
        "  function renderAppointments() {\n",
        month_runtime + "\n  function renderAppointments() {\n",
        "visual calendar runtime",
    )

    frontend = replace_once(
        frontend,
        '''  async function loadCalendar() {
    state = await api("api/calendar");
    renderAppointments();
    renderReminders();''',
        '''  async function loadCalendar() {
    const complete = await api("api/calendar?include_past=true");
    const now = Date.now() / 1000;
    state = {
      ...complete,
      allAppointments: complete.appointments || [],
      appointments: (complete.appointments || []).filter(item => Number(item.end_timestamp || item.start_timestamp || 0) >= now),
    };
    renderMonthCalendar();
    renderAppointments();
    renderReminders();''',
        "calendar data for month and upcoming views",
    )

    month_handlers = r'''  $("calendar-month-previous").addEventListener("click", () => {
    monthCursor = new Date(monthCursor.getFullYear(), monthCursor.getMonth() - 1, 1);
    selectedCalendarDay = new Date(monthCursor);
    renderMonthCalendar();
  });
  $("calendar-month-next").addEventListener("click", () => {
    monthCursor = new Date(monthCursor.getFullYear(), monthCursor.getMonth() + 1, 1);
    selectedCalendarDay = new Date(monthCursor);
    renderMonthCalendar();
  });
  $("calendar-month-today").addEventListener("click", () => {
    selectedCalendarDay = new Date();
    monthCursor = new Date(selectedCalendarDay.getFullYear(), selectedCalendarDay.getMonth(), 1);
    renderMonthCalendar();
  });
  $("calendar-month-grid").addEventListener("click", event => {
    const day = event.target.closest("[data-calendar-day]");
    if (!day) return;
    const [year, month, date] = day.dataset.calendarDay.split("-").map(Number);
    selectedCalendarDay = new Date(year, month - 1, date);
    if (selectedCalendarDay.getMonth() !== monthCursor.getMonth() || selectedCalendarDay.getFullYear() !== monthCursor.getFullYear()) {
      monthCursor = new Date(year, month - 1, 1);
    }
    renderMonthCalendar();
  });
  $("calendar-day-appointments").addEventListener("click", event => {
    const edit = event.target.closest("[data-calendar-edit-reminders]");
    if (edit) openReminderEditor(edit.dataset.calendarEditReminders);
  });

'''
    frontend = replace_once(
        frontend,
        '  $("calendar-form").addEventListener("submit", async event => {\n',
        month_handlers + '  $("calendar-form").addEventListener("submit", async event => {\n',
        "month navigation handlers",
    )

    calendar_css = r'''
    /* v0.12.73 visual monthly calendar. */
    .calendar-month-layout { display:grid; grid-template-columns:minmax(0,1.65fr) minmax(17rem,.65fr); gap:.75rem; }
    .calendar-month-toolbar { display:grid; grid-template-columns:auto minmax(0,1fr) auto; align-items:center; gap:.6rem; margin-bottom:.65rem; }
    .calendar-month-toolbar h3,.calendar-month-toolbar p { margin:.05rem 0; text-align:center; }
    .calendar-month-toolbar > button,.calendar-month-actions button { min-width:2.1rem; padding:.42rem .58rem; }
    .calendar-month-actions { display:flex; align-items:center; gap:.35rem; }
    .calendar-weekdays,.calendar-month-grid { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); }
    .calendar-weekdays { color:var(--text-muted); font-size:.66rem; text-align:center; text-transform:uppercase; letter-spacing:.06em; }
    .calendar-weekdays span { padding:.3rem .15rem; }
    .calendar-month-grid { overflow:hidden; border-top:1px solid var(--line); border-left:1px solid var(--line); border-radius:7px; }
    .calendar-day { display:flex; flex-direction:column; align-items:stretch; justify-content:flex-start; gap:.28rem; min-width:0; min-height:7.2rem; padding:.38rem; border:0; border-right:1px solid var(--line); border-bottom:1px solid var(--line); border-radius:0; background:transparent; color:var(--text); text-align:left; }
    .calendar-day:hover,.calendar-day:focus-visible { background:color-mix(in srgb,var(--cyan) 9%,transparent); }
    .calendar-day[data-outside-month="true"] { opacity:.42; }
    .calendar-day[data-today="true"] .calendar-day-number { display:grid; place-items:center; width:1.5rem; height:1.5rem; border-radius:50%; background:var(--cyan); color:var(--panel); }
    .calendar-day[data-selected="true"] { box-shadow:inset 0 0 0 2px color-mix(in srgb,var(--cyan) 72%,transparent); }
    .calendar-day-number { align-self:flex-end; font-size:.72rem; font-weight:650; }
    .calendar-day-events { display:grid; gap:.18rem; min-width:0; }
    .calendar-day-event { display:block; min-width:0; padding:.18rem .25rem; overflow:hidden; border-left:2px solid var(--cyan); border-radius:3px; background:color-mix(in srgb,var(--cyan) 10%,transparent); font-size:.64rem; line-height:1.25; text-overflow:ellipsis; white-space:nowrap; }
    .calendar-day-event time { color:var(--cyan); font-variant-numeric:tabular-nums; }
    .calendar-day-more { color:var(--text-muted); font-size:.62rem; }
    @media(max-width:1050px) { .calendar-month-layout { grid-template-columns:1fr; } }
    @media(max-width:680px) {
      .calendar-month-card { overflow-x:auto; }
      .calendar-weekdays,.calendar-month-grid { min-width:42rem; }
      .calendar-day { min-height:6.2rem; }
      .calendar-month-toolbar { position:sticky; left:0; min-width:min(100%,42rem); }
    }
'''
    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.73 visual calendar could not locate the stylesheet close")
    frontend = frontend[:style_close] + calendar_css + frontend[style_close:]

    backend_markers = ('version="0.12.73"', '"X-ZBRANO-Frontend-Version": "0.12.73"')
    frontend_markers = (
        "HUD 0.12.73", 'data-calendar-view="month"', 'id="calendar-month-grid"',
        'id="calendar-day-appointments"', "function renderMonthCalendar()",
        "function renderSelectedCalendarDay()", 'api("api/calendar?include_past=true")',
        "cell.dataset.calendarDay = key", "calendar-month-layout",
    )
    missing = [marker for marker in backend_markers if marker not in backend]
    missing += [marker for marker in frontend_markers if marker not in frontend]
    if missing:
        raise RuntimeError("ZBRANO v0.12.73 visual calendar verification failed: " + ", ".join(missing))

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
