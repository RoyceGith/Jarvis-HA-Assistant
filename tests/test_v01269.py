import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_grinder_incident_routing_v01269.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_grinder_failure_prompts_get_only_local_grinder_tools():
    assert "def is_grinder_diagnostic_intent(" in PATCH
    assert '"grinder" not in normalized' in PATCH
    for term in ("incident", "freeze", "frozen", "stuck", "reboot", "telemetry", "hx711"):
        assert f'"{term}"' in PATCH
    assert "return grinder_priority_tools()" in PATCH
    assert "return list(GRINDER_MONITOR_TOOLS)" in PATCH


def test_grinder_routing_does_not_break_developer_isolation():
    developer = PATCH.index("if developer_mode_enabled():")
    grinder = PATCH.index("if is_grinder_diagnostic_intent(message):", developer)
    assert developer < grinder
    assert "return developer_runtime_tools() + developer_mcp_tools()" in PATCH


def test_incident_instruction_requires_runtime_evidence():
    assert "GRINDER DIAGNOSTIC INTENT IS ACTIVE" in PATCH
    assert "call get_grinder_incident with that exact" in PATCH
    assert "Analyze the bounded pre_failure_window" in PATCH
    assert "rather than asking the user for an export" in PATCH
    assert "later POWER ON reset as operator-caused" in PATCH
    assert "Clearly separate" in PATCH
    assert "measured evidence from inference" in PATCH


def test_v01269_release_chain_and_markers():
    assert "COPY apply_grinder_incident_routing_v01269.py" in DOCKER
    assert DOCKER.index("python3 ./apply_workshop_write_reconciliation_v01268.py") < DOCKER.index(
        "python3 ./apply_grinder_incident_routing_v01269.py"
    )
    assert DOCKER.index("python3 ./apply_grinder_incident_routing_v01269.py") < DOCKER.index(
        "python3 ./validate_release_manifest.py"
    )
    assert 'version: "0.12.69"' in CONFIG
    assert MANIFEST["version"] == "0.12.69"
    assert "ZBRANO v0.12.69" in README
    assert 'version="0.12.69"' in PATCH
    assert "HUD 0.12.69" in PATCH
