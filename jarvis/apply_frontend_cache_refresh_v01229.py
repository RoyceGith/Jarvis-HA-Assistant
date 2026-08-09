import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"ZBRANO v0.12.29 patch expected one {label} marker; found {count}"
        )
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.29 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        '''@app.get("/{path:path}", include_in_schema=False)
async def frontend(path: str = "") -> FileResponse:
    candidate = STATIC_DIR / path
    if path and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(STATIC_DIR / "index.html")''',
        '''@app.get("/{path:path}", include_in_schema=False)
async def frontend(path: str = "") -> FileResponse:
    candidate = STATIC_DIR / path
    if path and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-ZBRANO-Frontend-Version": "0.12.29",
        },
    )''',
        "frontend response cache policy",
    )
    frontend = replace_once(
        frontend,
        '''  <meta charset="utf-8">''',
        '''  <meta charset="utf-8">
  <meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate, max-age=0">
  <meta http-equiv="Pragma" content="no-cache">
  <meta http-equiv="Expires" content="0">''',
        "frontend cache metadata",
    )

    backend = backend.replace('version="0.12.28"', 'version="0.12.29"')
    backend = backend.replace('"version": "0.12.28"', '"version": "0.12.29"')
    frontend = frontend.replace("HUD 0.12.28", "HUD 0.12.29")

    require(backend, '"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"', "HTTP cache prevention")
    require(backend, '"X-ZBRANO-Frontend-Version": "0.12.29"', "frontend response version")
    require(frontend, 'http-equiv="Cache-Control"', "document cache metadata")
    require(frontend, 'id="composer-plugin-icons"', "v0.12.28 plugin indicators")
    require(backend, 'version="0.12.29"', "backend version")
    require(frontend, "HUD 0.12.29", "HUD version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
