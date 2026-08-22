import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_native_web_search_v01226.py").read_text(encoding="utf-8")
PLAYWRIGHT_PATCH = (ROOT / "jarvis/apply_playwright_mcp_readiness_fix_v01226.py").read_text(encoding="utf-8")
RUN = (ROOT / "jarvis/run.sh").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01226_uses_current_responses_web_search_contract():
    assert '"type": "web_search"' in PATCH
    assert '"web_search_call.action.sources"' in PATCH
    assert "web_search_preview" not in PATCH
    assert 'search_context_size' in PATCH


def test_v01226_supports_auto_forced_and_disabled_search():
    assert 'pattern="^(auto|search|off)$"' in PATCH
    assert '{"type": "web_search"} if search_mode == "search"' in PATCH
    assert 'search_mode == "off"' in PATCH
    assert 'id="web-search-mode"' in PATCH


def test_v01226_extracts_persists_and_renders_safe_sources():
    assert "def response_web_sources" in PATCH
    assert 'event.get("type") == "sources"' in PATCH
    assert 'eventData.type === "sources"' in PATCH
    assert 'target="_blank" rel="noopener noreferrer"' in PATCH
    assert 'startswith(("https://", "http://"))' in PATCH


def test_v01226_preserves_developer_tool_isolation():
    assert 'if developer_mode_enabled() or search_mode == "off"' in PATCH
    assert "Developer Mode remains isolated from public search" in README


def test_v01226_is_last_patch_before_release_validation():
    assert "COPY apply_native_web_search_v01226.py" in DOCKER
    assert "COPY apply_playwright_mcp_readiness_fix_v01226.py" in DOCKER
    assert DOCKER.index("python3 ./apply_bounded_model_continuation_v01225.py") < DOCKER.index("python3 ./apply_native_web_search_v01226.py")
    assert DOCKER.index("python3 ./apply_native_web_search_v01226.py") < DOCKER.index("python3 ./apply_playwright_mcp_readiness_fix_v01226.py")
    assert DOCKER.index("python3 ./apply_playwright_mcp_readiness_fix_v01226.py") < DOCKER.index("python3 ./validate_release_manifest.py")


def test_v01226_aligns_release_markers():
    assert 'version: "0.12.26"' in CONFIG
    assert MANIFEST["version"] == "0.12.26"
    assert "ZBRANO v0.12.26" in README
    assert 'version="0.12.26"' in PATCH
    assert '"version": "0.12.26"' in PATCH
    assert "HUD 0.12.26" in PATCH


def test_v01226_allows_only_local_playwright_mcp_hosts():
    assert '--allowed-hosts "127.0.0.1' in RUN
    assert 'localhost' in RUN
    assert '--host 127.0.0.1' in RUN
    assert '--allowed-hosts "*"' not in RUN


def test_v01226_reports_bounded_playwright_startup_evidence():
    assert "def playwright_chromium_executable" in PLAYWRIGHT_PATCH
    assert "def playwright_process_available" in PLAYWRIGHT_PATCH
    assert "def playwright_startup_log_tail" in PLAYWRIGHT_PATCH
    assert "max_bytes: int = 4096" in PLAYWRIGHT_PATCH
    assert "max_lines: int = 12" in PLAYWRIGHT_PATCH
    assert "response_detail" in PLAYWRIGHT_PATCH
    assert "def playwright_redact_evidence" in PLAYWRIGHT_PATCH


def test_v01226_updates_playwright_mcp_client_version():
    assert '"version": "0.12.26"' in PLAYWRIGHT_PATCH
