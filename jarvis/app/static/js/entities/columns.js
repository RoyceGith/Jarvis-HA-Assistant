(() => {
  const STORAGE_KEY = "zbrano_entity_column_layout_v1";
  const DEFAULTS = [
    {key:"select", label:"Select", width:76, min:62},
    {key:"name", label:"Friendly name", width:190, min:90},
    {key:"entity_id", label:"Entity ID", width:230, min:110},
    {key:"domain", label:"Domain", width:110, min:74},
    {key:"area", label:"Area", width:150, min:88},
    {key:"site", label:"Site / Zone", width:170, min:100},
    {key:"labels", label:"HA Labels", width:220, min:120},
    {key:"state", label:"State", width:110, min:72},
    {key:"class_unit", label:"Class / unit", width:150, min:88},
    {key:"access", label:"Access", width:210, min:125},
    {key:"aliases", label:"Aliases", width:220, min:110},
  ];
  const defaultOrder = DEFAULTS.map(column => column.key);
  const definitions = new Map(DEFAULTS.map(column => [column.key, column]));
  const table = document.querySelector("#entities-panel .table-wrap table");
  const rows = document.getElementById("entity-rows");
  if (!table || !rows) return;

  function loadLayout() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
      const order = Array.isArray(saved?.order)
        ? saved.order.filter(key => definitions.has(key))
        : [];
      for (const key of defaultOrder) if (!order.includes(key)) order.push(key);
      const widths = {};
      for (const key of defaultOrder) {
        const definition = definitions.get(key);
        const requested = Number(saved?.widths?.[key]);
        widths[key] = Number.isFinite(requested)
          ? Math.max(definition.min, Math.min(700, Math.round(requested)))
          : definition.width;
      }
      return {order, widths};
    } catch (_) {
      return {
        order:[...defaultOrder],
        widths:Object.fromEntries(DEFAULTS.map(column => [column.key, column.width])),
      };
    }
  }

  let layout = loadLayout();
  let draggedKey = "";
  let resizing = null;

  function saveLayout() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
  }

  function ensureMetadata() {
    const headers = [...table.tHead?.rows?.[0]?.cells || []];
    headers.forEach((header, index) => {
      if (!header.dataset.entityColumn) header.dataset.entityColumn = defaultOrder[index] || `column_${index}`;
      header.draggable = true;
      header.title = "Drag to move this column. Drag the right edge to resize it.";
      if (!header.querySelector(".entity-column-resizer")) {
        const resizer = document.createElement("span");
        resizer.className = "entity-column-resizer";
        resizer.setAttribute("role", "separator");
        resizer.setAttribute("aria-label", `Resize ${header.textContent.trim()} column`);
        header.appendChild(resizer);
      }
    });
    for (const row of rows.rows) {
      [...row.cells].forEach((cell, index) => {
        if (!cell.dataset.entityColumn) cell.dataset.entityColumn = defaultOrder[index] || `column_${index}`;
      });
    }
  }

  function reorderRow(row) {
    const cells = new Map([...row.cells].map(cell => [cell.dataset.entityColumn, cell]));
    const current = [...row.cells].map(cell => cell.dataset.entityColumn);
    if (current.join("|") === layout.order.join("|")) return;
    for (const key of layout.order) {
      const cell = cells.get(key);
      if (cell) row.appendChild(cell);
    }
  }

  function applyWidths() {
    let total = 0;
    for (const key of layout.order) total += layout.widths[key] || definitions.get(key)?.width || 100;
    table.style.width = `${total}px`;
    table.style.minWidth = `${total}px`;
    for (const row of [table.tHead?.rows?.[0], ...rows.rows]) {
      if (!row) continue;
      for (const cell of row.cells) {
        const width = layout.widths[cell.dataset.entityColumn];
        if (!width) continue;
        cell.style.width = `${width}px`;
        cell.style.minWidth = `${width}px`;
        cell.style.maxWidth = `${width}px`;
      }
    }
  }

  function applyLayout() {
    ensureMetadata();
    const headerRow = table.tHead?.rows?.[0];
    if (headerRow) reorderRow(headerRow);
    for (const row of rows.rows) reorderRow(row);
    applyWidths();
  }
  window.zbranoApplyEntityColumnLayout = applyLayout;

  function clearDropTargets() {
    table.querySelectorAll(".entity-column-drop-target").forEach(item => item.classList.remove("entity-column-drop-target"));
  }

  table.addEventListener("dragstart", event => {
    if (event.target.closest?.(".entity-column-resizer")) {
      event.preventDefault();
      return;
    }
    const header = event.target.closest?.("th[data-entity-column]");
    if (!header) return;
    draggedKey = header.dataset.entityColumn;
    header.classList.add("entity-column-dragging");
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", draggedKey);
  });
  table.addEventListener("dragover", event => {
    const header = event.target.closest?.("th[data-entity-column]");
    if (!header || !draggedKey || header.dataset.entityColumn === draggedKey) return;
    event.preventDefault();
    clearDropTargets();
    header.classList.add("entity-column-drop-target");
    event.dataTransfer.dropEffect = "move";
  });
  table.addEventListener("drop", event => {
    const header = event.target.closest?.("th[data-entity-column]");
    if (!header || !draggedKey || header.dataset.entityColumn === draggedKey) return;
    event.preventDefault();
    const nextOrder = layout.order.filter(key => key !== draggedKey);
    let targetIndex = nextOrder.indexOf(header.dataset.entityColumn);
    const bounds = header.getBoundingClientRect();
    if (event.clientX > bounds.left + bounds.width / 2) targetIndex += 1;
    nextOrder.splice(Math.max(0, targetIndex), 0, draggedKey);
    layout.order = nextOrder;
    saveLayout();
    applyLayout();
  });
  table.addEventListener("dragend", () => {
    table.querySelectorAll(".entity-column-dragging").forEach(item => item.classList.remove("entity-column-dragging"));
    clearDropTargets();
    draggedKey = "";
  });

  table.addEventListener("pointerdown", event => {
    const handle = event.target.closest?.(".entity-column-resizer");
    if (!handle) return;
    const header = handle.closest("th[data-entity-column]");
    if (!header) return;
    event.preventDefault();
    event.stopPropagation();
    resizing = {
      key: header.dataset.entityColumn,
      startX: event.clientX,
      startWidth: layout.widths[header.dataset.entityColumn] || header.getBoundingClientRect().width,
      pointerId: event.pointerId,
    };
    handle.setPointerCapture?.(event.pointerId);
  });
  window.addEventListener("pointermove", event => {
    if (!resizing || event.pointerId !== resizing.pointerId) return;
    const definition = definitions.get(resizing.key);
    layout.widths[resizing.key] = Math.max(
      definition?.min || 62,
      Math.min(700, Math.round(resizing.startWidth + event.clientX - resizing.startX)),
    );
    applyWidths();
  });
  window.addEventListener("pointerup", event => {
    if (!resizing || event.pointerId !== resizing.pointerId) return;
    resizing = null;
    saveLayout();
  });

  const toolbar = document.querySelector("#entities-panel .toolbar");
  if (toolbar && !document.getElementById("reset-entity-columns")) {
    const reset = document.createElement("button");
    reset.id = "reset-entity-columns";
    reset.type = "button";
    reset.textContent = "Reset columns";
    reset.addEventListener("click", () => {
      localStorage.removeItem(STORAGE_KEY);
      layout = loadLayout();
      applyLayout();
    });
    toolbar.appendChild(reset);
    const help = document.createElement("span");
    help.className = "entity-column-help";
    help.textContent = "Drag headers to move · drag header edges to resize";
    toolbar.appendChild(help);
  }

  applyLayout();
})();
