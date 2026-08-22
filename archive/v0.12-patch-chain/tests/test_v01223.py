import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_live_developer_progress_v01223.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01223_shows_evidence_based_live_progress():
    assert "Checking the affected runtime layers..." in PATCH
    assert "Problem confirmed. Reviewing the fault boundary..." in PATCH
    assert "Investigation complete. Reviewing the evidence..." in PATCH
    assert "elapsed_seconds" in PATCH


def test_v01223_bounds_developer_investigations():
    assert "timeout=30.0" in PATCH
    assert "hard_timeout = 40.0" in PATCH
    assert "No repository changes were made" in PATCH
    assert "asyncio.shield(tool_task)" in PATCH


def test_v01223_explains_silent_waits_without_exposing_reasoning():
    assert "quietSeconds >= 20" in PATCH
    assert "taking longer than expected; you can stop safely" in PATCH
    assert "chain of thought" not in PATCH.lower()


def test_v01223_is_last_patch_before_release_validation():
    assert "COPY apply_live_developer_progress_v01223.py" in DOCKER
    assert DOCKER.index("python3 ./apply_release_validator_build_fix_v01222.py") < DOCKER.index("python3 ./apply_live_developer_progress_v01223.py")
    assert DOCKER.index("python3 ./apply_live_developer_progress_v01223.py") < DOCKER.index("python3 ./validate_release_manifest.py")


def test_v01223_aligns_release_markers():
    assert 'version: "0.12.23"' in CONFIG
    assert MANIFEST["version"] == "0.12.23"
    assert "ZBRANO v0.12.23" in README
    assert 'version="0.12.23"' in PATCH
    assert '"version": "0.12.23"' in PATCH
    assert "HUD 0.12.23" in PATCH
