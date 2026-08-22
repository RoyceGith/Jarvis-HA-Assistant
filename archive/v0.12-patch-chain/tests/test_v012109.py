import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "jarvis/models/wakeword/hey_zbrano.onnx"
MODEL_README = (ROOT / "jarvis/models/wakeword/README.md").read_text(encoding="utf-8")
PATCH = (ROOT / "jarvis/apply_real_room_wake_model_v012109.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_real_room_model_is_exact_release_artifact() -> None:
    expected = "0fb509d0c50e4350c3c8fb8c222d0c5d21f49c6479c242f35e0b7f6da97bdf8a"
    assert hashlib.sha256(MODEL.read_bytes()).hexdigest() == expected
    assert expected in MODEL_README
    assert "20/21 wake phrases" in MODEL_README
    assert "19/19" in MODEL_README


def test_model_remains_inside_silent_shadow_boundary() -> None:
    assert 'wakeword_models=[str(WAKE_SHADOW_MODEL_PATH)]' in PATCH
    assert "checksum mismatch" in PATCH
    assert "cannot activate chat" in MODEL_README


def test_release_and_build_order_are_aligned() -> None:
    assert 'version: "0.12.109"' in CONFIG
    assert MANIFEST["version"] == "0.12.109"
    copy = "COPY apply_real_room_wake_model_v012109.py ./apply_real_room_wake_model_v012109.py"
    run = "python3 ./apply_real_room_wake_model_v012109.py"
    assert copy in DOCKER and run in DOCKER
    assert DOCKER.index("python3 ./apply_wake_calibration_build_fix_v012108.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
