import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXED_PATCH = (ROOT / "jarvis/apply_validated_wake_samples_v012107.py").read_text(encoding="utf-8")
RELEASE_PATCH = (ROOT / "jarvis/apply_wake_calibration_build_fix_v012108.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_legacy_calibration_patch_uses_encoding_independent_boundary() -> None:
    assert "speech-armed calibration state" in FIXED_PATCH
    assert "calibration_message_start = frontend.find" in FIXED_PATCH
    assert "could not isolate the legacy calibration message" in FIXED_PATCH
    assert "label == \"speech-armed calibration\"" in FIXED_PATCH


def test_release_patch_requires_completed_validation_feature() -> None:
    assert 'def _wake_clip_quality' in RELEASE_PATCH
    assert '@app.delete("/api/voice/wake-calibration/invalid")' in RELEASE_PATCH
    assert "started:false,armedAt:performance.now()" in RELEASE_PATCH
    assert "Recording begins when speech is detected." in RELEASE_PATCH


def test_release_and_build_order_are_aligned() -> None:
    assert 'version: "0.12.108"' in CONFIG
    assert MANIFEST["version"] == "0.12.108"
    copy = "COPY apply_wake_calibration_build_fix_v012108.py ./apply_wake_calibration_build_fix_v012108.py"
    run = "python3 ./apply_wake_calibration_build_fix_v012108.py"
    assert copy in DOCKER and run in DOCKER
    assert DOCKER.index("python3 ./apply_validated_wake_samples_v012107.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
