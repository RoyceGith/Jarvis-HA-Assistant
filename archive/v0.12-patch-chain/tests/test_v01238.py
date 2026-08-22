import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_mobile_chat_layout_v01238.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01238_keeps_mobile_navigation_to_one_compact_row():
    assert "flex-wrap: nowrap" in PATCH
    assert "overflow-x: auto" in PATCH
    assert "scrollbar-width: none" in PATCH
    assert "#developer-tab { margin-left: 0; }" in PATCH


def test_v01238_prioritizes_the_mobile_chat_viewport():
    assert "savedCollapse === null ? phoneDefault" in PATCH
    assert 'window.matchMedia("(max-width: 760px)")' in PATCH
    assert ".voice-settings { display: none; }" in PATCH
    assert "#messages { min-height: 5rem" in PATCH
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in PATCH
    assert ".composer-input-stack { grid-column: 1 / -1" in PATCH


def test_v01238_matches_title_editor_to_conversation_actions():
    assert ".chat-title-editor" in PATCH
    assert "height: 1.8rem" in PATCH
    assert "height: 1.65rem" in PATCH
    assert "line-height: 1.65rem" in PATCH


def test_v01238_repairs_automation_safety_layout():
    assert "#automations-panel::before { display: none; }" in PATCH
    assert "#autonomy-settings-form" in PATCH
    assert "#automation-draft-form" in PATCH
    assert "display: block" in PATCH
    assert ".autonomy-safety-grid > .autonomy-card" in PATCH
    assert ".autonomy-form-grid textarea" in PATCH
    assert "max-width: 100%" in PATCH
    assert ".autonomy-form-actions { flex-wrap: wrap; }" in PATCH


def test_v01238_handles_short_phone_viewports():
    assert "(max-width: 760px) and (max-height: 560px)" in PATCH
    assert ".voice-bar { display: none; }" in PATCH
    assert "min-height: 100dvh" not in PATCH  # Preserve the existing dynamic viewport implementation.


def test_v01238_runs_last_and_aligns_release_markers():
    assert "COPY apply_mobile_chat_layout_v01238.py" in DOCKER
    assert DOCKER.index("python3 ./apply_playwright_chat_isolation_v01237.py") < DOCKER.index("python3 ./apply_mobile_chat_layout_v01238.py")
    assert DOCKER.index("python3 ./apply_mobile_chat_layout_v01238.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.38"' in CONFIG
    assert MANIFEST["version"] == "0.12.38"
    assert "ZBRANO v0.12.38" in README
    assert 'version="0.12.38"' in PATCH
    assert "HUD 0.12.38" in PATCH
