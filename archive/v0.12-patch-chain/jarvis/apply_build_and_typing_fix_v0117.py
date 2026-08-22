from pathlib import Path

ROOT = Path("/opt/jarvis")
PATCH_0116 = ROOT / "apply_catalog_backend_and_chat_ui_v0116.py"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"Jarvis v0.11.7 patch missing: {label}")


def main() -> None:
    text = PATCH_0116.read_text(encoding="utf-8")

    old_boundary = '''    function_start = main.find("async def _fetch_plugin_catalog(force=False):")
    function_end = main.find('\\n\\n@app.get("/api/plugin-catalog")', function_start)
    function_body = main[function_start:function_end]
    for line in function_body.splitlines():
        stripped = line.strip()
        if stripped.startswith("return ") and stripped.count(",") < 2:
            missing.append("inconsistent return: " + stripped)'''
    new_boundary = '''    function_start = main.find("async def _fetch_plugin_catalog(force=False):")
    function_end = main.find("\\n\\ndef _verify_catalog_result_contract", function_start)
    if function_end < 0:
        function_end = main.find('\\n\\n@app.get("/api/plugin-catalog")', function_start)
    function_body = main[function_start:function_end]
    for line in function_body.splitlines():
        stripped = line.strip()
        if stripped.startswith("return ") and stripped.count(",") < 2:
            missing.append("inconsistent return: " + stripped)'''
    require(text, old_boundary, "v0.11.6 verifier boundary")
    text = text.replace(old_boundary, new_boundary, 1)

    old_insert = '    text = text.replace("</script>", script + "\\n</script>", 1)'
    new_insert = '''    last_script = text.rfind("</script>")
    if last_script < 0:
        raise RuntimeError("Jarvis v0.11.7 patch missing: final script close")
    text = text[:last_script] + script + "\\n" + text[last_script:]'''
    require(text, old_insert, "typing listener insertion")
    text = text.replace(old_insert, new_insert, 1)

    text = text.replace('version="0.11.5"', 'version="0.11.7"')
    text = text.replace('"version": "0.11.5"', '"version": "0.11.7"')
    text = text.replace('HUD 0.11.5', 'HUD 0.11.7')
    text = text.replace('if "0.11.6" not in main:', 'if "0.11.7" not in main:')
    text = text.replace('missing.append("backend version 0.11.6")', 'missing.append("backend version 0.11.7")')

    PATCH_0116.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
