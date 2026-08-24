(() => {
  const bindings = [];

  function isViewed(button, panel) {
    const selected = button.classList.contains("active") || button.getAttribute("aria-selected") === "true";
    return selected && !panel.hidden && !panel.closest(".hidden");
  }

  function mark(button) {
    if (!button || button.classList.contains("zbrano-tab-unseen")) return;
    button.classList.add("zbrano-tab-unseen");
    if (!button.hasAttribute("aria-label")) {
      button.dataset.zbranoActivityLabel = "generated";
      button.setAttribute("aria-label", `${button.textContent.trim()} · new activity`);
    }
  }

  function clear(button) {
    if (!button) return;
    button.classList.remove("zbrano-tab-unseen");
    if (button.dataset.zbranoActivityLabel === "generated") {
      button.removeAttribute("aria-label");
      delete button.dataset.zbranoActivityLabel;
    }
  }

  function bind(button, panel) {
    if (!button || !panel || bindings.some(item => item.button === button)) return;
    button.addEventListener("click", () => requestAnimationFrame(() => clear(button)));
    bindings.push({button, panel});
  }

  function markIfUnseen(button) {
    const binding = bindings.find(item => item.button === button);
    if (binding && !isViewed(binding.button, binding.panel)) mark(binding.button);
  }

  for (const name of ["chat", "files", "plugins", "entities", "calendar", "automations", "settings", "developer"]) {
    bind(document.getElementById(`${name}-tab`), document.getElementById(`${name}-panel`));
  }
  for (const button of document.querySelectorAll("[data-auto-view]")) {
    bind(button, document.querySelector(`[data-auto-panel="${CSS.escape(button.dataset.autoView)}"]`));
  }
  for (const button of document.querySelectorAll("[data-notification-view]")) {
    bind(button, document.querySelector(`[data-notification-panel="${CSS.escape(button.dataset.notificationView)}"]`));
  }
  for (const button of document.querySelectorAll(".settings-category-tab[data-settings-target]")) {
    bind(button, document.querySelector(`[data-settings-category="${CSS.escape(button.dataset.settingsTarget)}"]`));
  }
  for (const button of document.querySelectorAll("#plugins-installed-tab, #plugins-browse-tab")) {
    bind(button, document.getElementById(button.getAttribute("aria-controls")));
  }

  window.zbranoMarkTabChanged = tabId => markIfUnseen(document.getElementById(tabId));
  window.zbranoClearTabChanged = tabId => clear(document.getElementById(tabId));
  document.addEventListener("click", event => {
    const button = event.target.closest?.(
      "#chat-tab,#files-tab,#plugins-tab,#entities-tab,#calendar-tab,#automations-tab,#settings-tab,#developer-tab,[data-auto-view],[data-notification-view],.settings-category-tab[data-settings-target],#plugins-installed-tab,#plugins-browse-tab"
    );
    if (!button) return;
    clear(button);
    requestAnimationFrame(() => clear(button));
  }, true);

  const nativeFetch = window.fetch.bind(window);
  window.fetch = async (...args) => {
    const response = await nativeFetch(...args);
    try {
      const request = args[0];
      const options = args[1] || {};
      const method = String(options.method || (request instanceof Request ? request.method : "GET")).toUpperCase();
      const url = new URL(request instanceof Request ? request.url : String(request), document.baseURI);
      if (response.ok && !["GET", "HEAD", "OPTIONS"].includes(method)) {
        const path = url.pathname;
        if (path.includes("/api/files/")) markIfUnseen(document.getElementById("files-tab"));
        if (path.includes("/api/plugins")) markIfUnseen(document.getElementById("plugins-tab"));
        if (path.includes("/api/automations")) {
          markIfUnseen(document.getElementById("automations-tab"));
          markIfUnseen(document.querySelector('[data-auto-view="library"]'));
        }
        if (path.includes("/api/calendar")) markIfUnseen(document.getElementById("calendar-tab"));
        if (path.includes("/api/notifications")) {
          markIfUnseen(document.getElementById("automations-tab"));
          markIfUnseen(document.querySelector('[data-auto-view="notifications"]'));
          if (path.endsWith("/test")) markIfUnseen(document.querySelector('[data-notification-view="logs"]'));
        }
      }
    } catch (_) {}
    return response;
  };

  window.addEventListener("message", event => {
    if (event.origin === window.location.origin && event.data?.type === "zbrano-plugin-oauth") {
      markIfUnseen(document.getElementById("plugins-tab"));
    }
  });

  let activityRevisions = null;
  const activityTargets = {
    chat: ["#chat-tab"],
    files: ["#files-tab"],
    plugins: ["#plugins-tab"],
    automations: ["#automations-tab", '[data-auto-view="library"]'],
    notifications: ["#automations-tab", '[data-auto-view="notifications"]', '[data-notification-view="logs"]'],
    calendar: ["#calendar-tab"],
    settings: ["#settings-tab"],
    developer: ["#developer-tab"],
  };

  async function checkSemanticActivity() {
    try {
      const response = await nativeFetch("api/tab-activity", {cache:"no-store"});
      if (!response.ok) return;
      const payload = await response.json();
      const revisions = payload.revisions || {};
      if (activityRevisions !== null) {
        for (const [name, revision] of Object.entries(revisions)) {
          if (activityRevisions[name] === revision) continue;
          for (const selector of activityTargets[name] || []) markIfUnseen(document.querySelector(selector));
        }
      }
      activityRevisions = revisions;
      for (const binding of bindings) {
        if (isViewed(binding.button, binding.panel)) clear(binding.button);
      }
    } catch (_) {}
  }

  checkSemanticActivity();
  setInterval(checkSemanticActivity, 10000);
})();
