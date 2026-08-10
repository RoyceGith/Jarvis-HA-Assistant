import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_playwright_chat_isolation_v01237.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01237_marks_playwright_navigation_as_internal():
    assert 'inspection_url = f"{url}?zbrano_inspection=1"' in PATCH
    assert '"url": inspection_url' in PATCH
    assert 'new URLSearchParams(window.location.search)' in PATCH
    assert '"zbrano-playwright-inspection"' in PATCH


def test_v01237_excludes_inspection_sessions_from_chat_storage_and_catalog():
    assert '"zbrano-playwright-"' in PATCH
    assert "INTERNAL_CHAT_SESSION_PREFIXES" in PATCH
    assert "zbrano-diagnostic-" in PATCH
    assert "is_internal_chat_session" not in PATCH  # Uses the existing centralized filter.


def test_v01237_preserves_normal_browser_chat_identity():
    assert "if (!zbranoInspectionSession)" in PATCH
    assert 'localStorage.getItem("jarvis_chat_session_id")' in PATCH
    assert "crypto.randomUUID" in PATCH


def test_v01237_refines_runtime_status_and_conversation_sidebar():
    assert "failed to place Developer Mode above Online/version" in PATCH
    assert 'id=\"conversations-toggle\"' in PATCH
    assert ".chat-shell.conversations-collapsed" in PATCH
    assert ".chat-rename, .chat-delete" in PATCH
    assert 'storageKey = "zbrano_conversations_collapsed"' in PATCH
    assert 'collapsed ? ">" : "<"' in PATCH


def test_v01237_runs_last_and_aligns_release_markers():
    assert "COPY apply_playwright_chat_isolation_v01237.py" in DOCKER
    assert DOCKER.index("python3 ./apply_playwright_routing_timeout_v01236.py") < DOCKER.index("python3 ./apply_playwright_chat_isolation_v01237.py")
    assert DOCKER.index("python3 ./apply_playwright_chat_isolation_v01237.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.37"' in CONFIG
    assert MANIFEST["version"] == "0.12.37"
    assert "ZBRANO v0.12.37" in README
    assert 'version="0.12.37"' in PATCH
    assert "HUD 0.12.37" in PATCH
