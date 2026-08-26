from __future__ import annotations

from collections.abc import Callable
from typing import Any


_developer_mode_enabled: Callable[[], bool] = lambda: False
_developer_system_instructions: Callable[[str], str] = lambda base: base
_is_ha_history: Callable[[str], bool] = lambda message: False
_ha_history_instructions: Callable[[str], str] = lambda base: base
_is_automation: Callable[[str], bool] = lambda message: False
_automation_instructions: Callable[[str], str] = lambda base: base
_calendar_instructions: Callable[[str], str] = lambda base: base
_is_grinder: Callable[[str], bool] = lambda message: False
_grinder_instructions: Callable[[str], str] = lambda base: base
_is_ha_priority: Callable[[str], bool] = lambda message: False
_developer_tools: Callable[[], list[dict[str, Any]]] = lambda: []
_developer_mcp_tools: Callable[[], list[dict[str, Any]]] = lambda: []
_grinder_tools: Callable[[], list[dict[str, Any]]] = lambda: []
_is_fast_memory: Callable[[str], bool] = lambda message: False
_fast_memory_tools: Callable[[], list[dict[str, Any]]] = lambda: []
_automation_tools: Callable[[], list[dict[str, Any]]] = lambda: []
_is_calendar: Callable[[str], bool] = lambda message: False
_calendar_tools: Callable[[], list[dict[str, Any]]] = lambda: []
_ha_history_tools: Callable[[], list[dict[str, Any]]] = lambda: []
_ha_priority_tools: Callable[[], list[dict[str, Any]]] = lambda: []
_default_tools: Callable[[], list[dict[str, Any]]] = lambda: []
_is_workshop_memory: Callable[[str], bool] = lambda message: False
_workshop_memory_tools: Callable[[], list[dict[str, Any]]] = lambda: []
_native_web_search_tool: Callable[[str], dict[str, Any] | None] = lambda mode: None


def configure_runtime_routing(
    *,
    developer_mode_enabled_fn: Callable[[], bool],
    developer_system_instructions_fn: Callable[[str], str],
    is_ha_history_fn: Callable[[str], bool],
    ha_history_instructions_fn: Callable[[str], str],
    is_automation_fn: Callable[[str], bool],
    automation_instructions_fn: Callable[[str], str],
    calendar_instructions_fn: Callable[[str], str],
    is_grinder_fn: Callable[[str], bool],
    grinder_instructions_fn: Callable[[str], str],
    is_ha_priority_fn: Callable[[str], bool],
    developer_tools_fn: Callable[[], list[dict[str, Any]]],
    developer_mcp_tools_fn: Callable[[], list[dict[str, Any]]],
    grinder_tools_fn: Callable[[], list[dict[str, Any]]],
    is_fast_memory_fn: Callable[[str], bool],
    fast_memory_tools_fn: Callable[[], list[dict[str, Any]]],
    automation_tools_fn: Callable[[], list[dict[str, Any]]],
    is_calendar_fn: Callable[[str], bool],
    calendar_tools_fn: Callable[[], list[dict[str, Any]]],
    ha_history_tools_fn: Callable[[], list[dict[str, Any]]],
    ha_priority_tools_fn: Callable[[], list[dict[str, Any]]],
    default_tools_fn: Callable[[], list[dict[str, Any]]],
    native_web_search_tool_fn: Callable[[str], dict[str, Any] | None],
    is_workshop_memory_fn: Callable[[str], bool] | None = None,
    workshop_memory_tools_fn: Callable[[], list[dict[str, Any]]] | None = None,
) -> None:
    global _developer_mode_enabled, _developer_system_instructions, _is_ha_history
    global _ha_history_instructions, _is_automation, _automation_instructions
    global _calendar_instructions, _is_grinder, _grinder_instructions, _is_ha_priority
    global _developer_tools, _developer_mcp_tools, _grinder_tools, _is_fast_memory
    global _fast_memory_tools, _automation_tools, _is_calendar, _calendar_tools
    global _ha_history_tools, _ha_priority_tools, _default_tools, _native_web_search_tool
    global _is_workshop_memory, _workshop_memory_tools
    _developer_mode_enabled = developer_mode_enabled_fn
    _developer_system_instructions = developer_system_instructions_fn
    _is_ha_history = is_ha_history_fn
    _ha_history_instructions = ha_history_instructions_fn
    _is_automation = is_automation_fn
    _automation_instructions = automation_instructions_fn
    _calendar_instructions = calendar_instructions_fn
    _is_grinder = is_grinder_fn
    _grinder_instructions = grinder_instructions_fn
    _is_ha_priority = is_ha_priority_fn
    _developer_tools = developer_tools_fn
    _developer_mcp_tools = developer_mcp_tools_fn
    _grinder_tools = grinder_tools_fn
    _is_fast_memory = is_fast_memory_fn
    _fast_memory_tools = fast_memory_tools_fn
    _automation_tools = automation_tools_fn
    _is_calendar = is_calendar_fn
    _calendar_tools = calendar_tools_fn
    _ha_history_tools = ha_history_tools_fn
    _ha_priority_tools = ha_priority_tools_fn
    _default_tools = default_tools_fn
    _native_web_search_tool = native_web_search_tool_fn
    _is_workshop_memory = is_workshop_memory_fn or (lambda message: False)
    _workshop_memory_tools = workshop_memory_tools_fn or (lambda: [])


def priority_system_instructions(base: str, message: str) -> str:
    if not _developer_mode_enabled() and _is_ha_history(message):
        return _ha_history_instructions(base)
    if not _developer_mode_enabled() and _is_automation(message):
        return _automation_instructions(base)
    if not _developer_mode_enabled():
        base = _calendar_instructions(base)
    if not _developer_mode_enabled() and _is_grinder(message):
        return _grinder_instructions(base)
    if not _is_ha_priority(message):
        return _developer_system_instructions(base)
    return base + """

HOME ASSISTANT DEVICE CONTROL INTENT IS ACTIVE.
Resolve the requested device only with the provided Home Assistant entity tools. Do not inspect repositories,
plugins, Workshop Memory, or the web. If the entity name is ambiguous, search approved Home Assistant entities
and ask one concise clarification rather than selecting an unsafe device. Execute only the requested state change.
""".strip()


def runtime_chat_tools(search_mode: str = "auto", message: str = "") -> list[dict[str, Any]]:
    if _developer_mode_enabled():
        return _developer_tools() + _developer_mcp_tools()
    if _is_grinder(message):
        return _grinder_tools()
    if _is_fast_memory(message):
        return _fast_memory_tools()
    if _is_automation(message):
        return _automation_tools()
    if _is_calendar(message):
        return _calendar_tools()
    if _is_ha_history(message):
        return _ha_history_tools()
    if _is_ha_priority(message):
        return _ha_priority_tools()
    if _is_workshop_memory(message):
        return _workshop_memory_tools()
    tools = _default_tools()
    search_tool = _native_web_search_tool(search_mode)
    return tools + ([search_tool] if search_tool else [])
