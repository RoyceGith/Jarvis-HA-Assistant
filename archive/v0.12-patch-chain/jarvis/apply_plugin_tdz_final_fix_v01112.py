from pathlib import Path

ROOT = Path("/opt/jarvis")
INDEX = ROOT / "app/static/index.html"
MAIN = ROOT / "app/main.py"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"Jarvis v0.11.12 patch missing: {label}")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    # The plugin manager is injected into an earlier script than the main app.
    # Recovery handlers may call loadPlugins() before this declaration executes.
    # `const` therefore creates a TDZ for pluginList/pluginsPanel/pluginsTab.
    binding_prefix = (
        'const pluginsTab=document.getElementById("plugins-tab"),'
        'pluginsPanel=document.getElementById("plugins-panel"),'
        'pluginList='
    )
    require(text, binding_prefix, "plugin manager lexical bindings")
    text = text.replace(
        binding_prefix,
        (
            'var pluginsTab=document.getElementById("plugins-tab"),'
            'pluginsPanel=document.getElementById("plugins-panel"),'
            'pluginList='
        ),
        1,
    )

    # Make loadPlugins resolve the live node every time and never rely on the
    # top-level pluginList binding, including its catch/error path.
    loader_start = '''async function loadPlugins(){
  ensurePluginDomReady();'''
    require(text, loader_start, "guarded plugin loader")
    loader_replacement = '''function currentPluginList(){
  ensurePluginDomReady();
  return document.getElementById("plugin-list");
}

async function loadPlugins(){
  const listNode=currentPluginList();'''
    text = text.replace(loader_start, loader_replacement, 1)

    old_render = '(document.getElementById("plugin-list")||pluginList).innerHTML='
    if old_render in text:
        text = text.replace(old_render, 'listNode.innerHTML=', 1)

    # Replace the remaining loadPlugins-local accesses. Limit the operation to
    # the loader body so event handlers can keep using the initialized global.
    loader_pos = text.find("async function loadPlugins(){")
    install_pos = text.find('installPlugin.addEventListener("click"', loader_pos)
    if loader_pos < 0 or install_pos < 0:
        raise RuntimeError("Jarvis v0.11.12 patch missing: plugin loader bounds")
    loader = text[loader_pos:install_pos]
    loader = loader.replace("pluginList.innerHTML", "listNode.innerHTML")
    loader = loader.replace("pluginList.appendChild", "listNode.appendChild")
    loader = loader.replace("pluginList.textContent", "listNode.textContent")
    text = text[:loader_pos] + loader + text[install_pos:]

    # The list-level click/change listeners should bind to a live DOM node
    # after the static page exists instead of assuming pluginList initialized.
    text = text.replace(
        'pluginList.addEventListener("click",async e=>',
        'currentPluginList().addEventListener("click",async e=>',
        1,
    )
    text = text.replace(
        'pluginList.addEventListener("change",async e=>',
        'currentPluginList().addEventListener("change",async e=>',
        1,
    )

    text = text.replace("HUD 0.11.11", "HUD 0.11.12")
    INDEX.write_text(text, encoding="utf-8")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    text = text.replace('version="0.11.11"', 'version="0.11.12"')
    text = text.replace('"version": "0.11.11"', '"version": "0.11.12"')
    MAIN.write_text(text, encoding="utf-8")


def verify() -> None:
    index = INDEX.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")
    missing = []

    required = (
        'var pluginsTab=document.getElementById("plugins-tab")',
        "function currentPluginList()",
        "const listNode=currentPluginList();",
        'currentPluginList().addEventListener("click"',
        'currentPluginList().addEventListener("change"',
    )
    for marker in required:
        if marker not in index:
            missing.append(marker)

    if 'const pluginsTab=document.getElementById("plugins-tab")' in index:
        missing.append("stale const plugin manager bindings")

    loader_pos = index.find("async function loadPlugins(){")
    install_pos = index.find('installPlugin.addEventListener("click"', loader_pos)
    loader = index[loader_pos:install_pos]
    if "pluginList." in loader or "||pluginList" in loader:
        missing.append("loadPlugins still depends on pluginList binding")

    if "0.11.12" not in main:
        missing.append("backend version 0.11.12")

    if missing:
        raise RuntimeError(
            "Jarvis v0.11.12 verification failed: " + ", ".join(missing)
        )


if __name__ == "__main__":
    patch_index()
    patch_main()
    verify()
