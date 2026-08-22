import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.63 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    require(frontend, '<div class="plugin-actions">${pluginActions}</div></div>${p.oauth_connected?', "OAuth details outside plugin header")
    require(frontend, '<div class="plugin-oauth-details">', "OAuth detail sibling")
    require(frontend, "child !== head && child !== settings", "detail migration into Settings")
    require(backend, 'version="0.12.62"', "previous backend version")
    require(frontend, "HUD 0.12.62", "previous frontend version")

    backend = backend.replace('version="0.12.62"', 'version="0.12.63"')
    backend = backend.replace('"version": "0.12.62"', '"version": "0.12.63"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.62"', '"X-ZBRANO-Frontend-Version": "0.12.63"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.62"', '"name": "ZBRANO Developer Mode", "version": "0.12.63"')
    frontend = frontend.replace("HUD 0.12.62", "HUD 0.12.63")

    require(backend, 'version="0.12.63"', "backend version")
    require(backend, '"version": "0.12.63"', "runtime version marker")
    require(frontend, "HUD 0.12.63", "frontend version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
