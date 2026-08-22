import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_native_approval_and_activity_order_v01234.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01234_forbids_ai_generated_preapproval_prompts():
    assert "never write, simulate" in PATCH
    assert "manual preflight approval question" in PATCH
    assert "call the requested tool exactly once" in PATCH
    assert "platform-native MCP approval gate" in PATCH


def test_v01234_protects_native_approval_boundaries():
    assert "Calling an" in PATCH
    assert "approval-gated tool is therefore the required way to request approval" in PATCH
    assert "Never expose raw tool arguments" in PATCH
    assert "when a native approval is pending" in PATCH
    assert "do not propose another approval" in PATCH


def test_v01234_swaps_tool_and_completion_rows_without_removing_them():
    assert "ai_start = frontend.find" in PATCH
    assert "tool_start = frontend.find" in PATCH
    assert "frontend[:ai_start] + tool_block + ai_block" in PATCH
    assert "activity rows were not swapped" in PATCH
    assert 'id="tool-timeline"' in PATCH
    assert 'id="ai-activity"' in PATCH


def test_v01234_runs_last_and_aligns_release_markers():
    assert "COPY apply_native_approval_and_activity_order_v01234.py" in DOCKER
    assert DOCKER.index("python3 ./apply_provider_approval_flow_v01233.py") < DOCKER.index("python3 ./apply_native_approval_and_activity_order_v01234.py")
    assert DOCKER.index("python3 ./apply_native_approval_and_activity_order_v01234.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.34"' in CONFIG
    assert MANIFEST["version"] == "0.12.34"
    assert "ZBRANO v0.12.34" in README
    assert 'version="0.12.34"' in PATCH
    assert "HUD 0.12.34" in PATCH
