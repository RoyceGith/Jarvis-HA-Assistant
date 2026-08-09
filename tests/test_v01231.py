import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_live_tool_timeline_v01231.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01231_streams_real_tool_activity_metadata():
    assert "def openai_tool_activity" in PATCH
    assert 'item_type != "mcp_call"' in PATCH
    assert '"native-web-search"' in PATCH
    assert 'yield stream_event("activity", **activity)' in PATCH
    assert 'state="waiting_approval"' in PATCH


def test_v01231_renders_compact_timed_tool_timeline():
    assert 'id="tool-timeline"' in PATCH
    assert "function applyToolActivity" in PATCH
    assert "function updateToolTimelineClock" in PATCH
    assert "function finishOpenToolActivities" in PATCH
    assert "toolTimeline.children.length > 8" in PATCH


def test_v01231_pulses_only_the_active_plugin():
    assert "function setPluginToolActive" in PATCH
    assert 'data-composer-plugin' in PATCH
    assert 'classList.toggle("tool-active", active)' in PATCH
    assert "plugin-tool-pulse" in PATCH
    assert "prefers-reduced-motion" in PATCH


def test_v01231_uses_readable_core_activity_phases():
    for label in (
        "Searching web", "Reading Home Assistant", "Reading Workshop Memory", "Updating Workshop Memory",
        "Inspecting ZBRANO interface", "Investigating ZBRANO",
    ):
        assert label in PATCH


def test_v01231_matches_attachment_controls_to_web_selector():
    assert ".attachment-controls #attach-file,.attachment-controls #attachment-scope" in PATCH
    assert "min-height: 1.9rem; height: 1.9rem" in PATCH
    assert "border-radius: 999px" in PATCH
    assert "font-size: .72rem" in PATCH
    assert ".attachment-controls #attachment-state" in PATCH


def test_v01231_runs_last_and_aligns_release_markers():
    assert "COPY apply_live_tool_timeline_v01231.py" in DOCKER
    assert DOCKER.index("python3 ./apply_local_plugin_icons_and_composer_stack_v01230.py") < DOCKER.index("python3 ./apply_live_tool_timeline_v01231.py")
    assert DOCKER.index("python3 ./apply_live_tool_timeline_v01231.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.31"' in CONFIG
    assert MANIFEST["version"] == "0.12.31"
    assert "ZBRANO v0.12.31" in README
    assert 'version="0.12.31"' in PATCH
    assert "HUD 0.12.31" in PATCH
