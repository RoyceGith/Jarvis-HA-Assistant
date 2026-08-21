import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_wake_diagnostics_export_v012106.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_microphone_and_model_measurements_are_separate() -> None:
    assert 'id="wake-mic-rms"' in PATCH
    assert 'id="wake-mic-peak"' in PATCH
    assert "wakeShadowInputRms=Math.sqrt" in PATCH
    assert "wakeShadowAttempt.score=Math.max" in PATCH
    assert "wakeShadowAttempt.above>=2" in PATCH


def test_phrase_test_is_bounded_and_reports_both_signals() -> None:
    assert 'id="wake-test-phrase"' in PATCH
    assert "setTimeout(finishWakeShadowAttempt,4000)" in PATCH
    assert "model ${attempt.score.toFixed(3)}" in PATCH
    assert "RMS ${attempt.rms.toFixed(3)}" in PATCH


def test_export_contains_only_structured_recordings() -> None:
    assert '@app.get("/api/voice/wake-calibration/export")' in PATCH
    assert "positive/{label}" not in PATCH
    assert 'f"{label}/{label}_{index:03d}.wav"' in PATCH
    assert '"manifest.json"' in PATCH
    assert "WAKE_VERIFIER_PATH" not in PATCH.split('async def export_wake_calibration()', 1)[1].split('@app.put("/api/voice/wake-calibration/verifier")', 1)[0]


def test_release_and_build_order_are_aligned() -> None:
    assert 'version: "0.12.106"' in CONFIG
    assert MANIFEST["version"] == "0.12.106"
    copy = "COPY apply_wake_diagnostics_export_v012106.py ./apply_wake_diagnostics_export_v012106.py"
    run = "python3 ./apply_wake_diagnostics_export_v012106.py"
    assert copy in DOCKER and run in DOCKER
    assert DOCKER.index("python3 ./apply_optional_wake_verifier_v012105.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
