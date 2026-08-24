(() => {
  const tab = document.getElementById("calendar-tab");
  const panel = document.getElementById("calendar-panel");
  const quick = document.getElementById("calendar-quick-open");
  if (!tab || !panel || !quick) return;
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"})[char]);
  let state = {appointments:[], default_destination:""};
  let reminderFilter = "all";

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
      const reminderSummary = appointmentReminderSummary(item);
      const canEdit = Number(item.end_timestamp || item.start_timestamp || 0) >= Date.now() / 1000;
      const editAction = canEdit ? `<button class="calendar-edit-reminders" type="button" data-calendar-edit-reminders="${esc(item.id)}">Edit reminders</button>` : "";
      const deleteAction = `<button class="calendar-cancel calendar-month-delete" type="button" data-calendar-month-delete="${esc(item.id)}">Delete</button>`;
      node.innerHTML = `<div class="calendar-appointment-head"><div><div class="calendar-appointment-title">${esc(item.title)}</div><div class="calendar-appointment-time">${esc(time)}</div></div><div class="calendar-appointment-actions">${editAction}${deleteAction}</div></div><div class="calendar-meta">${meta.map(value => `<span>${esc(value)}</span>`).join("")}<span class="calendar-reminder-state" data-state="${esc(reminderSummary.state)}">${esc(reminderSummary.label)}</span></div>${item.notes ? `<div>${esc(item.notes)}</div>` : ""}<div class="calendar-reminder-badges">${(item.reminders || []).map(reminderBadge).join("") || '<span class="muted">No reminders</span>'}</div>`;
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
      cell.innerHTML = `<span class="calendar-day-number">${date.getDate()}</span><span class="calendar-day-events">${visible.map(item => { const reminder = appointmentReminderSummary(item); return `<span class="calendar-day-event"><time>${new Date(Number(item.start_timestamp) * 1000).toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"})}</time><span class="calendar-day-event-title">${esc(item.title)}</span><em class="calendar-month-reminder-state" data-state="${esc(reminder.state)}">${esc(reminder.label)}</em></span>`; }).join("")}${appointments.length > 3 ? `<span class="calendar-day-more">+${appointments.length - 3} more</span>` : ""}</span>`;
      grid.appendChild(cell);
    }
    renderSelectedCalendarDay();
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
      node.innerHTML = `<div class="calendar-appointment-head"><div><div class="calendar-appointment-title">${esc(item.title)}</div><div class="calendar-appointment-time">${esc(formatDate(item.start_timestamp))}</div></div><div class="calendar-appointment-actions"><button class="calendar-edit-reminders" type="button" data-calendar-edit-reminders="${esc(item.id)}">Edit reminders</button><button class="calendar-cancel" type="button" data-calendar-cancel="${esc(item.id)}">Cancel</button></div></div><div class="calendar-meta">${meta.map(value => `<span>${esc(value)}</span>`).join("")}</div>${item.notes ? `<div>${esc(item.notes)}</div>` : ""}<div class="calendar-reminder-badges">${(item.reminders || []).map(reminderBadge).join("") || '<span class="muted">No reminders</span>'}</div>`;
      root.appendChild(node);
    }
  }

  function reminderState(reminder) {
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
  }

  function renderBadge() {
    const count = (state.appointments || []).length;
    const badge = $("calendar-quick-count");
    badge.textContent = count > 99 ? "99+" : String(count);
    badge.dataset.empty = count ? "false" : "true";
    badge.setAttribute("aria-label", `${count} upcoming appointment${count === 1 ? "" : "s"}`);
  }

  async function loadChannels() {
    const notification = await api("api/notifications");
    for (const select of [$("calendar-destination"), $("calendar-reminder-destination")]) {
      select.replaceChildren(new Option("Notification Center default", ""));
      for (const channel of notification.channels || []) {
        const label = `${channel.platform === "telegram" ? "Telegram · " : ""}${channel.friendly_name}`;
        select.appendChild(new Option(label, channel.entity_id));
      }
    }
  }

  async function loadCalendar() {
    const complete = await api("api/calendar?include_past=true");
    const now = Date.now() / 1000;
    state = {
      ...complete,
      allAppointments: complete.appointments || [],
      appointments: (complete.appointments || []).filter(item => Number(item.end_timestamp || item.start_timestamp || 0) >= now),
    };
    renderMonthCalendar();
    renderAppointments();
    renderReminders();
    renderBadge();
    window.zbranoClearTabChanged?.("calendar-tab");
  }



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

  function showCalendar() {
    if (typeof showPanel === "function") showPanel("calendar");
    else {
      for (const node of document.querySelectorAll("main > section.panel")) node.classList.toggle("hidden", node !== panel);
      for (const node of document.querySelectorAll("nav > button")) node.classList.toggle("active", node === tab);
    }
    loadCalendar().catch(error => { $("calendar-summary").textContent = `Calendar unavailable: ${error.message || error}`; });
    loadChannels().catch(() => {});
    loadGoogleCalendarSync().catch(error => { $("google-calendar-status").textContent = `Google Calendar unavailable: ${error.message || error}`; });
  }

  function showView(name) {
    for (const button of panel.querySelectorAll("[data-calendar-view]")) {
      const active = button.dataset.calendarView === name;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
    }
    for (const view of panel.querySelectorAll("[data-calendar-panel]")) view.classList.toggle("hidden", view.dataset.calendarPanel !== name);
  }



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


  tab.addEventListener("click", event => { event.preventDefault(); event.stopImmediatePropagation(); showCalendar(); }, true);
  quick.addEventListener("click", showCalendar);
  $("calendar-refresh").addEventListener("click", () => loadCalendar().catch(error => { $("calendar-summary").textContent = error.message || String(error); }));
  panel.querySelector(".calendar-subtabs").addEventListener("click", event => {
    const button = event.target.closest("[data-calendar-view]");
    if (button) showView(button.dataset.calendarView);
  });

  $("calendar-month-previous").addEventListener("click", () => {
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
  $("calendar-day-appointments").addEventListener("click", async event => {
    const edit = event.target.closest("[data-calendar-edit-reminders]");
    if (edit) { openReminderEditor(edit.dataset.calendarEditReminders); return; }
    const remove = event.target.closest("[data-calendar-month-delete]");
    if (!remove || !confirm("Delete this appointment and cancel its pending reminders?")) return;
    remove.disabled = true;
    try { await api(`api/calendar/${encodeURIComponent(remove.dataset.calendarMonthDelete)}`, {method:"DELETE"}); await loadCalendar(); }
    catch (error) { $("calendar-month-summary").textContent = `Delete failed: ${error.message || error}`; }
    finally { remove.disabled = false; }
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
    const edit = event.target.closest("[data-calendar-edit-reminders]");
    if (edit) { openReminderEditor(edit.dataset.calendarEditReminders); return; }
    const button = event.target.closest("[data-calendar-cancel]");
    if (!button || !confirm("Cancel this appointment and its pending reminders?")) return;
    button.disabled = true;
    try { await api(`api/calendar/${encodeURIComponent(button.dataset.calendarCancel)}`, {method:"DELETE"}); await loadCalendar(); }
    catch (error) { $("calendar-summary").textContent = `Cancel failed: ${error.message || error}`; }
    finally { button.disabled = false; }
  });

  $("calendar-reminders").addEventListener("click", event => {
    const edit = event.target.closest("[data-calendar-edit-reminders]");
    if (edit) openReminderEditor(edit.dataset.calendarEditReminders);
  });
  panel.querySelector(".calendar-reminder-status").addEventListener("click", event => {
    const button = event.target.closest("[data-reminder-filter]");
    if (!button) return;
    reminderFilter = button.dataset.reminderFilter || "all";
    for (const item of panel.querySelectorAll("[data-reminder-filter]")) item.classList.toggle("active", item === button);
    renderReminders();
  });
  $("calendar-reminder-form").addEventListener("submit", event => { event.preventDefault(); saveReminderEditor(false); });
  $("calendar-reminder-remove-all").addEventListener("click", () => saveReminderEditor(true));
  $("calendar-reminder-editor-close").addEventListener("click", closeReminderEditor);

  document.addEventListener("click", event => {
    const other = event.target.closest?.("#chat-tab,#files-tab,#plugins-tab,#entities-tab,#automations-tab,#settings-tab,#developer-tab");
    if (other) { panel.classList.add("hidden"); tab.classList.remove("active"); }
  }, true);
  loadCalendar().catch(() => {});
  window.setInterval(() => { if (!document.hidden) loadCalendar().catch(() => {}); }, 60000);
  window.zbranoCalendar = {ready:true, open:showCalendar, refresh:loadCalendar};
})();
