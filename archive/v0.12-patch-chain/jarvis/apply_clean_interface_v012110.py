import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"

SCANLINES = '''    body::after {
      content: ""; position: fixed; inset: 0; z-index: 2; pointer-events: none;
      background: repeating-linear-gradient(0deg, transparent 0 3px, rgba(92,236,255,.025) 3px 4px);
    }
'''
LIGHT_SCANLINES = '''    :root[data-theme="light"] body::after { background: repeating-linear-gradient(0deg, transparent 0 3px, rgba(23,72,67,.035) 3px 4px); }
'''


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.110 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    require(backend, 'version="0.12.109"', "backend version")
    require(frontend, "HUD 0.12.109", "frontend version")
    require(frontend, SCANLINES, "global scanline overlay")
    require(frontend, LIGHT_SCANLINES, "light-theme scanline overlay")

    frontend = frontend.replace(SCANLINES, "", 1)
    frontend = frontend.replace(LIGHT_SCANLINES, "", 1)
    backend = backend.replace('version="0.12.109"', 'version="0.12.110"')
    backend = backend.replace('"version": "0.12.109"', '"version": "0.12.110"')
    frontend = frontend.replace("HUD 0.12.109", "HUD 0.12.110")

    require(backend, 'version="0.12.110"', "updated backend version")
    require(frontend, "HUD 0.12.110", "updated frontend version")
    if "repeating-linear-gradient(0deg, transparent 0 3px" in frontend:
        raise RuntimeError("ZBRANO v0.12.110 scanline overlay remains")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
