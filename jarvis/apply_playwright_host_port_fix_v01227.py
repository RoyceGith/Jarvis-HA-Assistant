import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.27 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = backend.replace('version="0.12.26"', 'version="0.12.27"')
    backend = backend.replace('"version": "0.12.26"', '"version": "0.12.27"')
    frontend = frontend.replace("HUD 0.12.26", "HUD 0.12.27")

    require(backend, 'version="0.12.27"', "backend version")
    require(
        backend,
        '"clientInfo": {"name": "ZBRANO Developer Mode", "version": "0.12.27"}',
        "Playwright MCP client version",
    )
    require(frontend, "HUD 0.12.27", "HUD version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
