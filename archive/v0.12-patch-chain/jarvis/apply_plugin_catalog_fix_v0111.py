from pathlib import Path

ROOT = Path("/opt/jarvis")
INDEX = ROOT / "app/static/index.html"
MAIN = ROOT / "app/main.py"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"Jarvis v0.11.1 patch missing: {label}")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    old_recovery = '''  async function recoverPlugins() {
    activatePanel("plugins");
    const state = byId("plugin-state");
    try {
      if (typeof loadPlugins !== "function") {
        throw new Error("Plugin loader is unavailable");
      }
      await loadPlugins();
    } catch (error) {
      if (state) state.textContent = `Could not load plugins: ${error.message || error}`;
    }
  }'''
    new_recovery = '''  async function recoverPlugins() {
    activatePanel("plugins");
    const state = byId("plugin-state");
    const catalogState = byId("catalog-status");
    try {
      const tasks = [];
      if (typeof loadPlugins === "function") tasks.push(loadPlugins());
      else throw new Error("Plugin loader is unavailable");
      if (typeof loadCatalog === "function") tasks.push(loadCatalog(false));
      await Promise.all(tasks);
    } catch (error) {
      const message = `Could not load plugins: ${error.message || error}`;
      if (state) state.textContent = message;
      if (catalogState) catalogState.textContent = message;
    }
  }'''
    require(text, old_recovery, "plugin recovery handler")
    text = text.replace(old_recovery, new_recovery, 1)

    old_click = '''  tabs.plugins?.addEventListener("click", event => {
    event.preventDefault();
    event.stopImmediatePropagation();
    recoverPlugins();
  }, true);'''
    new_click = '''  tabs.plugins?.addEventListener("click", event => {
    event.preventDefault();
    event.stopImmediatePropagation();
    recoverPlugins();
  }, true);'''
    require(text, old_click, "plugin capture handler")
    text = text.replace(old_click, new_click, 1)

    marker = 'window.jarvisActivatePanel = activatePanel;'
    require(text, marker, "recovery export")
    text = text.replace(
        marker,
        '''window.jarvisActivatePanel = activatePanel;
  if (tabs.plugins?.classList.contains("active")) recoverPlugins();''',
        1,
    )

    text = text.replace("HUD 0.11.0", "HUD 0.11.1")
    INDEX.write_text(text, encoding="utf-8")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")

    if not text.startswith("import hashlib\n") and "\nimport hashlib\n" not in text.split("class ", 1)[0]:
        if "import ipaddress\n" in text:
            text = text.replace("import ipaddress\n", "import hashlib\nimport ipaddress\n", 1)
        else:
            text = "import hashlib\n" + text

    old_except = '''    except Exception:
        cached = _catalog_cache_read()
        if cached is not None:
            return cached, True
    _plugin_save(PLUGIN_CATALOG_CACHE_PATH, {"saved_at": time.time(), "plugins": plugins})
    return plugins, False'''
    new_except = '''    except Exception as exc:
        cached = _catalog_cache_read()
        if cached is not None:
            return cached, True, str(exc)
        _plugin_save(PLUGIN_CATALOG_CACHE_PATH, {"saved_at": time.time(), "plugins": plugins})
        return plugins, False, str(exc)
    _plugin_save(PLUGIN_CATALOG_CACHE_PATH, {"saved_at": time.time(), "plugins": plugins})
    return plugins, False, None'''
    require(text, old_except, "catalog fetch error handling")
    text = text.replace(old_except, new_except, 1)

    text = text.replace(
        '''    plugins, cached = await _fetch_plugin_catalog(force=refresh)''',
        '''    plugins, cached, registry_error = await _fetch_plugin_catalog(force=refresh)''',
        1,
    )
    text = text.replace(
        '''    return {"plugins": result[:100], "cached": cached}''',
        '''    return {"plugins": result[:100], "cached": cached, "registry_error": registry_error}''',
        1,
    )
    text = text.replace(
        '''    plugins, _ = await _fetch_plugin_catalog(force=False)''',
        '''    plugins, _, _ = await _fetch_plugin_catalog(force=False)''',
        1,
    )

    text = text.replace('version="0.11.0"', 'version="0.11.1"')
    text = text.replace('"version": "0.11.0"', '"version": "0.11.1"')
    MAIN.write_text(text, encoding="utf-8")


def verify() -> None:
    index = INDEX.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")
    required_index = (
        'typeof loadCatalog === "function"',
        'Promise.all(tasks)',
        'id="catalog-status"',
    )
    required_main = (
        "import hashlib",
        '"registry_error": registry_error',
        "plugins, _, _ = await _fetch_plugin_catalog",
    )
    missing = [item for item in required_index if item not in index]
    missing += [item for item in required_main if item not in main]
    if missing:
        raise RuntimeError("Jarvis v0.11.1 verification failed: " + ", ".join(missing))


if __name__ == "__main__":
    patch_index()
    patch_main()
    verify()
