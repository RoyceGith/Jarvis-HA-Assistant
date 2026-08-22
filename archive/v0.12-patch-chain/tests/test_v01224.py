import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_diagnostic_investigate_fix_v01224.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01224_adds_action_only_to_failed_diagnostics():
    assert 'if (status === "failed")' in PATCH
    assert 'fixButton.textContent = "Investigate & Fix"' in PATCH
    assert "item.repair_hint" in PATCH


def test_v01224_enables_developer_mode_and_launches_chat():
    assert 'fetch("api/developer/mode"' in PATCH
    assert "JSON.stringify({enabled: true})" in PATCH
    assert 'document.getElementById("chat-tab")?.click()' in PATCH
    assert "chatForm.requestSubmit();" in PATCH


def test_v01224_preserves_context_and_prevents_duplicate_launches():
    assert "Return to diagnostic" in PATCH
    assert "launchInProgress || activeRequest" in PATCH
    assert "Finish or stop the current Chat request" in PATCH


def test_v01224_is_last_patch_before_release_validation():
    assert "COPY apply_diagnostic_investigate_fix_v01224.py" in DOCKER
    assert DOCKER.index("python3 ./apply_live_developer_progress_v01223.py") < DOCKER.index("python3 ./apply_diagnostic_investigate_fix_v01224.py")
    assert DOCKER.index("python3 ./apply_diagnostic_investigate_fix_v01224.py") < DOCKER.index("python3 ./validate_release_manifest.py")


def test_v01224_aligns_release_markers():
    assert 'version: "0.12.24"' in CONFIG
    assert MANIFEST["version"] == "0.12.24"
    assert "ZBRANO v0.12.24" in README
    assert 'version="0.12.24"' in PATCH
    assert '"version": "0.12.24"' in PATCH
    assert "HUD 0.12.24" in PATCH
