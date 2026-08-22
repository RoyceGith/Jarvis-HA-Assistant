from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_investigation_engine_v0124.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v0124_has_targeted_feature_registry():
    for feature in (
        "attachments",
        "shared_files",
        "new_chat",
        "plugin_catalog",
        "plugins",
        "entities",
        "settings",
        "voice",
        "workshop_memory",
        "developer",
    ):
        assert f'"{feature}"' in PATCH
    assert "DEVELOPER_FEATURE_SPECS" in PATCH
    assert "matches.sort(reverse=True)" in PATCH


def test_v0124_exposes_read_only_investigation_to_chat_only_in_developer_mode():
    for marker in (
        "def developer_runtime_tools()",
        "if not developer_mode_enabled():",
        '"name": "investigate_zbrano_feature"',
        "WORKSHOP_TOOLS + developer_runtime_tools() + active_mcp_tools()",
        'elif name == "investigate_zbrano_feature":',
    ):
        assert marker in PATCH


def test_v0124_does_not_treat_green_diagnostics_as_bug_resolution():
    for marker in (
        'status = "inconclusive"',
        "Do not close the issue from green diagnostics alone",
        '"automatic_changes_made": False',
        '"repository_writes_require_approval": True',
        "Never invent successful reproduction",
    ):
        assert marker in PATCH


def test_v0124_ui_collects_browser_runtime_evidence():
    for marker in (
        'id="developer-investigate"',
        'id="developer-symptom"',
        'id="zbrano-v0124-investigation-engine"',
        "collectBrowserEvidence",
        "runtimeErrors",
        "lastActionOk",
        "lastUploadOk",
        'fetch("api/developer/investigate"',
    ):
        assert marker in PATCH


def test_v0124_api_and_version_build_order():
    assert '@app.post("/api/developer/investigate")' in PATCH
    assert '@app.get("/api/developer/features")' in PATCH
    assert DOCKER.index("python3 ./apply_shared_files_and_diagnostics_v0123.py") < DOCKER.index("python3 ./apply_investigation_engine_v0124.py")
    assert DOCKER.index("python3 ./apply_investigation_engine_v0124.py") < DOCKER.index("validate_inline_js.py ./app/static/index.html")
    assert "COPY apply_investigation_engine_v0124.py ./apply_investigation_engine_v0124.py" in DOCKER
    assert "./apply_investigation_engine_v0124.py ./validate_inline_js.py" in DOCKER
    assert 'version: "0.12.4"' in CONFIG
