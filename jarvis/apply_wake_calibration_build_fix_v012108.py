import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.108 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    for marker, location in [
        ('version="0.12.107"', backend),
        ('def _wake_clip_quality', backend),
        ('@app.delete("/api/voice/wake-calibration/invalid")', backend),
        ('started:false,armedAt:performance.now()', frontend),
        ('Recording begins when speech is detected.', frontend),
        ('HUD 0.12.107', frontend),
    ]:
        require(location, marker, marker)

    backend = backend.replace('version="0.12.107"', 'version="0.12.108"')
    backend = backend.replace('"version": "0.12.107"', '"version": "0.12.108"')
    frontend = frontend.replace("HUD 0.12.107", "HUD 0.12.108")

    require(backend, 'version="0.12.108"', "backend version")
    require(frontend, "HUD 0.12.108", "frontend version")
    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
