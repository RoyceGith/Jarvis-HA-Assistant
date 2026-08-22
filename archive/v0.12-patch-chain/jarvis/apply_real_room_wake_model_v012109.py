import hashlib
import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"
MODEL = ROOT / "models/wakeword/hey_zbrano.onnx"
MODEL_SHA256 = "0fb509d0c50e4350c3c8fb8c222d0c5d21f49c6479c242f35e0b7f6da97bdf8a"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.109 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    require(backend, 'version="0.12.108"', "backend version")
    require(frontend, "HUD 0.12.108", "frontend version")
    require(backend, 'wakeword_models=[str(WAKE_SHADOW_MODEL_PATH)]', "local wake model")

    if hashlib.sha256(MODEL.read_bytes()).hexdigest() != MODEL_SHA256:
        raise RuntimeError("ZBRANO v0.12.109 wake model checksum mismatch")

    backend = backend.replace('version="0.12.108"', 'version="0.12.109"')
    backend = backend.replace('"version": "0.12.108"', '"version": "0.12.109"')
    frontend = frontend.replace("HUD 0.12.108", "HUD 0.12.109")

    require(backend, 'version="0.12.109"', "updated backend version")
    require(frontend, "HUD 0.12.109", "updated frontend version")
    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
