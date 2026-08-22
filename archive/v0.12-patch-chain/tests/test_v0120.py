from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_developer_mode_self_diagnostics_v0120.py").read_text(encoding="utf-8")
BUILD_FIX = (ROOT / "jarvis/apply_github_tool_approval_build_fix_v01129.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v0120_preserves_catalog_and_github_helpers():
    assert 'safe_boundary = \'plugin_public_end = text.find("\\\\ndef _mcp_response_json", plugin_public_start)\'' in BUILD_FIX
    assert 'previous_bad_boundary' in BUILD_FIX
    assert 'old_active_boundary' in BUILD_FIX
    assert 'PLUGIN_CATALOG_CACHE_PATH =' in BUILD_FIX
    assert 'def _mcp_response_json(response):' in PATCH
    assert 'def _plugin_url_key(url):' in PATCH
    assert 'async def _fetch_plugin_catalog(force=False):' in PATCH
    assert '@app.get("/api/plugin-catalog")' in PATCH


def test_v0120_developer_backend_is_guarded_and_persistent():
    assert 'DEVELOPER_STATE_PATH = Path("/data/zbrano_developer_mode.json")' in PATCH
    assert 'DEVELOPER_FRONTEND_PATH = Path(__file__).resolve().parent / "static/index.html"' in PATCH
    assert 'class DeveloperModeRequest(BaseModel):' in PATCH
    assert 'def developer_mode_enabled() -> bool:' in PATCH
    assert 'def developer_system_instructions(base: str) -> str:' in PATCH
    assert 'Never bypass, weaken, remove, or silently alter approval rules' in PATCH
    assert '@app.get("/api/developer/status")' in PATCH
    assert '@app.put("/api/developer/mode")' in PATCH
    assert '@app.get("/api/developer/diagnostics")' in PATCH
    assert 'developer_system_instructions(effective_system_instructions())' in PATCH


def test_v0120_diagnostics_cover_working_surfaces():
    for marker in (
        '"/api/plugin-catalog"',
        '"/api/plugins"',
        '"/api/files/shared"',
        '"/api/chats"',
        '"/api/developer/status"',
        '"/api/developer/diagnostics"',
        '"new-chat-button"',
        '"files-tab"',
        '"attach-file"',
        '"plugins-tab"',
        '"entities-tab"',
        '"developer-tab"',
        '"GitHub MCP"',
    ):
        assert marker in PATCH


def test_v0120_frontend_has_developer_mode_and_error_monitor():
    for marker in (
        'id="developer-tab"',
        'id="developer-panel"',
        'id="developer-toggle"',
        'id="developer-run-diagnostics"',
        'zbrano-v0120-developer-mode',
        'window.addEventListener("error"',
        'window.addEventListener("unhandledrejection"',
        'Interface monitor healthy',
        'hideDeveloperPanel',
    ):
        assert marker in PATCH


def test_v0120_build_order_and_version():
    assert 'apply_developer_mode_self_diagnostics_v0120.py' in DOCKER
    assert DOCKER.index('python3 ./apply_catalog_and_plugin_compact_v01131.py') < DOCKER.index('python3 ./apply_developer_mode_self_diagnostics_v0120.py')
    assert DOCKER.index('python3 ./apply_developer_mode_self_diagnostics_v0120.py') < DOCKER.index('validate_inline_js.py ./app/static/index.html')
    assert 'version: "0.12.0"' in CONFIG
