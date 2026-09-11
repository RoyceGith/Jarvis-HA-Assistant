(() => {
  if (typeof loadPlugins !== "function") return;
  const pluginListNode = document.getElementById("plugin-list");
  if (!pluginListNode) return;

  function compactPluginRows() {
    for (const row of pluginListNode.querySelectorAll(".plugin-row")) {
      const head = row.querySelector(".plugin-head");
      if (!head) continue;

      let settings = row.querySelector(":scope > .plugin-settings");
      if (!settings) {
        settings = document.createElement("div");
        settings.className = "plugin-settings";
        row.appendChild(settings);
      }
      const movable = [...row.children].filter(child => child !== head && child !== settings);
      for (const child of movable) settings.appendChild(child);
      if (settings !== row.lastElementChild) row.appendChild(settings);
      row.classList.add("compact-plugin");

      const actions = head.querySelector(".plugin-actions") || head;
      if (!actions.querySelector(".plugin-settings-toggle")) {
        const toggle = document.createElement("button");
        toggle.type = "button";
        toggle.className = "plugin-settings-toggle";
        toggle.dataset.a = "settings";
        toggle.setAttribute("aria-expanded", row.classList.contains("open") ? "true" : "false");
        toggle.textContent = "Settings";
        actions.prepend(toggle);
      }
    }
  }

  const baseLoadPlugins = loadPlugins;
  loadPlugins = async function(...args) {
    const result = await baseLoadPlugins.apply(this, args);
    compactPluginRows();
    return result;
  };

  const pluginRowsObserver = new MutationObserver(compactPluginRows);
  pluginRowsObserver.observe(pluginListNode, {childList: true});

  pluginListNode.addEventListener("click", event => {
    const toggle = event.target.closest("button.plugin-settings-toggle");
    if (!toggle) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const row = toggle.closest(".plugin-row");
    const willOpen = !row.classList.contains("open");
    for (const other of pluginListNode.querySelectorAll(".plugin-row.open")) {
      other.classList.remove("open");
      other.querySelector(".plugin-settings-toggle")?.setAttribute("aria-expanded", "false");
    }
    row.classList.toggle("open", willOpen);
    toggle.setAttribute("aria-expanded", willOpen ? "true" : "false");
  }, true);

  compactPluginRows();
})();
