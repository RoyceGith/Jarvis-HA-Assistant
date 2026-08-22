from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_required(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count < 1:
        raise RuntimeError(f"ZBRANO v0.12.85 release bump missing {label}")
    return text.replace(old, new)


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")
    backend = replace_required(backend, 'version="0.12.76"', 'version="0.12.85"', "backend version")
    backend = replace_required(backend, '"version": "0.12.76"', '"version": "0.12.85"', "runtime version")
    frontend = replace_required(frontend, "HUD 0.12.76", "HUD 0.12.85", "frontend version")
    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()