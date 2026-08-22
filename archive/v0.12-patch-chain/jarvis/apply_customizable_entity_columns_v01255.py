import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.55 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.55 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    frontend = replace_once(
        frontend,
        "  updateSelectionSummary(filtered.length);\n}",
        "  updateSelectionSummary(filtered.length);\n  window.zbranoApplyEntityColumnLayout?.();\n}",
        "entity render layout hook",
    )

    styles = r'''<style id="zbrano-v01255-entity-columns-style">
  #entities-panel .entity-column-help { margin-left: auto; font-size: .72rem; color: var(--text-muted); }
  #entities-panel table.entity-columns-customizable { table-layout: fixed; width: max-content; min-width: 0; }
  #entities-panel table.entity-columns-customizable th,
  #entities-panel table.entity-columns-customizable td { box-sizing: border-box; overflow-wrap: anywhere; }
  #entities-panel table.entity-columns-customizable th {
    position: sticky; cursor: grab; user-select: none; padding-right: 1rem;
  }
  #entities-panel table.entity-columns-customizable th:active { cursor: grabbing; }
  #entities-panel table.entity-columns-customizable th.entity-column-dragging { opacity: .55; }
  #entities-panel table.entity-columns-customizable th.entity-column-drop-target {
    box-shadow: inset 3px 0 0 var(--cyan);
  }
  #entities-panel .entity-column-resizer {
    position: absolute; top: 0; right: -4px; width: 9px; height: 100%; z-index: 3;
    cursor: col-resize; touch-action: none;
  }
  #entities-panel .entity-column-resizer::after {
    content: ""; position: absolute; top: 20%; bottom: 20%; left: 4px; width: 1px;
    background: color-mix(in srgb, var(--cyan) 45%, transparent);
  }
  #entities-panel table.entity-columns-customizable td input:not([type="checkbox"]),
  #entities-panel table.entity-columns-customizable td select { width: 100%; min-width: 0; box-sizing: border-box; }
  @media (max-width: 760px) {
    #entities-panel .entity-column-help { flex-basis: 100%; margin-left: 0; }
  }
</style>
'''
    head_close = frontend.find("</head>")
    if head_close < 0:
        raise RuntimeError("ZBRANO v0.12.55 could not locate head close")
    frontend = frontend[:head_close] + styles + frontend[head_close:]

    runtime = r'''<script id="zbrano-v01255-entity-columns">
(() => {
  const STORAGE_KEY = "zbrano_entity_column_layout_v1";
  const DEFAULTS = [
    {key:"select", label:"Select", width:76, min:62},
    {key:"name", label:"Friendly name", width:190, min:90},
    {key:"entity_id", label:"Entity ID", width:230, min:110},
    {key:"domain", label:"Domain", width:110, min:74},
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
</script>
'''
    body_close = frontend.rfind("</body>")
    if body_close < 0:
        raise RuntimeError("ZBRANO v0.12.55 could not locate body close")
    frontend = frontend[:body_close] + runtime + frontend[body_close:]

    backend = backend.replace('version="0.12.54"', 'version="0.12.55"')
    backend = backend.replace('"version": "0.12.54"', '"version": "0.12.55"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.54"', '"X-ZBRANO-Frontend-Version": "0.12.55"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.54"', '"name": "ZBRANO Developer Mode", "version": "0.12.55"')
    frontend = frontend.replace("HUD 0.12.54", "HUD 0.12.55")

    for marker in ('version="0.12.55"', 'service_domain = "telegram_bot" if channel["platform"] == "telegram" else "notify"'):
        require(backend, marker, marker)
    for marker in (
        "HUD 0.12.55",
        'id="zbrano-v01255-entity-columns"',
        'id="zbrano-v01255-entity-columns-style"',
        "zbrano_entity_column_layout_v1",
        "window.zbranoApplyEntityColumnLayout = applyLayout",
        'reset.id = "reset-entity-columns"',
        'event.target.closest?.(".entity-column-resizer")',
    ):
        require(frontend, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
