(() => {
  const panel = document.getElementById("entities-panel");
  const grid = document.getElementById("device-grid");
  if (!panel || !grid) return;
  const $ = id => document.getElementById(id);
  const t = text => window.ZbranoI18n?.t(text) || text;
  const keyOf = entity => entity.device_id ? `device:${entity.device_id}` : `entity:${entity.entity_id}`;
  const roomOf = entity => JSON.stringify([entity.site_name || "", entity.area_id || entity.area_name || ""]);
  const readSaved = (key, fallback) => { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } };
  const savedFavorites = readSaved("zbrano_device_favorites_v1", []);
  const favorites = new Set(Array.isArray(savedFavorites) ? savedFavorites.filter(item => typeof item === "string") : []);
  let location = "all", quick = "", selected = "", limit = 60, groups = new Map();
  let layout = readSaved("zbrano_entity_view_v1", "cards") === "table" ? "table" : "cards";
  const node = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  };
  const userText = (tag, className, text) => { const element = node(tag, className, text); element.dataset.i18nIgnore = ""; return element; };
  function icon(entity) {
    const paths = {
      light: '<path d="M9 18h6m-5 3h4M8 14a6 6 0 1 1 8 0c-1 1-1 2-1 2H9s0-1-1-2Z"/>',
      climate: '<path d="M12 3v18M4 7l16 10M4 17 20 7M9 5l3 3 3-3M9 19l3-3 3 3"/>',
      switch: '<rect x="3" y="7" width="18" height="10" rx="5"/><circle cx="15" cy="12" r="2"/>',
      sensor: '<path d="M9 14V6a3 3 0 0 1 6 0v8a5 5 0 1 1-6 0Z"/><path d="M12 8v9"/>',
      binary_sensor: '<path d="M4 8a12 12 0 0 1 16 0M7 12a7 7 0 0 1 10 0M10 16a3 3 0 0 1 4 0"/><circle cx="12" cy="20" r="1"/>',
    };
    const element = node("span", "device-symbol");
    element.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true">${paths[entity.domain] || '<rect x="4" y="4" width="16" height="16" rx="4"/><path d="M9 12h6m-3-3v6"/>'}</svg>`;
    return element;
  }
  function access(entity) {
    const review = ensureReview(entity);
    if (!review.selected || review.access === "restricted") return "Not allowed";
    return review.access === "low_risk_control_proposed" ? "Control" : "Read only";
  }
  function groupAccess(group) {
    const values = new Set(group.entities.map(access));
    return values.size === 1 ? [...values][0] : "Mixed access";
  }
  function rebuildGroups() {
    groups = new Map();
    for (const entity of entityInventory) {
      const key = keyOf(entity);
      if (!groups.has(key)) groups.set(key, {key, entities: []});
      groups.get(key).entities.push(entity);
    }
    for (const group of groups.values()) {
      group.primary = group.entities.find(entity => entity.domain === "climate") || group.entities.find(entity => entity.control_capable) || group.entities[0];
      group.name = group.primary.device_name || group.entities.find(entity => entity.device_name)?.device_name || group.primary.friendly_name;
    }
  }
  function matches(entity) {
    const matchLocation = location === "all" || (location === "favorites" ? favorites.has(keyOf(entity)) : location === "unassigned" ? !entity.area_id && !entity.area_name : roomOf(entity) === location);
    const matchQuick = !quick || (quick === "unavailable" ? !entity.available : quick === "sensors" ? ["sensor", "binary_sensor"].includes(entity.domain) : entity.domain === quick);
    return matchLocation && matchQuick;
  }
  function navigate(value) {
    location = value; selected = ""; limit = 60;
    document.querySelector('[data-entity-view="inventory"]').click();
    renderEntities();
  }
  function navigation() {
    const root = $("device-room-nav"); root.replaceChildren();
    const add = (label, value, count, parent = root) => {
      const button = node("button", "device-room-link"); button.type = "button";
      button.dataset.deviceLocation = value;
      button.setAttribute("aria-pressed", String(location === value));
      button.append(userText("span", "", label), node("small", "", String(count)));
      button.addEventListener("click", () => navigate(value)); parent.append(button);
    };
    add(t("All devices"), "all", groups.size);
    add(t("Favorites"), "favorites", [...groups.keys()].filter(key => favorites.has(key)).length);
    add(t("Unassigned"), "unassigned", new Set(entityInventory.filter(entity => !entity.area_id && !entity.area_name).map(keyOf)).size);
    const sites = new Map();
    for (const entity of entityInventory) {
      if (!entity.area_id && !entity.area_name) continue;
      const site = entity.site_name || t("Rooms");
      if (!sites.has(site)) sites.set(site, new Map());
      const rooms = sites.get(site), key = roomOf(entity);
      if (!rooms.has(key)) rooms.set(key, {name: entity.area_name || t("Unassigned"), keys: new Set()});
      rooms.get(key).keys.add(keyOf(entity));
    }
    for (const [site, rooms] of [...sites].sort(([a], [b]) => a.localeCompare(b))) {
      root.append(userText("h3", "device-site-title", site));
      for (const [key, room] of [...rooms].sort(([, a], [, b]) => a.name.localeCompare(b.name))) add(room.name, key, room.keys.size);
    }
  }
  function refreshAccess() {
    for (const badge of panel.querySelectorAll("[data-device-access]")) {
      const group = groups.get(badge.dataset.deviceAccess);
      if (group) badge.textContent = t(groupAccess(group));
    }
  }
  function closeDetails() {
    const previous = selected; selected = "";
    $("device-details").hidden = true;
    $("device-browser").classList.remove("has-details");
    for (const button of grid.querySelectorAll("[data-device-open]")) {
      button.setAttribute("aria-expanded", "false");
      if (button.dataset.deviceOpen === previous) button.focus();
    }
  }
  function details(group, focus = false) {
    const root = $("device-details"); root.replaceChildren(); root.hidden = false;
    $("device-browser").classList.add("has-details");
    const header = node("header", "device-detail-heading");
    const title = userText("h3", "", group.name); title.id = "device-detail-title";
    const close = node("button", "device-close", "×"); close.type = "button";
    close.setAttribute("aria-label", t("Close device details")); close.addEventListener("click", closeDetails);
    header.append(title, close); root.append(header);
    root.append(node("p", "device-detail-help", t("Permissions apply to each entity separately.")));
    for (const entity of group.entities) {
      const review = ensureReview(entity);
      const section = node("details", "device-entity"); section.dataset.deviceEntity = entity.entity_id;
      section.open = group.entities.length === 1 || entity === group.primary;
      const summary = node("summary", "");
      summary.append(userText("strong", "", entity.friendly_name), userText("span", "", entityStateLabel(entity)));
      section.append(summary);
      const fields = node("div", "device-entity-fields");
      const enabled = node("input"); enabled.type = "checkbox"; enabled.checked = review.selected;
      const allowLabel = node("label", "device-allow"); allowLabel.append(enabled, node("span", "", t("Allow ZBRANO")));
      const select = node("select"); select.setAttribute("aria-label", t("Device access"));
      for (const [value, label] of entityAccessOptions(entity, review.access)) {
        const option = node("option", "", t(label)); option.value = value; select.append(option);
      }
      select.value = review.access;
      const history = node("button", "device-history", t("View history")); history.type = "button";
      history.disabled = !review.selected || review.access === "restricted";
      const changed = () => {
        history.disabled = !review.selected || review.access === "restricted";
        updateSelectionSummary(); refreshAccess(); queuePolicySave(entity, review);
      };
      enabled.addEventListener("change", () => {
        review.selected = enabled.checked;
        if (review.selected && review.access === "restricted") review.access = defaultAllowedEntityAccess(entity);
        select.value = review.access; changed();
      });
      select.addEventListener("change", () => {
        review.access = select.value;
        if (review.access === "restricted") review.selected = enabled.checked = false;
        changed();
      });
      const aliases = node("input"); aliases.value = review.aliases;
      aliases.placeholder = t("Other names, separated by commas");
      aliases.setAttribute("aria-label", t("Other names"));
      aliases.addEventListener("input", () => { review.aliases = aliases.value; backupEntityAliases(entity.entity_id, review.aliases); queuePolicySave(entity, review, 600); });
      aliases.addEventListener("blur", () => flushEntityPolicy(entity, review));
      aliases.addEventListener("keydown", event => { if (event.key === "Enter") { event.preventDefault(); aliases.blur(); } });
      history.addEventListener("click", () => {
        $("ha-history-entities").value = entity.entity_id;
        window.zbranoHaHistory?.show();
        window.zbranoHaHistory?.load().catch(error => { $("ha-history-status").textContent = String(error.message || error); });
      });
      const metadata = node("details", "device-technical");
      metadata.append(node("summary", "", t("Entity details")), userText("code", "", entity.entity_id), userText("p", "", [entity.area_name, entity.site_name, ...(entity.labels || []), entity.device_class, entity.unit].filter(Boolean).join(" · ")));
      fields.append(allowLabel, select, aliases, history, metadata); section.append(fields); root.append(section);
    }
    if (focus) close.focus();
  }
  function render(filtered) {
    rebuildGroups(); navigation();
    panel.dataset.deviceLayout = layout;
    const table = entityRows.closest(".table-wrap"); table.hidden = layout !== "table";
    $("device-browser").hidden = layout === "table";
    const visibleKeys = new Set(filtered.map(keyOf));
    const visible = [...groups.values()].filter(group => visibleKeys.has(group.key)).sort((a, b) => a.name.localeCompare(b.name));
    $("device-result-count").textContent = `${visible.length} ${t(visible.length === 1 ? "device" : "devices")} · ${filtered.length} ${t(filtered.length === 1 ? "entity" : "entities")}`;
    if (layout === "table") return false;
    grid.replaceChildren();
    if (!visible.length) grid.append(node("p", "device-empty", t("No devices match. Try another room or clear the filters.")));
    for (const group of visible.slice(0, limit)) {
      const card = node("article", "device-card");
      const open = node("button", "device-card-open"); open.type = "button";
      open.dataset.deviceOpen = group.key; open.setAttribute("aria-controls", "device-details"); open.setAttribute("aria-expanded", String(selected === group.key));
      open.append(icon(group.primary), userText("strong", "device-name", group.name));
      open.append(userText("small", "device-room", group.primary.area_name || t("Unassigned")));
      open.append(userText("span", "device-state", group.primary.available ? entityStateLabel(group.primary) + (group.primary.unit && group.primary.domain !== "climate" ? ` ${group.primary.unit}` : "") : t("Unavailable")));
      const badge = node("span", "device-access", t(groupAccess(group))); badge.dataset.deviceAccess = group.key;
      const footer = node("span", "device-card-footer"); footer.append(badge, node("small", "", `${group.entities.length} ${t(group.entities.length === 1 ? "entity" : "entities")}`)); open.append(footer);
      open.addEventListener("click", () => {
        selected = group.key;
        for (const button of grid.querySelectorAll("[data-device-open]")) button.setAttribute("aria-expanded", String(button === open));
        details(group, true);
      });
      const star = node("button", "device-favorite", favorites.has(group.key) ? "★" : "☆"); star.type = "button";
      star.setAttribute("aria-label", t("Favorite device")); star.setAttribute("aria-pressed", String(favorites.has(group.key)));
      star.addEventListener("click", () => {
        if (favorites.has(group.key)) favorites.delete(group.key); else favorites.add(group.key);
        try { localStorage.setItem("zbrano_device_favorites_v1", JSON.stringify([...favorites])); } catch {}
        renderEntities();
      });
      card.append(open, star); grid.append(card);
    }
    $("device-show-more").hidden = visible.length <= limit;
    if (selected && visibleKeys.has(selected) && groups.has(selected)) details(groups.get(selected));
    else { selected = ""; $("device-details").hidden = true; $("device-browser").classList.remove("has-details"); }
    return true;
  }
  $("entity-layout").value = layout;
  $("entity-layout").addEventListener("change", event => {
    layout = event.target.value; selected = "";
    try { localStorage.setItem("zbrano_entity_view_v1", JSON.stringify(layout)); } catch {}
    renderEntities();
  });
  $("device-show-more").addEventListener("click", () => { limit += 60; renderEntities(); });
  $("device-clear-filters").addEventListener("click", () => {
    location = "all"; quick = ""; entitySearch.value = domainFilter.value = ""; entityPermissionFilter = "all";
    for (const button of entityPermissionGuide.querySelectorAll("[data-entity-permission-filter]")) button.setAttribute("aria-pressed", String(button.dataset.entityPermissionFilter === "all"));
    for (const button of $("device-quick-filters").querySelectorAll("button")) button.setAttribute("aria-pressed", String(button.dataset.deviceFilter === ""));
    renderEntities();
  });
  for (const button of $("device-quick-filters").querySelectorAll("[data-device-filter]")) button.addEventListener("click", () => {
    quick = button.dataset.deviceFilter; domainFilter.value = ""; limit = 60;
    for (const peer of $("device-quick-filters").querySelectorAll("button")) peer.setAttribute("aria-pressed", String(peer === button));
    renderEntities();
  });
  panel.addEventListener("keydown", event => { if (event.key === "Escape" && selected) { event.preventDefault(); closeDetails(); } });
  let locale = window.ZbranoI18n?.locale;
  window.addEventListener("zbrano:language-applied", () => {
    if (locale === window.ZbranoI18n?.locale) return;
    locale = window.ZbranoI18n?.locale;
    if (inventoryLoaded) renderEntities();
  });
  window.zbranoDeviceBrowser = {render, matches, refreshAccess};
  if (inventoryLoaded) renderEntities();
})();
