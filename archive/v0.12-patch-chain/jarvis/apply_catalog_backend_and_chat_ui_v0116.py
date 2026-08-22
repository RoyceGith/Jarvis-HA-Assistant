from pathlib import Path

ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"Jarvis v0.11.6 patch missing: {label}")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")

    old_cached = '''        if cached is not None:
            return cached, True'''
    new_cached = '''        if cached is not None:
            return cached, True, None'''
    require(text, old_cached, "fresh cache return")
    text = text.replace(old_cached, new_cached, 1)

    function_start = text.find("async def _fetch_plugin_catalog(force=False):")
    function_end = text.find('\n\n@app.get("/api/plugin-catalog")', function_start)
    if function_start < 0 or function_end < 0:
        raise RuntimeError("Jarvis v0.11.6 patch missing: catalog function bounds")

    function_body = text[function_start:function_end]
    invalid_returns = []
    for line in function_body.splitlines():
        stripped = line.strip()
        if stripped.startswith("return ") and stripped.count(",") < 2:
            invalid_returns.append(stripped)
    if invalid_returns:
        raise RuntimeError(
            "Jarvis v0.11.6 found inconsistent catalog returns: "
            + ", ".join(invalid_returns)
        )

    marker = '\n\n@app.get("/api/plugin-catalog")'
    contract_helper = '''


def _verify_catalog_result_contract(result):
    if not isinstance(result, tuple) or len(result) != 3:
        raise RuntimeError("Plugin catalog result must be a 3-item tuple")
    plugins, cached, registry_error = result
    if not isinstance(plugins, list):
        raise RuntimeError("Plugin catalog plugins must be a list")
    if not isinstance(cached, bool):
        raise RuntimeError("Plugin catalog cached flag must be boolean")
    if registry_error is not None and not isinstance(registry_error, str):
        raise RuntimeError("Plugin catalog registry error must be text or null")
    return result
'''
    require(text, marker, "catalog route marker")
    text = text.replace(marker, contract_helper + marker, 1)

    text = text.replace(
        '''    plugins, cached, registry_error = await _fetch_plugin_catalog(force=refresh)''',
        '''    plugins, cached, registry_error = _verify_catalog_result_contract(
        await _fetch_plugin_catalog(force=refresh)
    )''',
        1,
    )
    text = text.replace(
        '''    plugins, _, _ = await _fetch_plugin_catalog(force=False)''',
        '''    plugins, _, _ = _verify_catalog_result_contract(
        await _fetch_plugin_catalog(force=False)
    )''',
        1,
    )

    text = text.replace('version="0.11.5"', 'version="0.11.6"')
    text = text.replace('"version": "0.11.5"', '"version": "0.11.6"')
    MAIN.write_text(text, encoding="utf-8")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    require(text, "</style>", "style close")
    css = r'''
    /* v0.11.6 response readability */
    .message.jarvis > * + h2,
    .message.jarvis > * + h3,
    .message.jarvis > * + h4 {
      margin-top: 1.65rem !important;
    }
    .message.jarvis h2,
    .message.jarvis h3,
    .message.jarvis h4 {
      margin-bottom: .7rem;
      line-height: 1.3;
    }
    .message.jarvis p,
    .message.jarvis ul,
    .message.jarvis ol,
    .message.jarvis pre,
    .message.jarvis blockquote {
      margin-bottom: .9rem;
    }
    .message.jarvis pre,
    .message.jarvis blockquote {
      margin-top: .75rem;
    }

    /* Keep the neural background barely visible while composing a command. */
    body.jarvis-input-active #brain-network {
      opacity: .035 !important;
      transition: opacity .16s ease;
    }
'''
    text = text.replace("</style>", css + "\n</style>", 1)

    require(text, "</script>", "script close")
    script = r'''
(() => {
  const commandInput = document.getElementById("message");
  if (!commandInput) return;

  const syncNeuralOpacity = () => {
    document.body.classList.toggle(
      "jarvis-input-active",
      commandInput.value.length > 0
    );
  };

  commandInput.addEventListener("input", syncNeuralOpacity);
  commandInput.addEventListener("change", syncNeuralOpacity);
  syncNeuralOpacity();
})();
'''
    text = text.replace("</script>", script + "\n</script>", 1)

    old_papi = '''async function pApi(path,options={}){const r=await fetch(path,options),d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||`HTTP ${r.status}`);return d}'''
    if old_papi in text:
        new_papi = '''async function pApi(path,options={}){const r=await fetch(path,options),d=await r.json().catch(()=>({}));if(!r.ok){const detail=typeof d.detail==="string"?d.detail:(d.detail?JSON.stringify(d.detail):"");throw new Error(detail||`HTTP ${r.status}`)}return d}'''
        text = text.replace(old_papi, new_papi, 1)

    text = text.replace("HUD 0.11.5", "HUD 0.11.6")
    INDEX.write_text(text, encoding="utf-8")


def verify() -> None:
    main = MAIN.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")

    missing = []
    for marker in (
        "return cached, True, None",
        "def _verify_catalog_result_contract(result):",
        "body.jarvis-input-active #brain-network",
        "opacity: .035 !important",
        "commandInput.addEventListener(\"input\", syncNeuralOpacity)",
        ".message.jarvis > * + h3",
        "margin-top: 1.65rem !important",
    ):
        if marker not in main and marker not in index:
            missing.append(marker)

    function_start = main.find("async def _fetch_plugin_catalog(force=False):")
    function_end = main.find('\n\n@app.get("/api/plugin-catalog")', function_start)
    function_body = main[function_start:function_end]
    for line in function_body.splitlines():
        stripped = line.strip()
        if stripped.startswith("return ") and stripped.count(",") < 2:
            missing.append("inconsistent return: " + stripped)

    if "0.11.6" not in main:
        missing.append("backend version 0.11.6")

    if missing:
        raise RuntimeError(
            "Jarvis v0.11.6 verification failed: " + ", ".join(missing)
        )


if __name__ == "__main__":
    patch_main()
    patch_index()
    verify()
