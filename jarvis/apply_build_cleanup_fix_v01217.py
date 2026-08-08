from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.17 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")
    require(backend, 'version="0.12.16"', "backend version")
    require(frontend, "HUD 0.12.16", "frontend version")
    backend = backend.replace('version="0.12.16"', 'version="0.12.17"')
    backend = backend.replace('"version": "0.12.16"', '"version": "0.12.17"')
    frontend = frontend.replace("HUD 0.12.16", "HUD 0.12.17")
    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


def verify() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")
    for marker in ('version="0.12.17"', '"version": "0.12.17"'):
        require(backend, marker, marker)
    require(frontend, "HUD 0.12.17", "HUD version")


if __name__ == "__main__":
    main()
    verify()
