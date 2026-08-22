from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_github_tool_approval_policy_v01129.py").read_text(encoding="utf-8")
BUILD_FIX = (ROOT / "jarvis/apply_github_tool_approval_build_fix_v01129.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v01129_github_policy_exposes_read_and_approval_tools():
    assert '_github_discovered_permission' in PATCH
    assert 'return "read_only" if annotations.get("readOnlyHint") is True else "write"' in PATCH
    assert 'permission in {"read_only", "write"}' in PATCH
    assert '"always": {"tool_names": approval_tools}' in PATCH
    assert '"never": {"tool_names": read_tools}' in PATCH
    assert 'approval_tool_count' in PATCH
    assert 'approval required' in PATCH


def test_v01129_chat_handles_native_mcp_approval():
    assert 'PENDING_MCP_APPROVALS' in PATCH
    assert 'mcp_approval_requests' in PATCH
    assert '"type": "mcp_approval_response"' in PATCH
    assert '"approval_request_id": request["id"]' in PATCH
    assert 'Reply **approve** to continue or **cancel** to deny it.' in PATCH
    assert 'previous_response_id' in PATCH


def test_v01129_build_fix_precedes_policy_patch():
    assert 'plugin_public_end = text.find("\\ndef _is_github_plugin", plugin_public_start)' in BUILD_FIX
    assert 'installed_heading = \'<h2>INSTALLED PLUGINS</h2>\'' in BUILD_FIX
    assert 'help_start = text.find("<p>", heading_pos + len(installed_heading))' in BUILD_FIX
    assert 'Only tools declared read-only by the MCP server can be enabled in v0.10.0.' not in BUILD_FIX
    assert 'apply_github_tool_approval_build_fix_v01129.py' in DOCKER
    assert 'apply_github_tool_approval_policy_v01129.py' in DOCKER
    assert DOCKER.index('python3 ./apply_plugin_manager_recovery_v01128.py') < DOCKER.index('python3 ./apply_github_tool_approval_build_fix_v01129.py')
    assert DOCKER.index('python3 ./apply_github_tool_approval_build_fix_v01129.py') < DOCKER.index('python3 ./apply_github_tool_approval_policy_v01129.py')
    assert DOCKER.index('python3 ./apply_github_tool_approval_policy_v01129.py') < DOCKER.index('validate_inline_js.py ./app/static/index.html')


def test_v01129_release_version():
    assert 'version: "0.11.29"' in CONFIG
