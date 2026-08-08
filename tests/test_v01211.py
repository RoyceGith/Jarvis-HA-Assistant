from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_workshop_memory_writes_v01211.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v01211_discovers_workshop_memory_tool_catalog():
    assert '"method": "tools/list"' in PATCH
    assert "refresh_workshop_memory_tools" in PATCH
    assert "workshop_memory_function_tools" in PATCH
    assert 'parameters.pop("$schema", None)' in PATCH


def test_v01211_defaults_unknown_tools_to_approval_required():
    assert 'return "read_only" if annotations.get("readOnlyHint") is True else "write"' in PATCH
    assert "workshop_memory_write_calls" in PATCH
    assert "PENDING_WORKSHOP_APPROVALS" in PATCH
    assert "Explicit user approval is required before this Workshop Memory change." in PATCH


def test_v01211_continues_exact_tool_call_after_approval():
    assert "approved_workshop_call_ids" in PATCH
    assert "denied_workshop_call_ids" in PATCH
    assert '"previous_response_id": pending["response_id"]' in PATCH
    assert "Reply **approve** to execute exactly these changes" in PATCH


def test_v01211_adds_complete_ha_metadata_inventory():
    assert '"name": "list_home_assistant_entity_inventory"' in PATCH
    assert 'inventory = await list_ha_entities()' in PATCH
    assert '"entity_id": entity.get("entity_id")' in PATCH
    assert "live state values are intentionally excluded" in PATCH


def test_v01211_keeps_developer_mode_isolated():
    assert "if not developer_mode_enabled():\n        await refresh_workshop_memory_tools()" in PATCH
    assert "developer_runtime_tools()\n        if developer_mode_enabled()" in PATCH


def test_v01211_build_order_and_version():
    assert DOCKER.index("python3 ./apply_autonomous_automations_v01210.py") < DOCKER.index("python3 ./apply_workshop_memory_writes_v01211.py")
    assert DOCKER.index("python3 ./apply_workshop_memory_writes_v01211.py") < DOCKER.index("validate_inline_js.py ./app/static/index.html")
    assert "COPY apply_workshop_memory_writes_v01211.py ./apply_workshop_memory_writes_v01211.py" in DOCKER
    assert "./apply_workshop_memory_writes_v01211.py ./validate_inline_js.py" in DOCKER
    assert 'version: "0.12.11"' in CONFIG
