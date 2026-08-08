from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.11 patch missing: {label}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    require(text, old, label)
    return text.replace(old, new, 1)


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")

    instruction_marker = '''    {
        "type": "function",
        "name": "save_general_instruction",'''
    require(text, instruction_marker, "Home Assistant inventory tool insertion")
    inventory_tool = r'''    {
        "type": "function",
        "name": "list_home_assistant_entity_inventory",
        "description": (
            "Return the complete Home Assistant entity inventory for documentation, "
            "including entity IDs and stable metadata but excluding live state values. "
            "Use this when the user asks to inventory or document all HA entities."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "strict": True,
    },
'''
    text = text.replace(instruction_marker, inventory_tool + instruction_marker, 1)

    discovery_marker = "async def probe_workshop_memory_endpoint(endpoint_url: str) -> tuple[bool, float, str | None]:\n"
    require(text, discovery_marker, "Workshop Memory discovery insertion")
    discovery = r'''WORKSHOP_DYNAMIC_TOOLS: dict[str, dict[str, Any]] = {}
WORKSHOP_DYNAMIC_TOOLS_REFRESHED_AT = 0.0
WORKSHOP_DYNAMIC_TOOLS_TTL = 60.0


async def _list_workshop_memory_endpoint_tools(endpoint_url: str) -> list[dict[str, Any]]:
    client = await get_mcp_client()
    initialize_id = 1
    init_messages, session_id = await _mcp_post(
        client,
        endpoint_url,
        {
            "jsonrpc": "2.0",
            "id": initialize_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {
                    "name": "jarvis-workshop-assistant",
                    "version": "0.12.11",
                },
            },
        },
    )
    _find_result(init_messages, initialize_id)
    await _mcp_post(
        client,
        endpoint_url,
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        session_id,
    )
    list_id = 2
    list_messages, _ = await _mcp_post(
        client,
        endpoint_url,
        {"jsonrpc": "2.0", "id": list_id, "method": "tools/list", "params": {}},
        session_id,
    )
    tools = _find_result(list_messages, list_id).get("tools") or []
    return [tool for tool in tools if isinstance(tool, dict)]


def _workshop_tool_permission(tool: dict[str, Any]) -> str:
    annotations = tool.get("annotations") or {}
    return "read_only" if annotations.get("readOnlyHint") is True else "write"


async def refresh_workshop_memory_tools(force: bool = False) -> dict[str, dict[str, Any]]:
    """Discover local MCP tools; unknown or unannotated tools default to write."""
    global WORKSHOP_DYNAMIC_TOOLS, WORKSHOP_DYNAMIC_TOOLS_REFRESHED_AT
    if (
        not force
        and WORKSHOP_DYNAMIC_TOOLS_REFRESHED_AT
        and time.monotonic() - WORKSHOP_DYNAMIC_TOOLS_REFRESHED_AT < WORKSHOP_DYNAMIC_TOOLS_TTL
    ):
        return WORKSHOP_DYNAMIC_TOOLS
    try:
        endpoint_url = await select_workshop_memory_endpoint()
        discovered = await _list_workshop_memory_endpoint_tools(endpoint_url)
    except (MCPError, httpx.HTTPError, OSError, RuntimeError, ValueError):
        return WORKSHOP_DYNAMIC_TOOLS

    static_names = {tool.get("name") for tool in WORKSHOP_TOOLS}
    catalog: dict[str, dict[str, Any]] = {}
    for tool in discovered:
        name = str(tool.get("name") or "").strip()
        if (
            not name
            or len(name) > 64
            or not re.fullmatch(r"[A-Za-z0-9_-]+", name)
            or name in static_names
        ):
            continue
        parameters = tool.get("inputSchema")
        if not isinstance(parameters, dict) or parameters.get("type") != "object":
            parameters = {"type": "object", "properties": {}}
        parameters = dict(parameters)
        parameters.pop("$schema", None)
        catalog[name] = {
            "name": name,
            "description": str(tool.get("description") or f"Workshop Memory tool: {name}")[:1000],
            "parameters": parameters,
            "permission": _workshop_tool_permission(tool),
        }
    WORKSHOP_DYNAMIC_TOOLS = catalog
    WORKSHOP_DYNAMIC_TOOLS_REFRESHED_AT = time.monotonic()
    return catalog


def workshop_memory_function_tools() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["parameters"],
            "strict": False,
        }
        for tool in WORKSHOP_DYNAMIC_TOOLS.values()
    ]


def workshop_memory_tool_permission(name: str) -> str | None:
    tool = WORKSHOP_DYNAMIC_TOOLS.get(name)
    return str(tool.get("permission")) if tool else None


'''
    text = text.replace(discovery_marker, discovery + discovery_marker, 1)

    execute_signature = '''async def execute_tool_calls(
    calls: list[dict[str, Any]],
    audit: list[dict[str, Any]],
    session_id: str = "default",
) -> list[dict[str, Any]]:
    tool_outputs: list[dict[str, Any]] = []
    allowed_function_tools = developer_runtime_tools() if developer_mode_enabled() else WORKSHOP_TOOLS
    allowed_names = {tool["name"] for tool in allowed_function_tools}'''
    execute_replacement = '''async def execute_tool_calls(
    calls: list[dict[str, Any]],
    audit: list[dict[str, Any]],
    session_id: str = "default",
    approved_workshop_call_ids: set[str] | None = None,
    denied_workshop_call_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    tool_outputs: list[dict[str, Any]] = []
    approved_workshop_call_ids = approved_workshop_call_ids or set()
    denied_workshop_call_ids = denied_workshop_call_ids or set()
    allowed_function_tools = (
        developer_runtime_tools()
        if developer_mode_enabled()
        else WORKSHOP_TOOLS + workshop_memory_function_tools()
    )
    allowed_names = {tool["name"] for tool in allowed_function_tools}'''
    text = replace_once(text, execute_signature, execute_replacement, "tool execution approval parameters")

    execution_guard = '''        if name not in allowed_names:
            result: dict[str, Any] = {"error": f"Tool is not allowed: {name}"}
        else:
            try:
                if name == "find_home_assistant_entities":'''
    execution_replacement = '''        permission = workshop_memory_tool_permission(name)
        if name not in allowed_names:
            result: dict[str, Any] = {"error": f"Tool is not allowed: {name}"}
        elif permission == "write" and call_id in denied_workshop_call_ids:
            result = {"error": "User denied this Workshop Memory change."}
        elif permission == "write" and call_id not in approved_workshop_call_ids:
            result = {"error": "Explicit user approval is required before this Workshop Memory change."}
        else:
            try:
                if name == "find_home_assistant_entities":'''
    text = replace_once(text, execution_guard, execution_replacement, "write execution guard")

    state_branch = '''                elif name == "get_home_assistant_state":
                    result = await ha_get_state(arguments["entity_id"])'''
    inventory_branch = '''                elif name == "get_home_assistant_state":
                    result = await ha_get_state(arguments["entity_id"])
                elif name == "list_home_assistant_entity_inventory":
                    inventory = await list_ha_entities()
                    entities = inventory.get("entities") or []
                    result = {
                        "count": len(entities),
                        "entities": [
                            {
                                "entity_id": entity.get("entity_id"),
                                "friendly_name": entity.get("friendly_name"),
                                "domain": entity.get("domain"),
                                "device_class": entity.get("device_class"),
                                "unit": entity.get("unit"),
                            }
                            for entity in entities
                        ],
                        "note": "Inventory metadata only; live state values are intentionally excluded.",
                    }'''
    text = replace_once(text, state_branch, inventory_branch, "Home Assistant inventory execution")

    runtime_return = '''    return WORKSHOP_TOOLS + active_mcp_tools()'''
    runtime_replacement = '''    return WORKSHOP_TOOLS + workshop_memory_function_tools() + active_mcp_tools()'''
    text = replace_once(text, runtime_return, runtime_replacement, "runtime Workshop Memory tools")

    system_marker = '''Workshop Memory remains review-controlled: do not claim to edit permanent
project notes unless an explicit approved workflow has completed.'''
    system_replacement = '''Workshop Memory remains review-controlled. Its MCP tool catalog is discovered at
runtime. You may use advertised tools to create projects or templates, update
project progress, and add notes when the user requests it. Every discovered
tool not explicitly annotated read-only requires an approval prompt and must
not execute until the user approves the exact tool and arguments. Never claim
a permanent write completed until its tool result confirms success. Do not use
save_general_instruction as a substitute for a project note.'''
    text = replace_once(text, system_marker, system_replacement, "Workshop Memory write policy")

    approval_marker = "PENDING_MCP_APPROVALS: dict[str, dict[str, Any]] = {}\n"
    require(text, approval_marker, "Workshop Memory approval helpers")
    approval_helpers = r'''PENDING_WORKSHOP_APPROVALS: dict[str, dict[str, Any]] = {}


def workshop_memory_write_calls(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        call for call in calls
        if workshop_memory_tool_permission(str(call.get("name") or "")) == "write"
    ]


def workshop_memory_approval_prompt(calls: list[dict[str, Any]]) -> str:
    writes = workshop_memory_write_calls(calls)
    lines = ["Workshop Memory is requesting permission to change permanent project data:"]
    for call in writes[:5]:
        name = str(call.get("name") or "unknown tool")
        arguments = str(call.get("arguments") or "{}")
        if len(arguments) > 900:
            arguments = arguments[:900] + "…"
        lines.append(f"- `{name}` with `{arguments}`")
    if len(writes) > 5:
        lines.append(f"- …and {len(writes) - 5} more change(s)")
    lines.append("Reply **approve** to execute exactly these changes or **cancel** to deny them.")
    return "\n".join(lines)


def store_workshop_memory_approval(
    session_id: str,
    response_id: str,
    calls: list[dict[str, Any]],
) -> str:
    PENDING_WORKSHOP_APPROVALS[session_id] = {
        "response_id": response_id,
        "calls": calls,
    }
    return workshop_memory_approval_prompt(calls)


async def continue_workshop_memory_approval(
    pending: dict[str, Any],
    approved: bool,
    session_id: str,
) -> dict[str, Any]:
    audit: list[dict[str, Any]] = []
    write_ids = {
        str(call.get("call_id") or "")
        for call in workshop_memory_write_calls(pending["calls"])
    }
    tool_outputs = await execute_tool_calls(
        pending["calls"],
        audit,
        session_id,
        approved_workshop_call_ids=write_ids if approved else set(),
        denied_workshop_call_ids=set() if approved else write_ids,
    )
    response = await create_openai_response({
        "model": active_agent_model(),
        **agent_reasoning_payload(),
        "instructions": developer_system_instructions(effective_system_instructions()),
        "previous_response_id": pending["response_id"],
        "input": tool_outputs,
        "tools": runtime_chat_tools(),
        "tool_choice": "auto",
    })
    for _round in range(6):
        native_approvals = mcp_approval_requests(response)
        if native_approvals:
            PENDING_MCP_APPROVALS[session_id] = {
                "response_id": response["id"],
                "requests": native_approvals,
            }
            return {"reply": mcp_approval_prompt(native_approvals), "tool_calls": audit}
        calls = function_calls(response)
        if not calls:
            reply = response_text(response)
            if not reply:
                reply = "Workshop Memory change completed." if approved else "Workshop Memory change was denied."
            return {"reply": reply, "tool_calls": audit}
        if workshop_memory_write_calls(calls):
            prompt = store_workshop_memory_approval(session_id, response["id"], calls)
            return {"reply": prompt, "tool_calls": audit}
        tool_outputs = await execute_tool_calls(calls, audit, session_id)
        response = await create_openai_response({
            "model": active_agent_model(),
            **agent_reasoning_payload(),
            "instructions": developer_system_instructions(effective_system_instructions()),
            "previous_response_id": response["id"],
            "input": tool_outputs,
            "tools": runtime_chat_tools(),
            "tool_choice": "auto",
        })
    raise OpenAIError("Workshop Memory approval continuation exceeded 6 tool rounds")


'''
    text = text.replace(approval_marker, approval_helpers + approval_marker, 1)

    run_start = '''async def run_jarvis(message: str, session_id: str = "default") -> dict[str, Any]:
    local_result = None if developer_mode_enabled() else await try_local_ha_route(message, session_id)'''
    run_replacement = '''async def run_jarvis(message: str, session_id: str = "default") -> dict[str, Any]:
    if not developer_mode_enabled():
        await refresh_workshop_memory_tools()
    pending_workshop = PENDING_WORKSHOP_APPROVALS.get(session_id)
    workshop_decision = mcp_approval_decision(message)
    if pending_workshop and workshop_decision is not None:
        PENDING_WORKSHOP_APPROVALS.pop(session_id, None)
        result = await continue_workshop_memory_approval(
            pending_workshop, workshop_decision, session_id
        )
        append_chat_message(session_id, "user", message)
        append_chat_message(session_id, "assistant", result["reply"])
        return result
    local_result = None if developer_mode_enabled() else await try_local_ha_route(message, session_id)'''
    text = replace_once(text, run_start, run_replacement, "non-stream approval continuation")

    run_execute = '''        tool_outputs = await execute_tool_calls(calls, audit, session_id)

        response = await create_openai_response('''
    run_execute_replacement = '''        if workshop_memory_write_calls(calls):
            prompt = store_workshop_memory_approval(session_id, response["id"], calls)
            append_chat_message(session_id, "user", message)
            append_chat_message(session_id, "assistant", prompt)
            return {"reply": prompt, "tool_calls": audit}

        tool_outputs = await execute_tool_calls(calls, audit, session_id)

        response = await create_openai_response('''
    text = replace_once(text, run_execute, run_execute_replacement, "non-stream write interception")

    stream_start = '''async def _run_jarvis_stream_events(message: str, session_id: str = "default") -> AsyncIterator[bytes]:
    yield stream_event("status", message="Thinking…")

    pending_approval = PENDING_MCP_APPROVALS.get(session_id)'''
    stream_replacement = '''async def _run_jarvis_stream_events(message: str, session_id: str = "default") -> AsyncIterator[bytes]:
    yield stream_event("status", message="Thinking…")

    if not developer_mode_enabled():
        await refresh_workshop_memory_tools()
    pending_workshop = PENDING_WORKSHOP_APPROVALS.get(session_id)
    workshop_decision = mcp_approval_decision(message)
    if pending_workshop and workshop_decision is not None:
        PENDING_WORKSHOP_APPROVALS.pop(session_id, None)
        yield stream_event(
            "status",
            message="Executing approved Workshop Memory change…" if workshop_decision else "Denying Workshop Memory change…",
        )
        result = await continue_workshop_memory_approval(
            pending_workshop, workshop_decision, session_id
        )
        yield stream_event("status", message="Responding…")
        yield stream_event("delta", text=result["reply"])
        yield stream_event("done", tool_calls=result["tool_calls"])
        return

    pending_approval = PENDING_MCP_APPROVALS.get(session_id)'''
    text = replace_once(text, stream_start, stream_replacement, "stream approval continuation")

    stream_execute = '''        tool_outputs = await execute_tool_calls(calls, audit, session_id)

        # Stream the next model response.'''
    stream_execute_replacement = '''        if workshop_memory_write_calls(calls):
            prompt = store_workshop_memory_approval(session_id, response["id"], calls)
            yield stream_event("status", message="Permission required…")
            yield stream_event("delta", text=prompt)
            yield stream_event("done", tool_calls=audit)
            return

        tool_outputs = await execute_tool_calls(calls, audit, session_id)

        # Stream the next model response.'''
    text = replace_once(text, stream_execute, stream_execute_replacement, "stream write interception")

    text = text.replace('version="0.12.10"', 'version="0.12.11"')
    text = text.replace('"version": "0.12.10"', '"version": "0.12.11"')
    MAIN.write_text(text, encoding="utf-8")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")
    text = text.replace("HUD 0.12.10", "HUD 0.12.11")
    INDEX.write_text(text, encoding="utf-8")


def verify() -> None:
    main = MAIN.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    required_main = (
        'version="0.12.11"',
        '"name": "list_home_assistant_entity_inventory"',
        '"method": "tools/list"',
        "WORKSHOP_DYNAMIC_TOOLS",
        'return "read_only" if annotations.get("readOnlyHint") is True else "write"',
        "workshop_memory_function_tools()",
        "PENDING_WORKSHOP_APPROVALS",
        "workshop_memory_write_calls(calls)",
        "store_workshop_memory_approval",
        "continue_workshop_memory_approval",
        "Explicit user approval is required before this Workshop Memory change.",
        "Executing approved Workshop Memory change…",
    )
    missing = [marker for marker in required_main if marker not in main]
    if "HUD 0.12.11" not in index:
        missing.append("HUD 0.12.11")
    if missing:
        raise RuntimeError("ZBRANO v0.12.11 verification failed: " + ", ".join(missing))


if __name__ == "__main__":
    patch_main()
    patch_index()
    verify()
