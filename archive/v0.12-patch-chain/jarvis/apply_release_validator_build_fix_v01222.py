from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.22 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")
    require(backend, 'version="0.12.21"', "backend version")
    require(frontend, "HUD 0.12.21", "HUD version")
    backend = backend.replace('version="0.12.21"', 'version="0.12.22"')
    backend = backend.replace('"version": "0.12.21"', '"version": "0.12.22"')
    frontend = frontend.replace("HUD 0.12.21", "HUD 0.12.22")
    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")

    require(backend, 'version="0.12.22"', "updated backend version")
    require(backend, '"version": "0.12.22"', "updated health version")
    require(frontend, "HUD 0.12.22", "updated HUD version")


if __name__ == "__main__":
    main()
