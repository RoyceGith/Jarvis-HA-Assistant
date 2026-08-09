import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_provider_approval_flow_v01233.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01233_resolves_the_actual_plugin_provider():
    assert "def mcp_approval_plugin_id" in PATCH
    assert "def mcp_approval_provider" in PATCH
    assert "plugin_registry().get(plugin_id)" in PATCH
    assert 'approval_provider = mcp_approval_provider(requests[0])' in PATCH
    assert "GitHub is requesting permission" not in PATCH


def test_v01233_summarizes_without_dumping_arguments():
    assert "def mcp_approval_summary" in PATCH
    assert "method_match" in PATCH
    assert "path_match" in PATCH
    assert 'lines.append(f"- **{mcp_approval_summary(request)}**")' in PATCH
    assert "arguments[:700]" not in PATCH
    assert "account_id" not in PATCH


def test_v01233_makes_cancellation_terminal():
    assert "if approval_decision is False:" in PATCH
    assert "No action was performed." in PATCH
    assert 'yield stream_event("done", tool_calls=[])' in PATCH
    assert "return" in PATCH
    assert 'state="cancelled"' in PATCH


def test_v01233_keeps_approval_for_capable_tools():
    assert "requests approval for an action its tools can use to change data" in PATCH
    assert "No action has run" in PATCH
    assert "Executing approved {approval_provider} action" in PATCH


def test_v01233_runs_last_and_aligns_release_markers():
    assert "COPY apply_provider_approval_flow_v01233.py" in DOCKER
    assert DOCKER.index("python3 ./apply_web_source_curation_v01232.py") < DOCKER.index("python3 ./apply_provider_approval_flow_v01233.py")
    assert DOCKER.index("python3 ./apply_provider_approval_flow_v01233.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.33"' in CONFIG
    assert MANIFEST["version"] == "0.12.33"
    assert "ZBRANO v0.12.33" in README
    assert 'version="0.12.33"' in PATCH
    assert "HUD 0.12.33" in PATCH
