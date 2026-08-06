from pathlib import Path

ROOT = Path("/opt/jarvis")
INDEX = ROOT / "app/static/index.html"
MAIN = ROOT / "app/main.py"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"Jarvis v0.11.2 patch missing: {label}")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    panel_start = text.find('<section id="plugins-panel"')
    if panel_start < 0:
        raise RuntimeError("Jarvis v0.11.2 patch missing: plugins panel")
    panel_end = text.find("</section>", panel_start)
    if panel_end < 0:
        raise RuntimeError("Jarvis v0.11.2 patch missing: plugins panel close")

    plugin_panel_html = text[panel_start:panel_end]
    if 'id="plugin-list"' not in plugin_panel_html:
        installed_card = '''
    <div class="plugin-card" style="grid-column:1/-1">
      <h2>INSTALLED PLUGINS</h2>
      <p>Only reviewed read-only tools can be enabled.</p>
      <div id="plugin-list" class="muted">No plugins loaded.</div>
    </div>
'''
        text = text[:panel_end] + installed_card + text[panel_end:]

    old_binding = 'pluginList=document.getElementById("plugin-list")'
    require(text, old_binding, "plugin list binding")
    new_binding = '''pluginList=document.getElementById("plugin-list")||(() => {
  const fallback=document.createElement("div");
  fallback.id="plugin-list";
  fallback.className="muted";
  fallback.textContent="No plugins loaded.";
  (pluginsPanel||document.body).appendChild(fallback);
  return fallback;
})()'''
    text = text.replace(old_binding, new_binding, 1)

    replacements = {
        'const catalogStatus=document.getElementById("catalog-status");':
            '''const catalogStatus=document.getElementById("catalog-status")||(() => {
  const node=document.createElement("div");
  node.id="catalog-status";
  node.setAttribute("role","status");
  (pluginsPanel||document.body).appendChild(node);
  return node;
})();''',
        'const catalogResults=document.getElementById("catalog-results");':
            '''const catalogResults=document.getElementById("catalog-results")||(() => {
  const node=document.createElement("div");
  node.id="catalog-results";
  node.className="catalog-grid";
  (pluginsPanel||document.body).appendChild(node);
  return node;
})();''',
    }
    for old, new in replacements.items():
        require(text, old, old)
        text = text.replace(old, new, 1)

    text = text.replace("HUD 0.11.1", "HUD 0.11.2")
    INDEX.write_text(text, encoding="utf-8")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    text = text.replace('version="0.11.1"', 'version="0.11.2"')
    text = text.replace('"version": "0.11.1"', '"version": "0.11.2"')
    MAIN.write_text(text, encoding="utf-8")


def verify() -> None:
    index = INDEX.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")

    panel_start = index.find('<section id="plugins-panel"')
    panel_end = index.find("</section>", panel_start)
    panel_html = index[panel_start:panel_end]

    missing = []
    if 'id="plugin-list"' not in panel_html:
        missing.append("static plugin-list")
    for marker in (
        'fallback.id="plugin-list"',
        'node.id="catalog-status"',
        'node.id="catalog-results"',
    ):
        if marker not in index:
            missing.append(marker)
    if "0.11.2" not in main:
        missing.append("backend version 0.11.2")

    if missing:
        raise RuntimeError(
            "Jarvis v0.11.2 verification failed: " + ", ".join(missing)
        )


if __name__ == "__main__":
    patch_index()
    patch_main()
    verify()
