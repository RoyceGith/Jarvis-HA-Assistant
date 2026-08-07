from pathlib import Path

ROOT = Path("/opt/jarvis")
INDEX = ROOT / "app/static/index.html"
MAIN = ROOT / "app/main.py"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.11.26 patch missing: {label}")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    runtime_start_marker = 'var pluginsTab=document.getElementById("plugins-tab"),pluginsPanel=document.getElementById("plugins-panel"),pluginList='
    runtime_end_marker = 'pluginsTab.addEventListener("click",async()=>{showPanel("plugins");await loadPlugins()});'

    require(text, runtime_start_marker, "plugin runtime start")
    require(text, runtime_end_marker, "plugin runtime end")

    runtime_start = text.find(runtime_start_marker)
    runtime_end = text.find(runtime_end_marker, runtime_start)
    if runtime_end < 0:
        raise RuntimeError("ZBRANO v0.11.26 patch missing: plugin runtime bounds")
    runtime_end += len(runtime_end_marker)

    first_script_close = text.find("</script>")
    head_close = text.find("</head>")
    if first_script_close < 0 or head_close < 0:
        raise RuntimeError("ZBRANO v0.11.26 patch missing: document head structure")
    if not (runtime_start < first_script_close < head_close):
        raise RuntimeError(
            "ZBRANO v0.11.26 expected plugin runtime in the early head script"
        )

    runtime = text[runtime_start:runtime_end].strip()
    text = text[:runtime_start] + text[runtime_end:]

    body_close = text.rfind("</body>")
    if body_close < 0:
        raise RuntimeError("ZBRANO v0.11.26 patch missing: body close")

    relocated = (
        '\n<script id="zbrano-v01126-plugin-runtime">\n'
        + runtime
        + '\n</script>\n'
    )
    text = text[:body_close] + relocated + text[body_close:]

    text = text.replace("HUD 0.11.25", "HUD 0.11.26")
    INDEX.write_text(text, encoding="utf-8")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    text = text.replace('version="0.11.25"', 'version="0.11.26"')
    text = text.replace('"version": "0.11.25"', '"version": "0.11.26"')
    MAIN.write_text(text, encoding="utf-8")


def verify() -> None:
    index = INDEX.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")
    missing = []

    marker = '<script id="zbrano-v01126-plugin-runtime">'
    if marker not in index:
        missing.append("relocated plugin runtime script")

    runtime_pos = index.find(marker)
    body_pos = index.find("<body")
    head_close = index.find("</head>")
    if runtime_pos < 0 or body_pos < 0 or runtime_pos < body_pos or runtime_pos < head_close:
        missing.append("plugin runtime must execute after body DOM exists")

    first_script_close = index.find("</script>")
    early_script = index[:first_script_close] if first_script_close >= 0 else index
    if 'pluginsTab=document.getElementById("plugins-tab")' in early_script:
        missing.append("stale plugin DOM lookup in early head script")
    if '(document.getElementById("plugins-panel")||document.body).appendChild' in early_script:
        missing.append("unsafe document.body fallback in early head script")

    required_runtime = (
        'var pluginsTab=document.getElementById("plugins-tab")',
        'pluginsPanel=document.getElementById("plugins-panel")',
        'function ensurePluginDomReady()',
        'function currentPluginList()',
        'pluginsTab.addEventListener("click"',
    )
    relocated_runtime = index[runtime_pos:index.find("</script>", runtime_pos)] if runtime_pos >= 0 else ""
    for value in required_runtime:
        if value not in relocated_runtime:
            missing.append(value)

    if "0.11.26" not in main:
        missing.append("backend version 0.11.26")

    if missing:
        raise RuntimeError(
            "ZBRANO v0.11.26 verification failed: " + ", ".join(missing)
        )


if __name__ == "__main__":
    patch_index()
    patch_main()
    verify()
