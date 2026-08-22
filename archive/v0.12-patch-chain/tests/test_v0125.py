from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_developer_tool_isolation_v0125.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v0125_uses_dynamic_runtime_version():
    assert "expected_version = str(app.version)" in PATCH
    assert 'version == expected_version' in PATCH
    assert 'expected {expected_version}' in PATCH


def test_v0125_isolates_developer_tools_from_workshop_and_other_plugins():
    for marker in (
        "def developer_mcp_tools()",
        "def runtime_chat_tools()",
        "return developer_runtime_tools() + developer_mcp_tools()",
        "if developer_mode_enabled()",
        "allowed_function_tools = developer_runtime_tools() if developer_mode_enabled() else WORKSHOP_TOOLS",
        "None if developer_mode_enabled() else await try_local_ha_route",
        "_is_github_plugin(",
    ):
        assert marker in PATCH


def test_v0125_investigation_is_feature_scoped_and_bounded():
    for marker in (
        "async def _targeted_developer_diagnostics(feature_key: str)",
        "never invoke the broad diagnostic suite",
        "timeout=8.0",
        "timeout=20.0",
        '"broad_diagnostics_run": False',
        "call investigate_zbrano_feature exactly once",
        "12 if developer_mode_enabled() else 5",
    ):
        assert marker in PATCH


def test_v0125_shows_response_activity_and_wraps_chat_composer():
    for marker in (
        '<textarea id="message"',
        'id="ai-activity"',
        'id="ai-response-timer"',
        "function startResponseActivity(",
        "function markFirstResponse(",
        "function resizeComposer(",
        'event.key === "Enter" && !event.shiftKey',
        'setResponseActivity(statusText)',
        "finishResponseActivity(",
        "overflow-wrap: anywhere",
    ):
        assert marker in PATCH


def test_v0125_build_order_and_version():
    assert DOCKER.index("python3 ./apply_investigation_engine_v0124.py") < DOCKER.index("python3 ./apply_developer_tool_isolation_v0125.py")
    assert DOCKER.index("python3 ./apply_developer_tool_isolation_v0125.py") < DOCKER.index("validate_inline_js.py ./app/static/index.html")
    assert "COPY apply_developer_tool_isolation_v0125.py ./apply_developer_tool_isolation_v0125.py" in DOCKER
    assert "./apply_developer_tool_isolation_v0125.py ./validate_inline_js.py" in DOCKER
    assert 'version: "0.12.5"' in CONFIG
