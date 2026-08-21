import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_wake_shadow_resources_v012102.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))
MODEL_ROOT = ROOT / "jarvis/models/wakeword"


def test_feature_models_are_exact_official_assets() -> None:
    expected = {
        "melspectrogram.onnx": (1087958, "ba2b0e0f8b7b875369a2c89cb13360ff53bac436f2895cced9f479fa65eb176f"),
        "embedding_model.onnx": (1326578, "70d164290c1d095d1d4ee149bc5e00543250a7316b59f31d056cff7bd3075c1f"),
    }
    for filename, (size, digest) in expected.items():
        model = MODEL_ROOT / filename
        assert model.stat().st_size == size
        assert hashlib.sha256(model.read_bytes()).hexdigest() == digest


def test_runtime_uses_explicit_bundled_feature_paths() -> None:
    assert "WAKE_SHADOW_MELSPEC_PATH" in PATCH
    assert "WAKE_SHADOW_EMBEDDING_PATH" in PATCH
    assert "melspec_model_path=str(WAKE_SHADOW_MELSPEC_PATH)" in PATCH
    assert "embedding_model_path=str(WAKE_SHADOW_EMBEDDING_PATH)" in PATCH
    assert "missing_models" in PATCH


def test_release_and_build_order_are_aligned() -> None:
    assert 'version: "0.12.102"' in CONFIG
    assert MANIFEST["version"] == "0.12.102"
    copy = "COPY apply_wake_shadow_resources_v012102.py ./apply_wake_shadow_resources_v012102.py"
    run = "python3 ./apply_wake_shadow_resources_v012102.py"
    assert copy in DOCKER and run in DOCKER
    assert DOCKER.index("python3 ./apply_local_wake_shadow_v012101.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
