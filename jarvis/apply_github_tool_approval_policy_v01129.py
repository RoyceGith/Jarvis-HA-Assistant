from pathlib import Path

ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.11.29 patch missing: {label}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    require(text, old, label)
    return text.replace(old, new, 1)


def replace_block(text: str, start_marker: str, end_marker: str, replacement: str, label: str) -> str:
    start = text.find(start_marker)
    end = text.find(end_marker, start)
    if start < 0 or end < 0:
        raise RuntimeError(f"ZBRANO v0.11.29 patch missing: {label}")
    return text[:start] + replacement + text[end:]


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")

    # GitHub policy: expose the complete discovered official GitHub MCP toolset.
    # MCP-declared read-only tools run without approval. Everything else is
    # treated as mutating/ambiguous and requires explicit approval in chat.
    policy_helpers = r'''
def _is_github_plugin(url: str = "", name: str = "") -> bool:
    value = f"{url} {name}".lower()
    return "github" in value or "githubcopilot.com/mcp" in value


def _github_discovered_permission(tool: dict[str, Any]) -> str:
    annotations = tool.get("annotations") or {}
    return "read_only" if annotations.get("readOnlyHint") is True else "write"


def _apply_github_tool_policy(registry: dict[str, Any]) -> bool:
    """Migrate installed GitHub plugins to the v0.11.29 approval policy."""
    changed = False
    for plugin in registry.values():
        if not isinstance(plugin, dict) or not _is_github_plugin(
            str(plugin.get("url") or ""), str(plugin.get("name") or "")
        ):
            continue
        if not plugin.get("enabled"):
            plugin["enabled"] = True
            changed = True
        for tool in plugin.get("tools") or []:
            if not isinstance(tool, dict):
                continue
            permission = str(tool.get("permission") or "blocked")
            # Existing installations do not retain MCP annotations. Preserve
            # known read-only classifications; migrate every other discovered
            # GitHub tool to approval-required instead of blocking it.
            desired = "read_only" if permission == "read_only" else "write"
            if tool.get("permission") != desired:
                tool["permission"] = desired
                changed = True
            if not tool.get("enabled"):
                tool["enabled"] = True
                changed = True
    return changed


'''
    marker = "async def discover_plugin_tools(url,token=\"\"):\n"
    require(text, marker, "plugin discovery function")
    text = text.replace(marker, policy_helpers + marker, 1)

    old_discovery = '        if name: result.append({"name":name[:128],"description":str(tool.get("description") or "")[:1000],"permission":"read_only" if (tool.get("annotations") or {}).get("readOnlyHint") is True else "blocked","enabled":False})'
    new_discovery = '''        if name:
            is_github = _is_github_plugin(url=url)
            permission = (
                _github_discovered_permission(tool)
                if is_github
                else ("read_only" if (tool.get("annotations") or {}).get("readOnlyHint") is True else "blocked")
            )
            result.append({
                "name": name[:128],
                "description": str(tool.get("description") or "")[:1000],
                "permission": permission,
                "enabled": bool(is_github and permission in {"read_only", "write"}),
            })'''
    text = replace_once(text, old_discovery, new_discovery, "tool classification")

    active_tools = r'''def active_mcp_tools():
    active = []
    secrets = plugin_secrets()
    registry = plugin_registry()
    if _apply_github_tool_policy(registry):
        _plugin_save(PLUGIN_REGISTRY_PATH, registry)
    for pid, plugin in registry.items():
        enabled_tools = [
            tool for tool in plugin.get("tools", [])
            if tool.get("enabled") and tool.get("permission") in {"read_only", "write"}
        ]
        if not plugin.get("enabled") or not enabled_tools:
            continue
        read_tools = [tool.get("name") for tool in enabled_tools if tool.get("permission") == "read_only"]
        approval_tools = [tool.get("name") for tool in enabled_tools if tool.get("permission") == "write"]
        allowed = [tool.get("name") for tool in enabled_tools if tool.get("name")]
        item = {
            "type": "mcp",
            "server_label": f"plugin_{pid}"[:64],
            "server_url": plugin["url"],
            "server_description": str(plugin.get("name") or pid)[:200],
            "allowed_tools": allowed,
        }
        if approval_tools and read_tools:
            item["require_approval"] = {
                "always": {"tool_names": approval_tools},
                "never": {"tool_names": read_tools},
            }
        elif approval_tools:
            item["require_approval"] = "always"
        else:
            item["require_approval"] = "never"
        if secrets.get(pid):
            item["authorization"] = secrets[pid]
        active.append(item)
    return active


'''
    text = replace_block(
        text,
        "def active_mcp_tools():\n",
        '@app.get("/api/plugins")',
        active_tools,
        "active MCP tools",
    )

    list_plugins = r'''@app.get("/api/plugins")
async def list_plugins():
    registry = plugin_registry()
    if _apply_github_tool_policy(registry):
        _plugin_save(PLUGIN_REGISTRY_PATH, registry)
    return {"plugins": [plugin_public(pid, plugin) for pid, plugin in registry.items()]}


'''
    text = replace_block(
        text,
        '@app.get("/api/plugins")\nasync def list_plugins():',
        '@app.post("/api/plugins")',
        list_plugins,
        "plugin list endpoint",
    )

    # Refresh keeps the GitHub safe-by-default policy while preserving the old
    # manual behavior for arbitrary third-party MCP servers.
    old_refresh = '''        for t in tools:
            previous=old.get(t["name"],{})
            if previous.get("permission")=="read_only": t["permission"]="read_only";t["enabled"]=bool(previous.get("enabled"))'''
    new_refresh = '''        for t in tools:
            previous = old.get(t["name"], {})
            if _is_github_plugin(str(p.get("url") or ""), str(p.get("name") or "")):
                t["enabled"] = t.get("permission") in {"read_only", "write"}
            elif previous.get("permission") == "read_only":
                t["permission"] = "read_only"
                t["enabled"] = bool(previous.get("enabled"))'''
    text = replace_once(text, old_refresh, new_refresh, "plugin refresh policy")

    old_update_guard = '    if request.permission!="read_only" or tool.get("permission")!="read_only": raise HTTPException(status_code=400,detail="Only MCP-declared read-only tools can be enabled")'
    new_update_guard = '''    declared = str(tool.get("permission") or "blocked")
    if declared not in {"read_only", "write"}:
        raise HTTPException(status_code=400, detail="Blocked tools cannot be enabled")
    if request.permission != declared:
        raise HTTPException(status_code=400, detail="Tool permission classification cannot be changed from the UI")'''
    text = replace_once(text, old_update_guard, new_update_guard, "tool update permission guard")

    # v0.11.28 counted only no-approval read tools. Count every enabled tool
    # that is actually exposed to chat and report the approval-required subset.
    plugin_public_start = text.find("def plugin_public(pid,p):")
    plugin_public_end = text.find("\n\nasync def discover_plugin_tools", plugin_public_start)
    if plugin_public_start < 0 or plugin_public_end < 0:
        raise RuntimeError("ZBRANO v0.11.29 patch missing: plugin_public bounds")
    plugin_public = r'''def plugin_public(pid,p):
    tools = list(p.get("tools") or [])
    enabled_tools = [
        tool for tool in tools
        if tool.get("enabled") and tool.get("permission") in {"read_only", "write"}
    ]
    enabled_tool_count = len(enabled_tools)
    approval_tool_count = sum(1 for tool in enabled_tools if tool.get("permission") == "write")
    return {
        "id": pid,
        "name": p.get("name", pid),
        "url": p.get("url", ""),
        "enabled": bool(p.get("enabled")),
        "healthy": bool(p.get("healthy")),
        "last_error": p.get("last_error"),
        "last_checked": p.get("last_checked"),
        "has_secret": bool(plugin_secrets().get(pid)),
        "tools": tools,
        "enabled_tool_count": enabled_tool_count,
        "approval_tool_count": approval_tool_count,
        "available_to_chat": bool(p.get("enabled") and enabled_tool_count),
    }'''
    text = text[:plugin_public_start] + plugin_public + text[plugin_public_end:]

    # Store pending native MCP approvals between chat turns. Approval responses
    # are linked with previous_response_id, so the user can simply reply
    # "approve" or "cancel" in the normal chat UI.
    approval_helpers = r'''
PENDING_MCP_APPROVALS: dict[str, dict[str, Any]] = {}


def mcp_approval_requests(response: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item for item in response.get("output", [])
        if item.get("type") == "mcp_approval_request"
    ]


def mcp_approval_decision(message: str) -> bool | None:
    normalized = " ".join(message.strip().lower().split())
    if normalized in {"approve", "approved", "confirm", "yes", "yes approve", "proceed", "go ahead"}:
        return True
    if normalized in {"cancel", "deny", "denied", "no", "reject", "do not", "don't"}:
        return False
    return None


def mcp_approval_prompt(requests: list[dict[str, Any]]) -> str:
    lines = ["GitHub is requesting permission for an action that may change data:"]
    for request in requests[:5]:
        name = str(request.get("name") or "unknown tool")
        arguments = str(request.get("arguments") or "{}")
        if len(arguments) > 700:
            arguments = arguments[:700] + "…"
        lines.append(f"- `{name}` with `{arguments}`")
    if len(requests) > 5:
        lines.append(f"- …and {len(requests) - 5} more approval request(s)")
    lines.append("Reply **approve** to continue or **cancel** to deny it.")
    return "\n".join(lines)


'''
    stream_marker = "async def _run_jarvis_stream_events(message: str, session_id: str = \"default\") -> AsyncIterator[bytes]:\n"
    require(text, stream_marker, "stream event function")
    text = text.replace(stream_marker, approval_helpers + stream_marker, 1)

    # Handle a user's approval/denial as a continuation of the exact Responses
    # API turn that emitted the mcp_approval_request.
    stream_start = '''async def _run_jarvis_stream_events(message: str, session_id: str = "default") -> AsyncIterator[bytes]:
    yield stream_event("status", message="Thinking…")

    local_result = await try_local_ha_route(message, session_id)'''
    stream_replacement = '''async def _run_jarvis_stream_events(message: str, session_id: str = "default") -> AsyncIterator[bytes]:
    yield stream_event("status", message="Thinking…")

    pending_approval = PENDING_MCP_APPROVALS.get(session_id)
    approval_decision = mcp_approval_decision(message)
    if pending_approval and approval_decision is not None:
        PENDING_MCP_APPROVALS.pop(session_id, None)
        yield stream_event(
            "status",
            message="Executing approved GitHub action…" if approval_decision else "Denying GitHub action…",
        )
        continued_response: dict[str, Any] | None = None
        emitted_continuation_text = False
        approval_input = [
            {
                "type": "mcp_approval_response",
                "approval_request_id": request["id"],
                "approve": approval_decision,
                "reason": "Approved by user in ZBRANO chat" if approval_decision else "Denied by user in ZBRANO chat",
            }
            for request in pending_approval["requests"]
        ]
        async for event in stream_openai_response(
            {
                "model": OPENAI_MODEL,
                "instructions": effective_system_instructions(),
                "previous_response_id": pending_approval["response_id"],
                "input": approval_input,
                "tools": WORKSHOP_TOOLS + active_mcp_tools(),
                "tool_choice": "auto",
            }
        ):
            event_type = event.get("type")
            if event_type == "response.output_text.delta":
                if not emitted_continuation_text:
                    yield stream_event("status", message="Responding…")
                    emitted_continuation_text = True
                delta = event.get("delta", "")
                if delta:
                    yield stream_event("delta", text=delta)
            elif event_type == "response.completed":
                continued_response = event.get("response")
            elif event_type in {"response.failed", "error"}:
                raise OpenAIError(
                    event.get("message")
                    or event.get("error", {}).get("message")
                    or "OpenAI MCP approval continuation failed"
                )
        if continued_response is None:
            raise OpenAIError("OpenAI approval continuation ended without response.completed")
        followup_approvals = mcp_approval_requests(continued_response)
        if followup_approvals:
            PENDING_MCP_APPROVALS[session_id] = {
                "response_id": continued_response["id"],
                "requests": followup_approvals,
            }
            prompt = mcp_approval_prompt(followup_approvals)
            yield stream_event("status", message="Permission required…")
            yield stream_event("delta", text=prompt)
            yield stream_event("done", tool_calls=[])
            return
        if not emitted_continuation_text:
            final_text = response_text(continued_response)
            if final_text:
                yield stream_event("status", message="Responding…")
                yield stream_event("delta", text=final_text)
        yield stream_event("done", tool_calls=[])
        return

    local_result = await try_local_ha_route(message, session_id)'''
    text = replace_once(text, stream_start, stream_replacement, "approval continuation entry")

    # Catch native MCP approval requests from both the initial response and any
    # subsequent local-function-tool round before the generic no-text error.
    initial_completed = '''    if response is None:
        raise OpenAIError("OpenAI stream ended without response.completed")

    if emitted_initial_text and not function_calls(response):'''
    initial_replacement = '''    if response is None:
        raise OpenAIError("OpenAI stream ended without response.completed")

    approval_requests = mcp_approval_requests(response)
    if approval_requests:
        PENDING_MCP_APPROVALS[session_id] = {
            "response_id": response["id"],
            "requests": approval_requests,
        }
        prompt = mcp_approval_prompt(approval_requests)
        yield stream_event("status", message="Permission required…")
        yield stream_event("delta", text=prompt)
        yield stream_event("done", tool_calls=audit)
        return

    if emitted_initial_text and not function_calls(response):'''
    text = replace_once(text, initial_completed, initial_replacement, "initial MCP approval detection")

    followup_completed = '''        if streamed_response is None:
            raise OpenAIError("OpenAI stream ended without response.completed")

        if emitted_text and not function_calls(streamed_response):'''
    followup_replacement = '''        if streamed_response is None:
            raise OpenAIError("OpenAI stream ended without response.completed")

        approval_requests = mcp_approval_requests(streamed_response)
        if approval_requests:
            PENDING_MCP_APPROVALS[session_id] = {
                "response_id": streamed_response["id"],
                "requests": approval_requests,
            }
            prompt = mcp_approval_prompt(approval_requests)
            yield stream_event("status", message="Permission required…")
            yield stream_event("delta", text=prompt)
            yield stream_event("done", tool_calls=audit)
            return

        if emitted_text and not function_calls(streamed_response):'''
    text = replace_once(text, followup_completed, followup_replacement, "follow-up MCP approval detection")

    text = text.replace('version="0.11.28"', 'version="0.11.29"')
    text = text.replace('"version": "0.11.28"', '"version": "0.11.29"')
    MAIN.write_text(text, encoding="utf-8")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    old_tool = '<input type="checkbox" data-p="${esc(p.id)}" data-t="${esc(t.name)}" ${t.enabled?"checked":""} ${t.permission!=="read_only"?"disabled":""}>'
    new_tool = '<input type="checkbox" data-p="${esc(p.id)}" data-t="${esc(t.name)}" data-permission="${esc(t.permission)}" ${t.enabled?"checked":""} ${t.permission==="blocked"?"disabled":""}>'
    text = replace_once(text, old_tool, new_tool, "plugin tool checkbox policy")

    old_badge = '<span class="plugin-badge ${esc(t.permission)}">${esc(t.permission)}</span>'
    new_badge = '<span class="plugin-badge ${esc(t.permission)}">${t.permission==="write"?"approval required":esc(t.permission)}</span>'
    text = replace_once(text, old_badge, new_badge, "plugin tool approval badge")

    old_update = 'body:JSON.stringify({enabled:c.checked,permission:"read_only"})'
    new_update = 'body:JSON.stringify({enabled:c.checked,permission:c.dataset.permission||"blocked"})'
    text = replace_once(text, old_update, new_update, "plugin tool update permission")

    old_status = '${p.enabled?"Enabled":"Installed · disabled"} · ${p.available_to_chat?"Available to chat":"Not available to chat"} · ${p.enabled_tool_count||0} tool${(p.enabled_tool_count||0)===1?"":"s"} enabled · ${p.healthy?"Healthy":"Unhealthy"} · token ${p.has_secret?"stored":"not set"}'
    new_status = '${p.enabled?"Enabled":"Installed · disabled"} · ${p.available_to_chat?"Available to chat":"Not available to chat"} · ${p.enabled_tool_count||0} tool${(p.enabled_tool_count||0)===1?"":"s"} enabled · ${p.approval_tool_count||0} require approval · ${p.healthy?"Healthy":"Unhealthy"} · token ${p.has_secret?"stored":"not set"}'
    text = replace_once(text, old_status, new_status, "plugin approval status")

    old_help = '<p>Only tools declared read-only by the MCP server can be enabled in v0.10.0.</p>'
    new_help = '<p>Read-only tools run automatically. GitHub tools that can change data remain available but require explicit approval in chat before execution.</p>'
    text = replace_once(text, old_help, new_help, "installed plugins help text")

    text = text.replace("HUD 0.11.28", "HUD 0.11.29")
    INDEX.write_text(text, encoding="utf-8")


def verify() -> None:
    main = MAIN.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    missing = []

    required_main = (
        "_github_discovered_permission",
        "_apply_github_tool_policy",
        'permission in {"read_only", "write"}',
        '"always": {"tool_names": approval_tools}',
        '"never": {"tool_names": read_tools}',
        "PENDING_MCP_APPROVALS",
        '"type": "mcp_approval_response"',
        '"approval_request_id": request["id"]',
        "mcp_approval_requests(response)",
        'version="0.11.29"',
    )
    required_index = (
        'data-permission="${esc(t.permission)}"',
        'approval required',
        'require approval',
        'permission:c.dataset.permission||"blocked"',
        "HUD 0.11.29",
    )
    for marker in required_main:
        if marker not in main:
            missing.append(marker)
    for marker in required_index:
        if marker not in index:
            missing.append(marker)

    if 'request.permission!="read_only"' in main:
        missing.append("legacy read-only-only tool guard")
    if 't.permission!=="read_only"?"disabled"' in index:
        missing.append("legacy write-tool UI block")

    if missing:
        raise RuntimeError(
            "ZBRANO v0.11.29 verification failed: " + ", ".join(missing)
        )


if __name__ == "__main__":
    patch_main()
    patch_index()
    verify()
