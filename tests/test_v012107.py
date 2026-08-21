import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_validated_wake_samples_v012107.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_backend_rejects_invalid_audio_and_counts_only_valid_samples() -> None:
    assert "def _wake_clip_quality" in PATCH
    assert "rms >= 0.003" in PATCH
    assert "peak >= 0.03" in PATCH
    assert "nonzero_fraction >= 0.08" in PATCH
    assert "clipped_fraction <= 0.005" in PATCH
    assert "target.unlink(missing_ok=True)" in PATCH
    assert "positive_invalid" in PATCH and "negative_invalid" in PATCH


def test_capture_waits_for_speech_and_has_bounded_stop_conditions() -> None:
    assert "started:false,armedAt:performance.now()" in PATCH
    assert 'wakeCalibrationCapture={label,samples:[]};' in PATCH
    assert "could not isolate the legacy calibration message" in PATCH
    assert "wakeShadowInputRms>=.012" in PATCH
    assert "now-capture.lastVoiceAt>=650" in PATCH
    assert "capture.samples.length>=64000" in PATCH
    assert "now-capture.armedAt>=8000" in PATCH


def test_invalid_cleanup_preserves_valid_samples() -> None:
    assert '@app.delete("/api/voice/wake-calibration/invalid")' in PATCH
    assert 'if not _wake_clip_quality(clip).get("valid")' in PATCH
    assert 'id="wake-remove-invalid"' in PATCH
    assert "Valid clips were preserved." in PATCH


def test_training_and_export_filter_existing_evidence() -> None:
    assert "positive_paths = [path for path" in PATCH
    assert "negative_paths = [path for path" in PATCH
    assert "valid_index = 0" in PATCH
    assert "if not _wake_clip_quality(clip).get" in PATCH


def test_release_and_build_order_are_aligned() -> None:
    assert 'version: "0.12.108"' in CONFIG
    assert MANIFEST["version"] == "0.12.108"
    copy = "COPY apply_validated_wake_samples_v012107.py ./apply_validated_wake_samples_v012107.py"
    run = "python3 ./apply_validated_wake_samples_v012107.py"
    assert copy in DOCKER and run in DOCKER
    assert DOCKER.index("python3 ./apply_wake_diagnostics_export_v012106.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
