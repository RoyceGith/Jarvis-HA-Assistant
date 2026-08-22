import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.102 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.102 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        '''WAKE_SHADOW_MODEL_PATH = Path(__file__).resolve().parent.parent / "models/wakeword/hey_zbrano.onnx"


def _new_wake_shadow_model() -> tuple[Any, Any]:''',
        '''WAKE_SHADOW_MODEL_PATH = Path(__file__).resolve().parent.parent / "models/wakeword/hey_zbrano.onnx"
WAKE_SHADOW_MELSPEC_PATH = Path(__file__).resolve().parent.parent / "models/wakeword/melspectrogram.onnx"
WAKE_SHADOW_EMBEDDING_PATH = Path(__file__).resolve().parent.parent / "models/wakeword/embedding_model.onnx"


def _new_wake_shadow_model() -> tuple[Any, Any]:''',
        "bundled feature model paths",
    )
    backend = replace_once(
        backend,
        '''    if not WAKE_SHADOW_MODEL_PATH.is_file():
        raise RuntimeError("ZBRANO wake-word model is missing")
    model = OpenWakeWordModel(
        wakeword_models=[str(WAKE_SHADOW_MODEL_PATH)],
        inference_framework="onnx",
    )''',
        '''    required_models = (WAKE_SHADOW_MODEL_PATH, WAKE_SHADOW_MELSPEC_PATH, WAKE_SHADOW_EMBEDDING_PATH)
    missing_models = [path.name for path in required_models if not path.is_file()]
    if missing_models:
        raise RuntimeError(f"ZBRANO wake-word runtime model is missing: {', '.join(missing_models)}")
    model = OpenWakeWordModel(
        wakeword_models=[str(WAKE_SHADOW_MODEL_PATH)],
        inference_framework="onnx",
        melspec_model_path=str(WAKE_SHADOW_MELSPEC_PATH),
        embedding_model_path=str(WAKE_SHADOW_EMBEDDING_PATH),
    )''',
        "explicit feature model loading",
    )

    backend = backend.replace('version="0.12.101"', 'version="0.12.102"')
    backend = backend.replace('"version": "0.12.101"', '"version": "0.12.102"')
    frontend = frontend.replace("HUD 0.12.101", "HUD 0.12.102")

    for marker, location in [
        ('version="0.12.102"', backend),
        ('WAKE_SHADOW_MELSPEC_PATH', backend),
        ('WAKE_SHADOW_EMBEDDING_PATH', backend),
        ('melspec_model_path=str(WAKE_SHADOW_MELSPEC_PATH)', backend),
        ('embedding_model_path=str(WAKE_SHADOW_EMBEDDING_PATH)', backend),
        ('HUD 0.12.102', frontend),
    ]:
        require(location, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
