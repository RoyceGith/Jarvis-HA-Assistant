(() => {
  const shell = document.getElementById("notification-inbox-shell");
  const toggle = document.getElementById("notification-inbox-toggle");
  const popover = document.getElementById("notification-inbox-popover");
  const list = document.getElementById("notification-inbox-list");
  const badge = document.getElementById("notification-inbox-count");
  const markAll = document.getElementById("notification-inbox-mark-all");
  const openCenter = document.getElementById("notification-inbox-open-center");
  if (!shell || !toggle || !popover || !list || !badge || !markAll || !openCenter) return;

  let notifications = [];
  let unreadCount = 0;
  let openReadTimer = 0;

  async function api(path, options={}) {
    const response = await fetch(path, {cache:"no-store", ...options});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    return data;
  }

  function updateBadge() {
    badge.textContent = unreadCount > 99 ? "99+" : String(unreadCount);
    badge.hidden = unreadCount < 1;
    toggle.setAttribute("aria-label", unreadCount ? `Open notifications · ${unreadCount} unread` : "Open notifications");
  }

  function displayMessage(item) {
    return item.message || item.detail || `${item.status || "Notification"} · ${item.target || "ZBRANO"}`;
  }

  async function decideSuggestion(item, verb, button) {
    button.disabled = true;
    try {
      if (verb === "never_suggest") {
        await api(`api/automations/discoveries/${encodeURIComponent(item.discovery_id)}/feedback`, {
          method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({feedback:"never_suggest"}),
        });
      } else {
        await api(`api/automations/suggestions/${encodeURIComponent(item.id)}/${verb}`, {method:"POST"});
      }
      await loadInbox();
      window.dispatchEvent(new Event("zbrano-notification-center-refresh"));
    } catch (error) {
      button.disabled = false;
      button.title = error.message || String(error);
    }
  }

  function render() {
    list.replaceChildren();
    if (!notifications.length) {
      const empty = document.createElement("div");
      empty.className = "notification-inbox-empty";
      empty.textContent = "No notifications yet.";
      list.appendChild(empty);
    }
    for (const item of notifications) {
      const row = document.createElement("article");
      row.className = "notification-inbox-item";
      row.dataset.unread = String("read_at" in item && !Number(item.read_at || 0));
      row.dataset.severity = item.severity || "information";
      const dot = document.createElement("span");
      dot.className = "notification-inbox-dot";
      dot.setAttribute("aria-hidden", "true");
      const copy = document.createElement("div");
      copy.className = "notification-inbox-copy";
      const title = document.createElement("strong");
      title.textContent = item.title || "ZBRANO notification";
      const message = document.createElement("span");
      message.textContent = displayMessage(item);
      const timestamp = document.createElement("time");
      timestamp.dateTime = new Date(Number(item.created_at || 0) * 1000).toISOString();
      timestamp.textContent = new Date(Number(item.created_at || 0) * 1000).toLocaleString(window.ZbranoI18n?.locale || undefined);
      const suggestion = item.automation_suggestion || {};
      const brain = suggestion.source === "automation_brain";
      const actionable = ((brain && suggestion.status === "pending") || suggestion.status === "approval_required") && suggestion.action_service && suggestion.action_entity;
      const dismissible = ["pending", "approval_required"].includes(suggestion.status);
      if (actionable || dismissible) {
        const controls = document.createElement("div");
        controls.className = "notification-inbox-suggestion-actions";
        if (actionable) {
          const approve = document.createElement("button");
          approve.type = "button";
          approve.textContent = "Approve action";
          approve.addEventListener("click", event => { event.stopPropagation(); decideSuggestion(suggestion, "approve", approve); });
          controls.appendChild(approve);
        }
        if (dismissible) {
          const dismiss = document.createElement("button");
          dismiss.type = "button";
          dismiss.textContent = "Not now";
          dismiss.addEventListener("click", event => { event.stopPropagation(); decideSuggestion(suggestion, "dismiss", dismiss); });
          controls.appendChild(dismiss);
        }
        if (brain && suggestion.discovery_id) {
          const never = document.createElement("button");
          never.type = "button";
          never.textContent = "Never suggest";
          never.addEventListener("click", event => { event.stopPropagation(); decideSuggestion(suggestion, "never_suggest", never); });
          controls.appendChild(never);
        }
        copy.append(title, message, timestamp, controls);
      } else {
        copy.append(title, message, timestamp);
      }
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "notification-inbox-delete";
      remove.setAttribute("aria-label", `Delete ${item.title || "notification"}`);
      remove.title = "Delete notification";
      remove.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3m-8 0 1 13h8l1-13M10 11v5m4-5v5"/></svg>';
      remove.addEventListener("click", async event => {
        event.stopPropagation();
        remove.disabled = true;
        try {
          await api("api/notifications/deliveries", {
            method:"DELETE", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ids:[item.id]}),
          });
          notifications = notifications.filter(notification => notification.id !== item.id);
          if ("read_at" in item && !Number(item.read_at || 0)) unreadCount = Math.max(0, unreadCount - 1);
          render();
          window.dispatchEvent(new Event("zbrano-notification-center-refresh"));
        } catch (_error) {
          remove.disabled = false;
        }
      });
      row.append(dot, copy, remove);
      list.appendChild(row);
    }
    markAll.disabled = unreadCount < 1;
    updateBadge();
  }

  async function loadInbox() {
    try {
      const data = await api("api/notifications/inbox?limit=10");
      notifications = data.notifications || [];
      unreadCount = Number(data.unread_count || 0);
      render();
    } catch (_error) {
      if (!notifications.length) list.innerHTML = '<div class="notification-inbox-empty">Notifications unavailable.</div>';
    }
  }

  async function markRead(ids=[], all=false) {
    if (!all && !ids.length) return;
    const data = await api("api/notifications/inbox/read", {
      method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ids, all}),
    });
    const marked = new Set(ids);
    const now = Date.now() / 1000;
    for (const item of notifications) if (all || marked.has(item.id)) item.read_at = now;
    unreadCount = Number(data.unread_count || 0);
    render();
  }

  function closePopover() {
    window.clearTimeout(openReadTimer);
    popover.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
  }

  function openPopover() {
    popover.hidden = false;
    toggle.setAttribute("aria-expanded", "true");
    loadInbox().then(() => {
      const visibleUnread = notifications.filter(item => "read_at" in item && !Number(item.read_at || 0)).map(item => item.id);
      if (visibleUnread.length) openReadTimer = window.setTimeout(() => markRead(visibleUnread).catch(() => {}), 700);
    });
  }

  toggle.addEventListener("click", event => {
    event.stopPropagation();
    popover.hidden ? openPopover() : closePopover();
  });
  popover.addEventListener("click", event => event.stopPropagation());
  markAll.addEventListener("click", () => markRead([], true).catch(() => {}));
  openCenter.addEventListener("click", () => {
    closePopover();
    document.getElementById("automations-tab")?.click();
    requestAnimationFrame(() => {
      document.querySelector('[data-auto-view="notifications"]')?.click();
      document.querySelector('[data-notification-view="logs"]')?.click();
    });
  });
  document.addEventListener("click", event => { if (!shell.contains(event.target)) closePopover(); });
  document.addEventListener("keydown", event => { if (event.key === "Escape") closePopover(); });
  window.addEventListener("zbrano-notification-inbox-refresh", loadInbox);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) loadInbox(); });
  loadInbox();
  window.setInterval(() => { if (!document.hidden) loadInbox(); }, 20000);
  window.zbranoNotificationInbox = {load:loadInbox, open:openPopover, close:closePopover};
})();
