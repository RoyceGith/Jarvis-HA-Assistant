from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_developer_indicator_and_policy_v0126.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v0126_routes_check_and_audit_requests_to_targeted_tool():
    for marker in (
        "check, audit, verify, health, version, or broken-feature requests",
        "Never claim that runtime checks are unavailable before calling this targeted Developer tool",
        "call investigate_zbrano_feature exactly once",
    ):
        assert marker in PATCH


def test_v0126_uses_direct_main_policy_without_weakening_approval():
    assert "direct updates to main; do not create a branch unless the user explicitly requests one" in PATCH
    assert "Every repository mutation, including a direct-main write, commit, or push, remains separately approval-gated" in PATCH


def test_v0126_removes_command_deck_safely():
    for marker in (
        'aria-label="Command deck"',
        "if (voiceRailState)",
        "if (sessionFragment)",
        "if (hudClock)",
        ".hud-layout { grid-template-columns: minmax(0, 1fr); }",
    ):
        assert marker in PATCH


def test_v0126_adds_live_developer_mode_header_indicator():
    for marker in (
        'id="developer-mode-indicator"',
        "Developer Mode Active",
        "modeIndicator.hidden = !enabled",
        "loadStatus().catch",
    ):
        assert marker in PATCH


def test_v0126_softens_chat_markdown_emphasis():
    for marker in (
        ".message.jarvis h2 { font-weight: 650; }",
        ".message.jarvis h3 { font-weight: 600; }",
        ".message.jarvis h4 { font-weight: 600; }",
        ".message.jarvis strong { font-weight: 600; }",
        ".message.jarvis h2 strong",
    ):
        assert marker in PATCH


def test_v0126_build_order_and_version():
    assert DOCKER.index("python3 ./apply_developer_tool_isolation_v0125.py") < DOCKER.index("python3 ./apply_developer_indicator_and_policy_v0126.py")
    assert DOCKER.index("python3 ./apply_developer_indicator_and_policy_v0126.py") < DOCKER.index("validate_inline_js.py ./app/static/index.html")
    assert "COPY apply_developer_indicator_and_policy_v0126.py ./apply_developer_indicator_and_policy_v0126.py" in DOCKER
    assert "./apply_developer_indicator_and_policy_v0126.py ./validate_inline_js.py" in DOCKER
    assert 'version: "0.12.6"' in CONFIG
