import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_optional_wake_verifier_v012105.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_personal_verifier_is_opt_in_and_persistent() -> None:
    assert "WAKE_VERIFIER_ENABLED_PATH" in PATCH
    assert "WAKE_VERIFIER_PATH.is_file() and WAKE_VERIFIER_ENABLED_PATH.is_file()" in PATCH
    assert '@app.put("/api/voice/wake-calibration/verifier")' in PATCH
    assert 'id="wake-use-verifier"' in PATCH


def test_verifier_can_be_deleted_without_recordings() -> None:
    assert '@app.delete("/api/voice/wake-calibration/verifier")' in PATCH
    assert 'id="wake-delete-verifier"' in PATCH
    assert "All calibration recordings were preserved." in PATCH
    verifier_delete = PATCH.split('@app.delete("/api/voice/wake-calibration/verifier")', 1)[1].split('@app.delete("/api/voice/wake-calibration")', 1)[0]
    assert "WAKE_POSITIVE_DIR" not in verifier_delete
    assert "WAKE_NEGATIVE_DIR" not in verifier_delete


def test_training_does_not_automatically_enable_verifier() -> None:
    assert "The broader base model remains active until you enable the verifier." in PATCH
    assert 'wakeUseVerifier.addEventListener("change"' in PATCH
    assert 'fetch(`api/voice/wake-calibration/verifier?enabled=${enabled}`' in PATCH


def test_release_and_build_order_are_aligned() -> None:
    assert 'version: "0.12.105"' in CONFIG
    assert MANIFEST["version"] == "0.12.105"
    copy = "COPY apply_optional_wake_verifier_v012105.py ./apply_optional_wake_verifier_v012105.py"
    run = "python3 ./apply_optional_wake_verifier_v012105.py"
    assert copy in DOCKER and run in DOCKER
    assert DOCKER.index("python3 ./apply_wake_verifier_route_fix_v012104.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
