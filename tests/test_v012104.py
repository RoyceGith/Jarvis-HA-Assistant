import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_wake_verifier_route_fix_v012104.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_static_train_route_cannot_collide_with_sample_upload() -> None:
    assert '@app.post("/api/voice/wake-calibration/samples/{label}")' in PATCH
    assert 'api/voice/wake-calibration/samples/${label}' in PATCH
    assert '"non-conflicting calibration sample route"' in PATCH


def test_structured_errors_are_human_readable() -> None:
    assert "function wakeCalibrationError" in PATCH
    assert 'Array.isArray(detail)' in PATCH
    assert 'JSON.stringify(detail)' in PATCH
    assert "[object Object]" not in PATCH


def test_release_and_build_order_are_aligned() -> None:
    assert 'version: "0.12.104"' in CONFIG
    assert MANIFEST["version"] == "0.12.104"
    copy = "COPY apply_wake_verifier_route_fix_v012104.py ./apply_wake_verifier_route_fix_v012104.py"
    run = "python3 ./apply_wake_verifier_route_fix_v012104.py"
    assert copy in DOCKER and run in DOCKER
    assert DOCKER.index("python3 ./apply_personal_wake_verifier_v012103.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
