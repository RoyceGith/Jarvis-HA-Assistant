(() => {
  const tab = document.querySelector('[data-auto-view="notifications"]');
  const panel = document.querySelector('[data-auto-panel="notifications"]');
  if (!tab || !panel) return;
  const $ = id => document.getElementById(id);
  let state = {settings:{}, channels:[], watches:[], deliveries:[]};
  const selectedDeliveries = new Set();

  async function api(path, options={}) {
    const response = await fetch(path, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    return data;
  }

  function option(select, channel) {
    const node = document.createElement("option");
    node.value = channel.entity_id;
    node.textContent = `${channel.platform === "telegram" ? "Telegram · " : ""}${channel.friendly_name}`;
    select.appendChild(node);
  }

  function renderChannels() {
    const root = $("notification-channels"); root.replaceChildren();
    const defaultSelect = $("notification-default-channel");
    const testSelect = $("notification-test-target");
    defaultSelect.replaceChildren(new Option("Choose a Home Assistant notify entity", ""));
    testSelect.replaceChildren(new Option("Choose channel", ""));
    for (const channel of state.channels) {
      option(defaultSelect, channel); option(testSelect, channel);
      const row = document.createElement("div"); row.className = "notification-channel";
      const head = document.createElement("div"); head.className = "notification-channel-head";
      const name = document.createElement("strong"); name.textContent = channel.friendly_name;
      const platform = document.createElement("span"); platform.className = "notification-platform"; platform.textContent = channel.platform;
      const id = document.createElement("code"); id.textContent = channel.entity_id;
      const availability = document.createElement("small"); availability.textContent = channel.available ? "Available" : `Unavailable · ${channel.state || "unknown"}`;
      head.append(name, platform); row.append(head, id, availability); root.appendChild(row);
    }
    if (!state.channels.length) root.innerHTML = '<div class="autonomy-empty">No Home Assistant notify entities found. Finish the Telegram bot integration and add an allowed chat ID.</div>';
    defaultSelect.value = state.settings.default_channel || "";
    testSelect.value = state.settings.default_channel || "";
  }

  function renderSettings() {
    $("notification-suggestions").checked = state.settings.suggestion_notifications !== false;
    $("notification-actions").checked = state.settings.autonomous_action_notifications !== false;
    $("notification-quiet-enabled").checked = Boolean(state.settings.quiet_hours_enabled);
    $("notification-quiet-start").value = state.settings.quiet_hours_start || "22:00";
    $("notification-quiet-end").value = state.settings.quiet_hours_end || "07:00";
    $("notification-critical-override").checked = state.settings.critical_override !== false;
    $("notification-critical-repeat").value = String(state.settings.repeat_critical_minutes ?? 15);
  }

  function showNotificationView(name) {
    for (const button of panel.querySelectorAll("[data-notification-view]")) {
      const active = button.dataset.notificationView === name;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
    }
    for (const view of panel.querySelectorAll("[data-notification-panel]")) {
      view.classList.toggle("hidden", view.dataset.notificationPanel !== name);
    }
  }

  panel.querySelector(".notification-subtabs")?.addEventListener("click", event => {
    const button = event.target.closest("[data-notification-view]");
    if (button) showNotificationView(button.dataset.notificationView);
  });

  function renderWatchlist() {
    const root = $("notification-watchlist"); root.replaceChildren();
    const watches = state.watches || [];
    $("notification-watch-count").textContent = `${watches.length} watch${watches.length === 1 ? "" : "es"}`;
    for (const watch of watches) {
      const row = document.createElement("div"); row.className = "notification-watch"; row.dataset.status = watch.status || "armed";
      const head = document.createElement("div"); head.className = "notification-watch-head";
      const summary = document.createElement("div");
      const name = document.createElement("strong"); name.textContent = watch.name || "Notification watch";
      const objective = document.createElement("div"); objective.textContent = watch.objective || "";
      summary.append(name, objective);
      const actions = document.createElement("div"); actions.className = "notification-watch-actions";
      const toggle = document.createElement("button"); toggle.type = "button"; toggle.dataset.watchToggle = watch.id; toggle.textContent = watch.enabled ? "Pause" : "Arm";
      const remove = document.createElement("button"); remove.type = "button"; remove.dataset.watchDelete = watch.id; remove.textContent = "Delete";
      actions.append(toggle, remove); head.append(summary, actions);
      const meta = document.createElement("div"); meta.className = "notification-watch-meta";
      const values = [watch.status || "armed", watch.severity || "information", watch.one_shot ? "one-time" : "repeating", `${watch.cooldown_minutes || 0} min cooldown`];
      if (watch.active_start && watch.active_end) values.push(`${watch.active_start}–${watch.active_end}`);
      for (const value of values) { const chip = document.createElement("span"); chip.textContent = value; meta.appendChild(chip); }
      const detail = document.createElement("small");
      const last = watch.last_triggered_at ? new Date(watch.last_triggered_at * 1000).toLocaleString() : "never";
      detail.textContent = `${watch.trigger_entity} → ${watch.trigger_state} · ${watch.destination} · triggered ${watch.trigger_count || 0} time(s) · last ${last}`;
      row.append(head, meta, detail); root.appendChild(row);
    }
    if (!watches.length) root.innerHTML = '<div class="autonomy-empty">No notification watches. In Chat, try “Notify me when the workshop door opens.”</div>';
  }

  function updateDeliverySelection() {
    const available = new Set((state.deliveries || []).map(item => item.id));
    for (const id of [...selectedDeliveries]) if (!available.has(id)) selectedDeliveries.delete(id);
    const count = selectedDeliveries.size;
    const all = (state.deliveries || []).length;
    $("notification-log-selection-count").textContent = `${count} selected`;
    $("notification-log-delete").disabled = count === 0;
    const selectAll = $("notification-log-select-all");
    selectAll.checked = all > 0 && count === all;
    selectAll.indeterminate = count > 0 && count < all;
  }

  function renderDeliveries() {
    const root = $("notification-deliveries"); root.replaceChildren();
    for (const delivery of state.deliveries || []) {
      const row = document.createElement("div"); row.className = "notification-delivery"; row.dataset.status = delivery.status;
      const head = document.createElement("div"); head.className = "notification-delivery-head";
      const titleGroup = document.createElement("label"); titleGroup.className = "notification-delivery-title";
      const checkbox = document.createElement("input"); checkbox.type = "checkbox"; checkbox.className = "notification-delivery-select"; checkbox.checked = selectedDeliveries.has(delivery.id); checkbox.setAttribute("aria-label", `Select ${delivery.title || "notification"}`);
      checkbox.addEventListener("change", () => { checkbox.checked ? selectedDeliveries.add(delivery.id) : selectedDeliveries.delete(delivery.id); updateDeliverySelection(); });
      const title = document.createElement("strong"); title.textContent = delivery.title || "Notification";
      const status = document.createElement("span"); status.className = "notification-platform"; status.textContent = delivery.status;
      const detail = document.createElement("small"); detail.textContent = `${delivery.target} · ${delivery.severity} · ${new Date(delivery.created_at * 1000).toLocaleString()}`;
      const evidence = document.createElement("small"); evidence.textContent = delivery.detail || "";
      titleGroup.append(checkbox, title); head.append(titleGroup, status); row.append(head, detail, evidence); root.appendChild(row);
    }
    if (!state.deliveries?.length) root.innerHTML = '<div class="autonomy-empty">No deliveries recorded.</div>';
    updateDeliverySelection();
  }

  async function load() {
    const status = $("notification-settings-status"); status.textContent = "Discovering channels…";
    try {
      state = await api("api/notifications");
      renderChannels(); renderSettings(); renderWatchlist(); renderDeliveries();
      $("notification-credential-boundary").textContent = state.credential_boundary || "";
      status.textContent = `${state.channels.length} channel(s); ${state.telegram_channels || 0} Telegram`;
    } catch (error) { status.textContent = `Load failed: ${error.message || error}`; }
  }

  $("notification-settings-form").addEventListener("submit", async event => {
    event.preventDefault(); const status = $("notification-settings-status"); status.textContent = "Saving…";
    const body = {
      default_channel: $("notification-default-channel").value,
      suggestion_notifications: $("notification-suggestions").checked,
      autonomous_action_notifications: $("notification-actions").checked,
      quiet_hours_enabled: $("notification-quiet-enabled").checked,
      quiet_hours_start: $("notification-quiet-start").value,
      quiet_hours_end: $("notification-quiet-end").value,
      critical_override: $("notification-critical-override").checked,
      repeat_critical_minutes: Number($("notification-critical-repeat").value || 0),
    };
    try { await api("api/notifications/settings", {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)}); status.textContent = "Notification policy saved."; await load(); }
    catch (error) { status.textContent = `Save failed: ${error.message || error}`; }
  });

  $("notification-test-form").addEventListener("submit", async event => {
    event.preventDefault(); const status = $("notification-test-status"); status.textContent = "Sending…";
    const body = {target:$("notification-test-target").value, severity:$("notification-test-severity").value, title:$("notification-test-title").value, message:$("notification-test-message").value};
    try { await api("api/notifications/test", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)}); status.textContent = "Delivered through Home Assistant."; await load(); }
    catch (error) { status.textContent = `Delivery failed: ${error.message || error}`; await load(); }
  });


  $("notification-watchlist").addEventListener("click", async event => {
    const toggle = event.target.closest("[data-watch-toggle]");
    if (toggle) {
      const watch = (state.watches || []).find(item => item.id === toggle.dataset.watchToggle);
      if (!watch) return;
      toggle.disabled = true;
      try { await api(`api/notifications/watches/${encodeURIComponent(watch.id)}/state`, {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({enabled:!watch.enabled})}); await load(); }
      catch (error) { $("notification-settings-status").textContent = `Watch update failed: ${error.message || error}`; toggle.disabled = false; }
      return;
    }
    const remove = event.target.closest("[data-watch-delete]");
    if (remove) {
      if (!confirm("Delete this notification watch?")) return;
      remove.disabled = true;
      try { await api(`api/notifications/watches/${encodeURIComponent(remove.dataset.watchDelete)}`, {method:"DELETE"}); await load(); }
      catch (error) { $("notification-settings-status").textContent = `Watch delete failed: ${error.message || error}`; remove.disabled = false; }
    }
  });
  $("notification-log-select-all").addEventListener("change", event => {
    selectedDeliveries.clear();
    if (event.target.checked) for (const delivery of state.deliveries || []) selectedDeliveries.add(delivery.id);
    renderDeliveries();
  });

  $("notification-log-delete").addEventListener("click", async () => {
    const ids = [...selectedDeliveries];
    if (!ids.length) return;
    const button = $("notification-log-delete"); button.disabled = true; button.textContent = "Deleting…";
    try {
      await api("api/notifications/deliveries", {method:"DELETE", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ids})});
      selectedDeliveries.clear(); await load();
    } catch (error) {
      $("notification-log-selection-count").textContent = `Delete failed: ${error.message || error}`;
    } finally { button.textContent = "Delete selected"; updateDeliverySelection(); }
  });

  tab.addEventListener("click", load);
  $("notification-refresh").addEventListener("click", load);
  window.zbranoNotificationCenter = {load, showView:showNotificationView};
})();
