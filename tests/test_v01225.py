import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_bounded_model_continuation_v01225.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01225_keeps_silent_model_work_observable():
    assert '"type": "zbrano.progress"' in PATCH
    assert "Reviewing the diagnostic evidence..." in PATCH
    assert "Waiting for Developer repository tools..." in PATCH
    assert "elapsed_seconds" in PATCH


def test_v01225_reports_remote_mcp_lifecycle_events():
    assert 'item_type == "mcp_list_tools"' in PATCH
    assert 'item_type != "mcp_call"' in PATCH
    assert "Developer tool started:" in PATCH
    assert "Developer tool completed:" in PATCH


def test_v01225_bounds_continuations_and_the_complete_request():
    assert "hard_timeout=min(180.0, remaining)" in PATCH
    assert "hard_timeout=180.0" in PATCH
    assert "request_deadline = time.monotonic() + (300.0" in PATCH
    assert "5-minute safety limit" in PATCH
    assert "no unapproved repository write" in PATCH


def test_v01225_is_last_patch_before_release_validation():
    assert "COPY apply_bounded_model_continuation_v01225.py" in DOCKER
    assert DOCKER.index("python3 ./apply_diagnostic_investigate_fix_v01224.py") < DOCKER.index("python3 ./apply_bounded_model_continuation_v01225.py")
    assert DOCKER.index("python3 ./apply_bounded_model_continuation_v01225.py") < DOCKER.index("python3 ./validate_release_manifest.py")


def test_v01225_aligns_release_markers():
    assert 'version: "0.12.25"' in CONFIG
    assert MANIFEST["version"] == "0.12.25"
    assert "ZBRANO v0.12.25" in README
    assert 'version="0.12.25"' in PATCH
    assert '"version": "0.12.25"' in PATCH
    assert "HUD 0.12.25" in PATCH
