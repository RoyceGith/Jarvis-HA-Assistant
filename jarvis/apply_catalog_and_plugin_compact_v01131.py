from pathlib import Path

ROOT = Path("/opt/jarvis")
INDEX = ROOT / "app/static/index.html"
MAIN = ROOT / "app/main.py"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.11.31 patch missing: {label}")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")

    fetch_marker = "async def _fetch_plugin_catalog(force=False):\n"
    require(text, fetch_marker, "catalog fetch function")
    helper = '''def _catalog_with_featured(items):
    merged = [dict(item) for item in FEATURED_REMOTE_PLUGINS]
    seen = {str(item.get("url") or item.get("id") or "") for item in merged}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        key = str(item.get("url") or item.get("id") or "")
        if key and key in seen:
            continue
        merged.append(item)
        if key:
            seen.add(key)
    return merged


'''
    text = text.replace(fetch_marker, helper + fetch_marker, 1)

    cache_return = '''        cached = _catalog_cache_read()
        if cached is not None:
            return cached, True, None'''
    require(text, cache_return, "catalog cache return")
    text = text.replace(
        cache_return,
        '''        cached = _catalog_cache_read()
        if cached is not None:
            return _catalog_with_featured(cached), True, None''',
        1,
    )

    # Also protect the registry-error fallback from a previously persisted
    # empty cache. Featured entries must always remain visible.
    error_return = '''        cached = _catalog_cache_read()
        if cached is not None:
            return cached, True, registry_error'''
    if error_return in text:
        text = text.replace(
            error_return,
            '''        cached = _catalog_cache_read()
        if cached is not None:
            return _catalog_with_featured(cached), True, registry_error''',
            1,
        )

    text = text.replace('version="0.11.30"', 'version="0.11.31"')
    text = text.replace('"version": "0.11.30"', '"version": "0.11.31"')
    MAIN.write_text(text, encoding="utf-8")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")
    require(text, 'id="plugin-list"', "installed plugin list")
    require(text, 'async function loadPlugins()', "plugin loader")

    css = r'''
    .plugin-row.compact-plugin .plugin-settings{display:none;margin-top:.65rem;border-top:1px solid var(--line);padding-top:.35rem}
    .plugin-row.compact-plugin.open .plugin-settings{display:block}
    .plugin-row.compact-plugin .plugin-head{align-items:center}
    .plugin-row.compact-plugin .plugin-meta{max-width:72ch}
    .plugin-settings-toggle[aria-expanded="true"]{border-color:var(--cyan);color:var(--cyan)}
'''
    style_close = text.find("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.11.31 patch missing: style close")
    text = text[:style_close] + css + "\n" + text[style_close:]

    runtime = r'''
<script id="zbrano-v01131-plugin-compact">
(() => {
  if (typeof loadPlugins !== "function") return;
  const pluginListNode = document.getElementById("plugin-list");
  if (!pluginListNode) return;

  function compactPluginRows() {
    for (const row of pluginListNode.querySelectorAll(".plugin-row")) {
      if (row.classList.contains("compact-plugin")) continue;
      const head = row.querySelector(".plugin-head");
      if (!head) continue;

      let settings = row.querySelector(":scope > .plugin-settings");
      if (!settings) {
        settings = document.createElement("div");
        settings.className = "plugin-settings";
        const movable = [...row.children].filter(child => child !== head);
        for (const child of movable) settings.appendChild(child);
        row.appendChild(settings);
      }
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
</script>
'''
    body_close = text.rfind("</body>")
    if body_close < 0:
        raise RuntimeError("ZBRANO v0.11.31 patch missing: body close")
    text = text[:body_close] + runtime + text[body_close:]

    text = text.replace("HUD 0.11.30", "HUD 0.11.31")
    INDEX.write_text(text, encoding="utf-8")


def verify() -> None:
    main = MAIN.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    missing = []
    for marker in (
        "def _catalog_with_featured(items):",
        "return _catalog_with_featured(cached), True, None",
        'version="0.11.31"',
    ):
        if marker not in main:
            missing.append(marker)
    for marker in (
        'zbrano-v01131-plugin-compact',
        'plugin-settings-toggle',
        'compactPluginRows()',
        'loadPlugins = async function',
        'HUD 0.11.31',
    ):
        if marker not in index:
            missing.append(marker)
    if missing:
        raise RuntimeError("ZBRANO v0.11.31 verification failed: " + ", ".join(missing))


if __name__ == "__main__":
    patch_main()
    patch_index()
    verify()
