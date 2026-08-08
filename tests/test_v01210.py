from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_autonomous_automations_v01210.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v01210_adds_organized_automation_workspace():
    for marker in (
        'id="automations-tab"', 'id="automations-panel"', "Suggestion Inbox",
        "Workshop Context Snapshot", "Automation Library", "Safety &amp; Authority",
        "Decision &amp; Activity Timeline",
    ):
        assert marker in PATCH


def test_v01210_persists_structured_automation_drafts():
    for marker in (
        "class AutonomousAutomationRequest", 'AUTOMATION_STORAGE_PATH = Path(',
        '@app.get("/api/automations")', '@app.post("/api/automations")',
        '@app.put("/api/automations/{automation_id}")',
        '@app.delete("/api/automations/{automation_id}")',
    ):
        assert marker in PATCH


def test_v01210_is_honest_about_inactive_engine_without_hardwiring_approvals():
    assert '"continuous_monitoring": False' in PATCH
    assert '"context_reasoning": False' in PATCH
    assert '"automatic_execution": False' in PATCH
    assert "evaluator is not implemented yet" in PATCH
    assert 'pattern="^(observe|suggest|approval_required|autonomous)$"' in PATCH
    assert 'value="selective_autonomy"' in PATCH
    assert "Per-automation authority" in PATCH


def test_v01210_supports_real_entity_context_and_workshop_templates():
    assert 'api("api/ha/entities")' in PATCH
    assert "Workshop comfort advisor" in PATCH
    assert "Workshop air quality advisor" in PATCH
    assert "Workshop departure safety check" in PATCH
    assert "Workshop presence lighting" in PATCH
    assert 'execution_policy:"autonomous"' in PATCH


def test_v01210_integrates_developer_diagnostics():
    assert '"automations": ("/api/automations",)' in PATCH
    assert '"Autonomous Automations API operational"' in PATCH
    assert 'automations: ["automations-tab", "automations-panel", "automation-library"]' in PATCH


def test_v01210_includes_automations_in_safe_backup_and_restore():
    assert '"automations": automation_store()' in PATCH
    assert "Automation backup data is malformed" in PATCH
    assert '_automation_save(automations)' in PATCH


def test_v01210_keeps_plugin_oauth_guidance_current():
    assert "Compatible providers offer Connect and browser authorization" in PATCH
    assert "cannot be installed until ZBRANO supports their authorization flow" in PATCH


def test_v01210_build_order_and_version():
    assert DOCKER.index("python3 ./apply_plugin_oauth_v0129.py") < DOCKER.index("python3 ./apply_autonomous_automations_v01210.py")
    assert DOCKER.index("python3 ./apply_autonomous_automations_v01210.py") < DOCKER.index("validate_inline_js.py ./app/static/index.html")
    assert "COPY apply_autonomous_automations_v01210.py ./apply_autonomous_automations_v01210.py" in DOCKER
    assert "./apply_autonomous_automations_v01210.py ./validate_inline_js.py" in DOCKER
    assert 'version: "0.12.10"' in CONFIG
