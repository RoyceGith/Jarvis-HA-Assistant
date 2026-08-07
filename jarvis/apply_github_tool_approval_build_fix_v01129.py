from pathlib import Path

PATCH = Path("/opt/jarvis/apply_github_tool_approval_policy_v01129.py")


def main() -> None:
    text = PATCH.read_text(encoding="utf-8")

    # plugin_public() is followed by helpers added in v0.11.20 before the
    # v0.11.29 policy helpers are injected. Stop before the FIRST existing
    # helper, not before discover_plugin_tools() or _is_github_plugin().
    # Otherwise _mcp_response_json(), GITHUB_MCP_URL and _plugin_url_key() are
    # deleted while later catalog/GitHub code still references them.
    original_boundary = 'plugin_public_end = text.find("\\n\\nasync def discover_plugin_tools", plugin_public_start)'
    previous_bad_boundary = 'plugin_public_end = text.find("\\ndef _is_github_plugin", plugin_public_start)'
    safe_boundary = 'plugin_public_end = text.find("\\ndef _mcp_response_json", plugin_public_start)'
    if original_boundary in text:
        text = text.replace(original_boundary, safe_boundary, 1)
    elif previous_bad_boundary in text:
        text = text.replace(previous_bad_boundary, safe_boundary, 1)
    elif safe_boundary not in text:
        raise RuntimeError("ZBRANO v0.11.29 build fix missing: plugin_public safe boundary")

    # v0.11.0 inserted the entire plugin catalog backend between
    # active_mcp_tools() and /api/plugins. Narrow the replacement boundary to
    # the catalog block start so only active_mcp_tools() itself is replaced.
    old_active_boundary = '''        "def active_mcp_tools():\\n",
        '@app.get("/api/plugins")',
        active_tools,'''
    new_active_boundary = '''        "def active_mcp_tools():\\n",
        "PLUGIN_CATALOG_CACHE_PATH =",
        active_tools,'''
    if old_active_boundary in text:
        text = text.replace(old_active_boundary, new_active_boundary, 1)
    elif new_active_boundary not in text:
        raise RuntimeError("ZBRANO v0.11.29 build fix missing: active MCP/catalog boundary")

    # Earlier UI patches changed the explanatory text beneath INSTALLED
    # PLUGINS, so v0.11.29 must not depend on the original v0.10.0 sentence.
    old_help_patch = '''    old_help = '<p>Only tools declared read-only by the MCP server can be enabled in v0.10.0.</p>'
    new_help = '<p>Read-only tools run automatically. GitHub tools that can change data remain available but require explicit approval in chat before execution.</p>'
    text = replace_once(text, old_help, new_help, "installed plugins help text")'''
    new_help_patch = '''    new_help = '<p>Read-only tools run automatically. GitHub tools that can change data remain available but require explicit approval in chat before execution.</p>'
    installed_heading = '<h2>INSTALLED PLUGINS</h2>'
    require(text, installed_heading, "installed plugins heading")
    heading_pos = text.find(installed_heading)
    help_start = text.find("<p>", heading_pos + len(installed_heading))
    help_end = text.find("</p>", help_start)
    if help_start < 0 or help_end < 0:
        raise RuntimeError("ZBRANO v0.11.29 patch missing: installed plugins help paragraph")
    help_end += len("</p>")
    text = text[:help_start] + new_help + text[help_end:]'''
    if old_help_patch in text:
        text = text.replace(old_help_patch, new_help_patch, 1)
    elif new_help_patch not in text:
        raise RuntimeError("ZBRANO v0.11.29 build fix missing: installed plugins help matcher")

    if original_boundary in text or previous_bad_boundary in text or safe_boundary not in text:
        raise RuntimeError("ZBRANO v0.11.29 build fix helper preservation verification failed")
    if old_active_boundary in text or new_active_boundary not in text:
        raise RuntimeError("ZBRANO v0.11.29 build fix catalog preservation verification failed")
    if old_help_patch in text or new_help_patch not in text:
        raise RuntimeError("ZBRANO v0.11.29 build fix help verification failed")

    PATCH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
