from __future__ import annotations

import re
from typing import Any

from .automation_intents import is_automation_intent


HOME_ASSISTANT_PRIORITY_TOOL_NAMES = {
    "find_home_assistant_entities",
    "get_home_assistant_state",
    "turn_on_home_assistant_entity",
    "turn_off_home_assistant_entity",
}
HOME_ASSISTANT_HISTORY_TOOL_NAMES = {
    "find_home_assistant_entities", "get_home_assistant_state", "get_home_assistant_history",
    "correlate_home_assistant_timeline", "search_home_assistant_logbook",
}
HOME_ASSISTANT_HISTORY_TERMS = (
    "history", "historical", "timeline", "logbook", "trend", "anomaly", "correlate", "correlation",
    "state changes", "changed over", "over time", "last hour", "last 24", "last day", "last week",
    "past hour", "past day", "past week", "when did", "how often", "how many times",
)

_workshop_tools: list[dict[str, Any]] = []


def configure_home_assistant_intents(*, workshop_tools: list[dict[str, Any]]) -> None:
    global _workshop_tools
    _workshop_tools = workshop_tools


def is_home_assistant_priority_intent(message: str) -> bool:
    normalized = " ".join(str(message or "").lower().split())
    if not normalized:
        return False
    if is_automation_intent(message):
        return False
    non_device_context = (
        "developer mode", "repository", "github", "git branch", "commit", "push", "pull request",
        "source code", "plugin", "web search", "search mode", "speak replies", "voice playback",
        "notification", "setting", "diagnostic", "automation", "autonomous", "automatically", "whenever",
    )
    if any(term in normalized for term in non_device_context):
        return False
    return bool(
        re.search(r"\b(?:turn|switch)\s+(?:on|off)\b", normalized)
        or re.search(r"\b(?:power|shut)\s+(?:on|off|down)\b", normalized)
        or re.search(r"\btoggle\b", normalized)
    )


def home_assistant_priority_tools() -> list[dict[str, Any]]:
    return [
        tool for tool in _workshop_tools
        if str(tool.get("name") or "") in HOME_ASSISTANT_PRIORITY_TOOL_NAMES
    ]


def is_home_assistant_history_intent(message: str) -> bool:
    normalized = " ".join(str(message or "").casefold().split())
    return bool(normalized and any(term in normalized for term in HOME_ASSISTANT_HISTORY_TERMS))


def home_assistant_history_tools() -> list[dict[str, Any]]:
    return [
        tool for tool in _workshop_tools
        if str(tool.get("name") or "") in HOME_ASSISTANT_HISTORY_TOOL_NAMES
    ]


def home_assistant_history_system_instructions(base: str) -> str:
    return base + """

HOME ASSISTANT HISTORY AND EVENT TIMELINE INTENT IS ACTIVE.
Use only the provided read-only Home Assistant tools. Resolve natural device names with find_home_assistant_entities,
then request bounded history for exact approved entity IDs. Use get_home_assistant_history for one or more trends,
search_home_assistant_logbook for named events, and correlate_home_assistant_timeline when timing relationships matter.
Default to 24 hours when the user gives no period. Never request more than seven days or eight entities in one call.
Report the exact observed window and distinguish measurements from inferred correlations. A close-in-time correlation
is not proof of causation. Do not inspect repositories, Workshop Memory, plugins, or the public web for this request.
""".strip()
