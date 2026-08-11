import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.60 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    require(backend, 'version="0.12.59"', "previous backend version")
    require(frontend, "HUD 0.12.59", "previous frontend version")

    backend = backend.replace('version="0.12.59"', 'version="0.12.60"')
    backend = backend.replace('"version": "0.12.59"', '"version": "0.12.60"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.59"', '"X-ZBRANO-Frontend-Version": "0.12.60"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.59"', '"name": "ZBRANO Developer Mode", "version": "0.12.60"')
    frontend = frontend.replace("HUD 0.12.59", "HUD 0.12.60")

    require(backend, 'version="0.12.60"', "backend version")
    require(backend, '"version": "0.12.60"', "runtime version marker")
    require(frontend, "HUD 0.12.60", "frontend version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
