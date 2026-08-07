from pathlib import Path

ROOT = Path("/opt/jarvis")
INDEX = ROOT / "app/static/index.html"
MAIN = ROOT / "app/main.py"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.11.28 patch missing: {label}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    require(text, old, label)
    return text.replace(old, new, 1)


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    # v0.10.2 installed a capture-phase recovery router before Shared Files
    # existed. It stops the modern Plugins listener and therefore leaves the
    # Shared Files panel visible. Remove the obsolete router completely.
    recovery_start_marker = '<script id="jarvis-v0102-tab-recovery">'
    require(text, recovery_start_marker, "legacy tab recovery script")
    recovery_start = text.find(recovery_start_marker)
    recovery_end = text.find("</script>", recovery_start)
    if recovery_end < 0:
        raise RuntimeError("ZBRANO v0.11.28 patch missing: legacy recovery close")
    recovery_end += len("</script>")
    text = text[:recovery_start] + text[recovery_end:]

    # The document itself is intentionally overflow:hidden. Give Plugins its
    # own scroll container so the installed-plugin controls remain reachable.
    style_marker = "</style>"
    require(text, style_marker, "style close")
    plugin_scroll_css = r'''
    #plugins-panel {
      overflow-y: auto;
      overflow-x: hidden;
      overscroll-behavior: contain;
      scrollbar-gutter: stable;
      scrollbar-color: var(--cyan-dim) transparent;
    }
    #plugins-panel .plugin-layout { min-height: min-content; padding-bottom: 1rem; }
'''
    text = text.replace(style_marker, plugin_scroll_css + "\n" + style_marker, 1)

    # Make the installed-plugin state describe whether chat can actually use
    # the plugin rather than only whether credentials were installed.
    old_meta = '${p.enabled?"Enabled":"Disabled"} · ${p.healthy?"Healthy":"Unhealthy"} · token ${p.has_secret?"stored":"not set"}'
    new_meta = '${p.enabled?"Enabled":"Installed · disabled"} · ${p.available_to_chat?"Available to chat":"Not available to chat"} · ${p.enabled_tool_count||0} tool${(p.enabled_tool_count||0)===1?"":"s"} enabled · ${p.healthy?"Healthy":"Unhealthy"} · token ${p.has_secret?"stored":"not set"}'
    text = replace_once(text, old_meta, new_meta, "installed plugin status text")

    # The modern listener must own Plugins navigation and load both sources.
    modern_listener = 'pluginsTab.addEventListener("click",async()=>{showPanel("plugins");await Promise.all([loadPlugins(),loadCatalog(false)])});'
    require(text, modern_listener, "modern Plugins listener")

    text = text.replace("HUD 0.11.27", "HUD 0.11.28")
    INDEX.write_text(text, encoding="utf-8")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")

    old_public = 'def plugin_public(pid,p):\n    return {"id":pid,"name":p.get("name",pid),"url":p.get("url",""),"enabled":bool(p.get("enabled")),"healthy":bool(p.get("healthy")),"last_error":p.get("last_error"),"last_checked":p.get("last_checked"),"has_secret":bool(plugin_secrets().get(pid)),"tools":list(p.get("tools") or [])}'
    new_public = '''def plugin_public(pid,p):
    tools = list(p.get("tools") or [])
    enabled_tool_count = sum(
        1
        for tool in tools
        if tool.get("enabled") and tool.get("permission") == "read_only"
    )
    return {
        "id": pid,
        "name": p.get("name", pid),
        "url": p.get("url", ""),
        "enabled": bool(p.get("enabled")),
        "healthy": bool(p.get("healthy")),
        "last_error": p.get("last_error"),
        "last_checked": p.get("last_checked"),
        "has_secret": bool(plugin_secrets().get(pid)),
        "tools": tools,
        "enabled_tool_count": enabled_tool_count,
        "available_to_chat": bool(p.get("enabled") and enabled_tool_count),
    }'''
    text = replace_once(text, old_public, new_public, "plugin public state")

    # A valid cache should be shown immediately, even when it contains only
    # the featured plugin. The old guard unnecessarily forced another crawl.
    old_cache_guard = '''    if not force:
        cached = _catalog_cache_read()
        if cached is not None and len(cached) > len(FEATURED_REMOTE_PLUGINS):
            return cached, True, None'''
    new_cache_guard = '''    if not force:
        cached = _catalog_cache_read()
        if cached is not None:
            return cached, True, None'''
    text = replace_once(text, old_cache_guard, new_cache_guard, "catalog cache guard")

    # Keep Registry discovery useful without allowing an unhealthy remote
    # registry to block the Plugins UI for dozens of requests.
    text = replace_once(text, "            while pages < 20:", "            while pages < 3:", "catalog page budget")

    fetch_start = text.find("async def _fetch_plugin_catalog(force=False):")
    fetch_end = text.find("\n\n", fetch_start + len("async def _fetch_plugin_catalog(force=False):"))
    if fetch_start < 0:
        raise RuntimeError("ZBRANO v0.11.28 patch missing: catalog fetch function")
    endpoint_marker = '\n\n@app.get("/api/plugin-catalog")'
    endpoint_pos = text.find(endpoint_marker, fetch_start)
    if endpoint_pos < 0:
        endpoint_pos = text.find('\n\n\ndef _verify_catalog_result_contract', fetch_start)
    if endpoint_pos < 0:
        raise RuntimeError("ZBRANO v0.11.28 patch missing: catalog fetch bounds")
    fetcher = text[fetch_start:endpoint_pos]
    require(fetcher, "timeout=PLUGIN_TIMEOUT", "catalog HTTP timeout")
    fetcher = fetcher.replace(
        "timeout=PLUGIN_TIMEOUT",
        "timeout=httpx.Timeout(4.0, connect=2.0)",
        1,
    )
    text = text[:fetch_start] + fetcher + text[endpoint_pos:]

    text = text.replace('version="0.11.27"', 'version="0.11.28"')
    text = text.replace('"version": "0.11.27"', '"version": "0.11.28"')
    MAIN.write_text(text, encoding="utf-8")


def verify() -> None:
    index = INDEX.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")
    missing = []

    if 'id="jarvis-v0102-tab-recovery"' in index:
        missing.append("legacy capture-phase tab recovery still present")
    for marker in (
        "#plugins-panel {",
        "overflow-y: auto;",
        'Available to chat',
        'Not available to chat',
        'enabled_tool_count',
        'pluginsTab.addEventListener("click",async()=>{showPanel("plugins");await Promise.all([loadPlugins(),loadCatalog(false)])});',
    ):
        if marker not in index:
            missing.append(marker)

    for marker in (
        '"available_to_chat": bool(p.get("enabled") and enabled_tool_count)',
        '"enabled_tool_count": enabled_tool_count',
        "if cached is not None:",
        "while pages < 3:",
        "timeout=httpx.Timeout(4.0, connect=2.0)",
        'version="0.11.28"',
    ):
        if marker not in main:
            missing.append(marker)

    if "while pages < 20:" in main:
        missing.append("old 20-page catalog crawl")

    if missing:
        raise RuntimeError(
            "ZBRANO v0.11.28 verification failed: " + ", ".join(missing)
        )


if __name__ == "__main__":
    patch_index()
    patch_main()
    verify()
