import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_gmail_direct_v01257.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_gmail_direct_uses_standard_api_and_not_preview_tools():
    assert "https://gmail.googleapis.com/gmail/v1/users/me" in PATCH
    assert "https://accounts.google.com/o/oauth2/v2/auth" in PATCH
    assert "https://oauth2.googleapis.com/token" in PATCH
    assert "if pid == _gmail_plugin_id()" in PATCH
    assert "Never expose the Developer Preview remote MCP" in PATCH
    assert "tools = gmail_direct_tool_records()" in PATCH


def test_gmail_direct_is_bounded_and_treats_mail_as_untrusted():
    assert "GMAIL_DIRECT_MAX_RESULTS = 10" in PATCH
    assert "GMAIL_DIRECT_MAX_MESSAGES = 20" in PATCH
    assert "GMAIL_DIRECT_MAX_BODY_CHARS = 40000" in PATCH
    assert "UNTRUSTED EMAIL CONTENT" in PATCH
    assert '"attachments": "not downloaded"' in PATCH
    assert "follow_redirects=False" in PATCH
    assert "Gmail API redirects are blocked" in PATCH


def test_drafts_require_approval_and_cannot_inherit_task_approval():
    assert 'GMAIL_DIRECT_WRITE_TOOLS = {"gmail_direct_create_draft"}' in PATCH
    assert "gmail_direct_write_calls(calls) or not workshop_memory_task_approval_active" in PATCH
    assert "not pending_has_gmail_write(pending_workshop)" in PATCH
    assert "The message will remain a draft and will not be sent" in PATCH
    assert '"sent": False' in PATCH
    assert "safe_tool_audit_arguments(name, arguments)" in PATCH
    assert "<redacted draft body:" in PATCH


def test_individual_gmail_tools_respect_plugin_toggles():
    assert "enabled_names = {" in PATCH
    assert 'if tool.get("enabled") and tool.get("permission") in {"read_only", "write"}' in PATCH
    assert 'return [tool for tool in tools if tool["name"] in enabled_names]' in PATCH


def test_no_dangerous_gmail_tools_are_exposed():
    tool_names = {
        "gmail_direct_list_labels",
        "gmail_direct_search",
        "gmail_direct_read_thread",
        "gmail_direct_create_draft",
    }
    assert all(name in PATCH for name in tool_names)
    assert "gmail_direct_send" not in PATCH
    assert "gmail_direct_delete" not in PATCH
    assert "gmail_direct_trash" not in PATCH
    assert "gmail_direct_modify_labels" not in PATCH


def test_v01257_gmail_direct_release_chain_and_markers():
    assert "COPY apply_gmail_direct_v01257.py ./apply_gmail_direct_v01257.py" in DOCKER
    assert DOCKER.index("python3 ./apply_gmail_oauth_least_privilege_v01256.py") < DOCKER.index("python3 ./apply_gmail_direct_v01257.py")
    assert DOCKER.index("python3 ./apply_gmail_direct_v01257.py") < DOCKER.index("python3 ./apply_plugin_settings_visibility_v01258.py")
    assert 'version="0.12.57"' in PATCH
    assert "HUD 0.12.57" in PATCH
