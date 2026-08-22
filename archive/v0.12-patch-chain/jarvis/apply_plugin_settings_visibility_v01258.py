import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.58 patch missing: {label}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"ZBRANO v0.12.58 patch expected one {label}; found {count}"
        )
    return text.replace(old, new, 1)


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    for marker, label in (
        ('toggle.className = "plugin-settings-toggle"', "installed plugin Settings action"),
        ('settings.className = "plugin-settings"', "installed plugin settings container"),
        ('row.querySelector(":scope > .plugin-settings")', "compact settings reuse"),
        ('actions.prepend(toggle)', "Settings toggle insertion"),
    ):
        require(frontend, marker, label)

    backend = backend.replace('version="0.12.57"', 'version="0.12.58"')
    backend = backend.replace('"version": "0.12.57"', '"version": "0.12.58"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.57"', '"X-ZBRANO-Frontend-Version": "0.12.58"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.57"', '"name": "ZBRANO Developer Mode", "version": "0.12.58"')
    frontend = frontend.replace("HUD 0.12.57", "HUD 0.12.58")

    require(backend, 'version="0.12.58"', "backend version")
    require(backend, '"version": "0.12.58"', "runtime version marker")
    require(frontend, "HUD 0.12.58", "frontend version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
