from pathlib import Path

ROOT = Path("/opt/jarvis")
INDEX = ROOT / "app/static/index.html"
MAIN = ROOT / "app/main.py"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.11.27 patch missing: {label}")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    runtime_marker = '<script id="zbrano-v01126-plugin-runtime">'
    catalog_override_marker = 'const baseCatalogCard = catalogCard;'
    require(text, runtime_marker, "relocated plugin runtime")
    require(text, catalog_override_marker, "catalog override")

    runtime_start = text.find(runtime_marker)
    runtime_end = text.find("</script>", runtime_start)
    if runtime_end < 0:
        raise RuntimeError("ZBRANO v0.11.27 patch missing: plugin runtime close")
    runtime_end += len("</script>")
    runtime_block = text[runtime_start:runtime_end]

    # Remove the v0.11.26 runtime from the end of body first.
    text = text[:runtime_start] + text[runtime_end:]

    override_pos = text.find(catalog_override_marker)
    if override_pos < 0:
        raise RuntimeError("ZBRANO v0.11.27 patch missing: catalog override position")
    override_script_start = text.rfind("<script", 0, override_pos)
    if override_script_start < 0:
        raise RuntimeError("ZBRANO v0.11.27 patch missing: catalog override script start")

    body_pos = text.find("<body")
    if body_pos < 0 or override_script_start <= body_pos:
        raise RuntimeError("ZBRANO v0.11.27 catalog override is not in body")

    # Insert the plugin/catalog definitions immediately before the dependent
    # body script. The DOM is already parsed here, but catalogCard now exists
    # before v0.11.11 decorates it and before Shared Files/Attach handlers run.
    text = (
        text[:override_script_start]
        + runtime_block
        + "\n"
        + text[override_script_start:]
    )

    text = text.replace("HUD 0.11.26", "HUD 0.11.27")
    INDEX.write_text(text, encoding="utf-8")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    text = text.replace('version="0.11.26"', 'version="0.11.27"')
    text = text.replace('"version": "0.11.26"', '"version": "0.11.27"')
    MAIN.write_text(text, encoding="utf-8")


def verify() -> None:
    index = INDEX.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")
    missing = []

    runtime_marker = '<script id="zbrano-v01126-plugin-runtime">'
    runtime_pos = index.find(runtime_marker)
    catalog_def_pos = index.find("function catalogCard(item)", runtime_pos)
    override_pos = index.find("const baseCatalogCard = catalogCard;")
    shared_pos = index.find('const tab=document.getElementById("files-tab")')
    body_pos = index.find("<body")
    head_close = index.find("</head>")

    if runtime_pos < 0:
        missing.append("plugin runtime")
    if runtime_pos <= body_pos or runtime_pos <= head_close:
        missing.append("plugin runtime must remain after DOM begins")
    if catalog_def_pos < 0:
        missing.append("catalogCard definition")
    if override_pos < 0:
        missing.append("catalogCard override")
    if catalog_def_pos >= 0 and override_pos >= 0 and catalog_def_pos > override_pos:
        missing.append("catalogCard must be defined before override")
    if shared_pos < 0:
        missing.append("Shared Files runtime")
    if override_pos >= 0 and shared_pos >= 0 and override_pos > shared_pos:
        missing.append("catalog override must execute before Shared Files runtime")

    # The runtime must no longer be stranded at the end after dependent code.
    body_close = index.rfind("</body>")
    if runtime_pos >= 0 and shared_pos >= 0 and runtime_pos > shared_pos:
        missing.append("plugin runtime still executes after Shared Files runtime")
    if body_close < 0:
        missing.append("body close")

    if "0.11.27" not in main:
        missing.append("backend version 0.11.27")

    if missing:
        raise RuntimeError(
            "ZBRANO v0.11.27 verification failed: " + ", ".join(missing)
        )


if __name__ == "__main__":
    patch_index()
    patch_main()
    verify()
