from pathlib import Path

ROOT = Path("/opt/jarvis")
INDEX = ROOT / "app/static/index.html"
MAIN = ROOT / "app/main.py"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"Jarvis v0.11.4 patch missing: {label}")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    replacements = {
        'const catalogSearch=document.getElementById("catalog-search");':
            'var catalogSearch=document.getElementById("catalog-search");',
        'const catalogCategory=document.getElementById("catalog-category");':
            'var catalogCategory=document.getElementById("catalog-category");',
        'const catalogRefresh=document.getElementById("catalog-refresh");':
            'var catalogRefresh=document.getElementById("catalog-refresh");',
        'const catalogStatus=document.getElementById("catalog-status")||(() => {':
            'var catalogStatus=document.getElementById("catalog-status")||(() => {',
        'const catalogResults=document.getElementById("catalog-results")||(() => {':
            'var catalogResults=document.getElementById("catalog-results")||(() => {',
    }
    for old, new in replacements.items():
        require(text, old, old)
        text = text.replace(old, new, 1)

    loader_marker = 'async function loadCatalog(force=false){\n  if(!catalogResults)return;'
    require(text, loader_marker, "loadCatalog start")
    loader_start = '''async function loadCatalog(force=false){
  ensurePluginDomReady();
  catalogSearch=document.getElementById("catalog-search");
  catalogCategory=document.getElementById("catalog-category");
  catalogRefresh=document.getElementById("catalog-refresh");
  catalogStatus=document.getElementById("catalog-status");
  catalogResults=document.getElementById("catalog-results");
  if(!catalogResults||!catalogStatus)return;'''
    text = text.replace(loader_marker, loader_start, 1)

    old_catalog_task = 'if (typeof loadCatalog === "function") tasks.push(loadCatalog(false));'
    new_catalog_task = '''if (typeof loadCatalog === "function") {
        tasks.push(new Promise(resolve => window.setTimeout(resolve, 0)).then(() => loadCatalog(false)));
      }'''
    require(text, old_catalog_task, "catalog recovery task")
    text = text.replace(old_catalog_task, new_catalog_task, 1)

    old_auto = '  if (tabs.plugins?.classList.contains("active")) recoverPlugins();'
    if old_auto in text:
        text = text.replace(old_auto, '', 1)

    text = text.replace("HUD 0.11.3", "HUD 0.11.4")
    INDEX.write_text(text, encoding="utf-8")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    text = text.replace('version="0.11.3"', 'version="0.11.4"')
    text = text.replace('"version": "0.11.3"', '"version": "0.11.4"')
    MAIN.write_text(text, encoding="utf-8")


def verify() -> None:
    index = INDEX.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")

    missing = []
    for marker in (
        'var catalogResults=',
        'var catalogStatus=',
        'catalogResults=document.getElementById("catalog-results");',
        'window.setTimeout(resolve, 0)',
    ):
        if marker not in index:
            missing.append(marker)

    for stale in (
        'const catalogResults=',
        'const catalogStatus=',
        'if (tabs.plugins?.classList.contains("active")) recoverPlugins();',
    ):
        if stale in index:
            missing.append(f"stale: {stale}")

    if "0.11.4" not in main:
        missing.append("backend version 0.11.4")

    if missing:
        raise RuntimeError(
            "Jarvis v0.11.4 verification failed: " + ", ".join(missing)
        )


if __name__ == "__main__":
    patch_index()
    patch_main()
    verify()
