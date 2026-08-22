import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.61 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    for marker, label in (
        ('child !== head && child !== settings', "direct tool migration"),
        ('settings.appendChild(child)', "settings population"),
        ('new MutationObserver(compactPluginRows)', "installed plugin observer"),
        ('pluginRowsObserver.observe(pluginListNode, {childList: true})', "plugin row observation"),
    ):
        require(frontend, marker, label)

    require(backend, 'version="0.12.60"', "previous backend version")
    require(frontend, "HUD 0.12.60", "previous frontend version")

    backend = backend.replace('version="0.12.60"', 'version="0.12.61"')
    backend = backend.replace('"version": "0.12.60"', '"version": "0.12.61"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.60"', '"X-ZBRANO-Frontend-Version": "0.12.61"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.60"', '"name": "ZBRANO Developer Mode", "version": "0.12.61"')
    frontend = frontend.replace("HUD 0.12.60", "HUD 0.12.61")

    require(backend, 'version="0.12.61"', "backend version")
    require(backend, '"version": "0.12.61"', "runtime version marker")
    require(frontend, "HUD 0.12.61", "frontend version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
