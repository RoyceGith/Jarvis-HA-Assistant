from pathlib import Path

ROOT = Path("/opt/jarvis")
INDEX = ROOT / "app/static/index.html"
MAIN = ROOT / "app/main.py"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"Jarvis v0.11.3 patch missing: {label}")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    old_plugin_fallback = '  (pluginsPanel||document.body).appendChild(fallback);'
    new_plugin_fallback = '  (document.getElementById("plugins-panel")||document.body).appendChild(fallback);'
    require(text, old_plugin_fallback, "plugin-list fallback parent")
    text = text.replace(old_plugin_fallback, new_plugin_fallback, 1)

    old_catalog_parent = '  (pluginsPanel||document.body).appendChild(node);'
    new_catalog_parent = '  (document.getElementById("plugins-panel")||document.body).appendChild(node);'
    if text.count(old_catalog_parent) < 2:
        raise RuntimeError("Jarvis v0.11.3 patch missing: catalog fallback parents")
    text = text.replace(old_catalog_parent, new_catalog_parent, 2)

    guard_marker = 'async function loadPlugins(){'
    require(text, guard_marker, "loadPlugins")
    guarded_loader = '''function ensurePluginDomReady(){
  const panel=document.getElementById("plugins-panel")||document.body;
  if(!document.getElementById("plugin-list")){
    const node=document.createElement("div");
    node.id="plugin-list";
    node.className="muted";
    node.textContent="No plugins loaded.";
    panel.appendChild(node);
  }
  if(!document.getElementById("catalog-status")){
    const node=document.createElement("div");
    node.id="catalog-status";
    node.setAttribute("role","status");
    panel.appendChild(node);
  }
  if(!document.getElementById("catalog-results")){
    const node=document.createElement("div");
    node.id="catalog-results";
    node.className="catalog-grid";
    panel.appendChild(node);
  }
}

async function loadPlugins(){
  ensurePluginDomReady();'''
    text = text.replace(guard_marker, guarded_loader, 1)

    old_inner = 'pluginList.innerHTML='
    require(text, old_inner, "plugin list rendering")
    text = text.replace(
        old_inner,
        '(document.getElementById("plugin-list")||pluginList).innerHTML=',
        1,
    )

    text = text.replace("HUD 0.11.2", "HUD 0.11.3")
    INDEX.write_text(text, encoding="utf-8")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    text = text.replace('version="0.11.2"', 'version="0.11.3"')
    text = text.replace('"version": "0.11.2"', '"version": "0.11.3"')
    MAIN.write_text(text, encoding="utf-8")


def verify() -> None:
    index = INDEX.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")

    missing = []
    required_index = (
        'document.getElementById("plugins-panel")||document.body',
        'function ensurePluginDomReady()',
        'ensurePluginDomReady();',
        '(document.getElementById("plugin-list")||pluginList).innerHTML=',
    )
    for marker in required_index:
        if marker not in index:
            missing.append(marker)

    if '(pluginsPanel||document.body).appendChild' in index:
        missing.append("stale pluginsPanel TDZ reference")
    if "0.11.3" not in main:
        missing.append("backend version 0.11.3")

    if missing:
        raise RuntimeError(
            "Jarvis v0.11.3 verification failed: " + ", ".join(missing)
        )


if __name__ == "__main__":
    patch_index()
    patch_main()
    verify()
