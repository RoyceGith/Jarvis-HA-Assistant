from pathlib import Path

ROOT = Path("/opt/jarvis")
PATCH_0116 = ROOT / "apply_catalog_backend_and_chat_ui_v0116.py"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"Jarvis v0.11.8 patch missing: {label}")


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
    if old_boundary in text:
        text = text.replace(old_boundary, new_boundary, 1)
    require(text, new_boundary, "catalog verifier boundary")

    old_insert = '    text = text.replace("</script>", script + "\\n</script>", 1)'
    new_insert = '''    last_script = text.rfind("</script>")
    if last_script < 0:
        raise RuntimeError("Jarvis v0.11.8 patch missing: final script close")
    text = text[:last_script] + script + "\\n" + text[last_script:]'''
    if old_insert in text:
        text = text.replace(old_insert, new_insert, 1)
    require(text, new_insert, "final body script insertion")

    candidates = [
        (
            '''    text = text.replace('version="0.11.5"', 'version="0.11.6"')''',
            '''    text = text.replace('version="0.11.5"', 'version="0.11.8"')'''
        ),
        (
            '''    text = text.replace('version="0.11.7"', 'version="0.11.6"')''',
            '''    text = text.replace('version="0.11.5"', 'version="0.11.8"')'''
        ),
    ]
    for old, new in candidates:
        if old in text:
            text = text.replace(old, new, 1)
            break
    else:
        raise RuntimeError("Jarvis v0.11.8 patch missing: backend version statement")

    candidates = [
        (
            '''    text = text.replace('"version": "0.11.5"', '"version": "0.11.6"')''',
            '''    text = text.replace('"version": "0.11.5"', '"version": "0.11.8"')'''
        ),
        (
            '''    text = text.replace('"version": "0.11.7"', '"version": "0.11.6"')''',
            '''    text = text.replace('"version": "0.11.5"', '"version": "0.11.8"')'''
        ),
    ]
    for old, new in candidates:
        if old in text:
            text = text.replace(old, new, 1)
            break
    else:
        raise RuntimeError("Jarvis v0.11.8 patch missing: JSON version statement")

    candidates = [
        (
            '''    text = text.replace("HUD 0.11.5", "HUD 0.11.6")''',
            '''    text = text.replace("HUD 0.11.5", "HUD 0.11.8")'''
        ),
        (
            '''    text = text.replace("HUD 0.11.7", "HUD 0.11.6")''',
            '''    text = text.replace("HUD 0.11.5", "HUD 0.11.8")'''
        ),
    ]
    for old, new in candidates:
        if old in text:
            text = text.replace(old, new, 1)
            break
    else:
        raise RuntimeError("Jarvis v0.11.8 patch missing: HUD version statement")

    if '''    if "0.11.6" not in main:''' in text:
        text = text.replace(
            '''    if "0.11.6" not in main:''',
            '''    if "0.11.8" not in main:''',
            1,
        )
    elif '''    if "0.11.7" not in main:''' in text:
        text = text.replace(
            '''    if "0.11.7" not in main:''',
            '''    if "0.11.8" not in main:''',
            1,
        )
    else:
        raise RuntimeError("Jarvis v0.11.8 patch missing: version verification")

    if '''        missing.append("backend version 0.11.6")''' in text:
        text = text.replace(
            '''        missing.append("backend version 0.11.6")''',
            '''        missing.append("backend version 0.11.8")''',
            1,
        )
    elif '''        missing.append("backend version 0.11.7")''' in text:
        text = text.replace(
            '''        missing.append("backend version 0.11.7")''',
            '''        missing.append("backend version 0.11.8")''',
            1,
        )
    else:
        raise RuntimeError("Jarvis v0.11.8 patch missing: verification message")

    PATCH_0116.write_text(text, encoding="utf-8")


def verify() -> None:
    text = PATCH_0116.read_text(encoding="utf-8")
    required = (
        '''text.replace('version="0.11.5"', 'version="0.11.8"')''',
        '''text.replace('"version": "0.11.5"', '"version": "0.11.8"')''',
        '''text.replace("HUD 0.11.5", "HUD 0.11.8")''',
        '''if "0.11.8" not in main:''',
        '''missing.append("backend version 0.11.8")''',
        '''last_script = text.rfind("</script>")''',
        '''function_end = main.find("\\n\\ndef _verify_catalog_result_contract"''',
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise RuntimeError(
            "Jarvis v0.11.8 verification failed: " + ", ".join(missing)
        )


if __name__ == "__main__":
    main()
    verify()
