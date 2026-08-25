from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from .mcp_approvals import mcp_approval_summary


GMAIL_DIRECT_TOOL_NAMES: set[str] = set()
_gmail_plugin_id: Callable[[], str] = lambda: ""


def configure_tool_progress(
    *,
    gmail_direct_tool_names: set[str],
    gmail_plugin_id_fn: Callable[[], str],
) -> None:
    global GMAIL_DIRECT_TOOL_NAMES, _gmail_plugin_id
    GMAIL_DIRECT_TOOL_NAMES = gmail_direct_tool_names
    _gmail_plugin_id = gmail_plugin_id_fn


def openai_tool_activity(event: dict[str, Any]) -> dict[str, str] | None:
    """Translate real Responses API tool events into safe UI activity metadata."""
    event_type = str(event.get("type") or "")
    item = event.get("item") if isinstance(event.get("item"), dict) else {}
    item_type = str(item.get("type") or "")
    if "web_search_call" in event_type or item_type == "web_search_call":
        state = "completed" if event_type.endswith((".completed", ".done")) else "started"
        return {
            "id": "native-web-search", "label": "Searching web", "state": state,
            "provider": "web", "plugin_id": "",
        }
    if item_type == "mcp_approval_request":
        label = mcp_approval_summary(item)
        server_label = str(item.get("server_label") or "")
        return {
            "id": str(item.get("id") or f"approval-{server_label}-{label}")[:180],
            "label": label, "state": "waiting_approval", "provider": "plugin",
            "plugin_id": server_label.removeprefix("plugin_"),
        }
    if item_type != "mcp_call" or event_type not in {"response.output_item.added", "response.output_item.done"}:
        return None
    name = str(item.get("name") or "Plugin tool")[:120]
    server_label = str(item.get("server_label") or "")
    state = "completed" if event_type.endswith(".done") else "started"
    return {
        "id": str(item.get("id") or f"mcp-{server_label}-{name}")[:180],
        "label": name.replace("_", " "), "state": state, "provider": "plugin",
        "plugin_id": server_label.removeprefix("plugin_"),
    }


def local_tool_activity(tool_names: list[str], *, writing: bool = False) -> dict[str, str]:
    history_tools = {
        "get_home_assistant_history", "correlate_home_assistant_timeline", "search_home_assistant_logbook",
    }
    local_ha = {
        "find_home_assistant_entities", "get_home_assistant_state",
        "turn_on_home_assistant_entity", "turn_off_home_assistant_entity", *history_tools,
    }
    if "prepare_autonomous_automation" in tool_names:
        return {"label": "Preparing automation preview", "provider": "home_assistant", "plugin_id": ""}
    if tool_names and all(name.startswith("get_grinder_") or name == "list_grinder_incidents" for name in tool_names):
        return {"label": "Reading grinder diagnostics", "provider": "grinder_monitor", "plugin_id": ""}
    if tool_names and all(name in local_ha for name in tool_names):
        label = "Reading Home Assistant History" if any(name in history_tools for name in tool_names) else "Reading Home Assistant"
        return {"label": label, "provider": "home_assistant", "plugin_id": ""}
    if tool_names and all(name in {"remember_fast_memory", "search_fast_memory", "forget_fast_memory"} for name in tool_names):
        writing_memory = any(name != "search_fast_memory" for name in tool_names)
        return {"label": "Updating Fast Memory" if writing_memory else "Reading Fast Memory", "provider": "fast_memory", "plugin_id": ""}
    if tool_names and all(name in GMAIL_DIRECT_TOOL_NAMES for name in tool_names):
        return {
            "label": "Creating Gmail draft" if writing else "Reading Gmail",
            "provider": "plugin", "plugin_id": _gmail_plugin_id(),
        }
    if "inspect_zbrano_ui_with_playwright" in tool_names:
        return {"label": "Inspecting ZBRANO interface", "provider": "developer", "plugin_id": "builtin-playwright"}
    if "investigate_zbrano_feature" in tool_names:
        return {"label": "Investigating ZBRANO", "provider": "developer", "plugin_id": ""}
    workshop_terms = ("project", "note", "memory", "handoff", "template", "reorganization", "progress")
    if any(any(term in name.lower() for term in workshop_terms) for name in tool_names):
        label = "Updating Workshop Memory" if writing else "Reading Workshop Memory"
        return {"label": label, "provider": "workshop_memory", "plugin_id": ""}
    readable = ", ".join(name.replace("_", " ") for name in tool_names[:3]) or "Tool work"
    return {"label": readable, "provider": "tool", "plugin_id": ""}


def remote_mcp_progress(event: dict[str, Any]) -> str | None:
    event_type = str(event.get("type") or "")
    if event_type not in {"response.output_item.added", "response.output_item.done"}:
        return None
    item = event.get("item") if isinstance(event.get("item"), dict) else {}
    item_type = str(item.get("type") or "")
    if item_type == "mcp_list_tools":
        return "Loading Developer repository tools..."
    if item_type != "mcp_call":
        return None
    name = str(item.get("name") or "repository tool")
    if event_type.endswith(".done"):
        return f"Developer tool completed: {name}. Reviewing its result..."
    return f"Developer tool started: {name}..."


def _tool_progress_phases(tool_names: list[str]) -> list[str]:
    if "investigate_zbrano_feature" in tool_names:
        return [
            "Checking the affected runtime layers...",
            "Reviewing targeted diagnostic evidence...",
            "Locating the likely fault boundary...",
        ]
    if "inspect_zbrano_ui_with_playwright" in tool_names:
        return [
            "Opening the local interface...",
            "Inspecting browser and network evidence...",
            "Reviewing the interface result...",
        ]
    return [
        "Waiting for the tool result...",
        "Reviewing returned evidence...",
        "The tool is taking longer than expected...",
    ]


def _tool_completion_status(tool_names: list[str], outputs: list[dict[str, Any]]) -> str:
    if "investigate_zbrano_feature" not in tool_names:
        return "Tool work complete. Reviewing the result..."
    for output in outputs:
        try:
            result = json.loads(str(output.get("output") or "{}"))
        except (TypeError, ValueError):
            continue
        if result.get("error"):
            return "Investigation stopped with an error. Preparing the details..."
        if result.get("status") in {"failed", "degraded"}:
            return "Problem confirmed. Reviewing the fault boundary..."
    return "Investigation complete. Reviewing the evidence..."
