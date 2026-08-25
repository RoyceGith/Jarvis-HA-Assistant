from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any


AUTOMATION_INTENT_TERMS = (
    "automation", "automate", "autonomous", "automatically", "whenever",
    "every time", "create a rule", "create rule", "make a rule",
)

_workshop_tools: list[dict[str, Any]] = []
_entity_memory_context: Callable[[str], str] = lambda message: ""
_brain_memory_context: Callable[[str], str] = lambda message: ""


def configure_automation_intents(
    *,
    workshop_tools: list[dict[str, Any]],
    entity_memory_context_fn: Callable[[str], str],
    brain_memory_context_fn: Callable[[str], str],
) -> None:
    global _workshop_tools, _entity_memory_context, _brain_memory_context
    _workshop_tools = workshop_tools
    _entity_memory_context = entity_memory_context_fn
    _brain_memory_context = brain_memory_context_fn


def is_automation_intent(message: str) -> bool:
    normalized = " ".join(str(message or "").casefold().split())
    if any(term in normalized for term in AUTOMATION_INTENT_TERMS):
        return True
    return bool(re.search(r"\b(?:if|when)\b.+\b(?:then|turn|switch|notify|suggest|tell|start|stop)\b", normalized))


def automation_priority_tools() -> list[dict[str, Any]]:
    names = {
        "find_home_assistant_entities", "get_home_assistant_state",
        "prepare_autonomous_automation", "create_notification_watch",
    }
    return [tool for tool in _workshop_tools if str(tool.get("name") or "") in names]


def automation_memory_input(message: str) -> list[dict[str, str]]:
    contexts = []
    if is_automation_intent(message):
        contexts.append(_entity_memory_context(message))
    contexts.append(_brain_memory_context(message))
    content = "\n".join(context for context in contexts if context)
    return [{"role": "developer", "content": content}] if content else []


def automation_system_instructions(base: str) -> str:
    return base + """

AUTOMATION BRAIN WORKFLOW IS ACTIVE.
Interpret the user's request as recurring behavior, not an immediate device command. First resolve each required
natural entity name with find_home_assistant_entities. Inspect the exact trigger and action entities with
get_home_assistant_state so current state and supported attributes are known. A remembered mapping is a candidate,
not permission to guess. If more than one plausible entity remains, present the short choices and ask which one.
Infer safe defaults only for cooldown and suggestion wording; ask when action semantics, presence, or authority are
materially ambiguous. Never generate executable code. Call prepare_autonomous_automation only with exact approved
entity IDs and a deterministic Home Assistant service. The tool stores a disabled draft and a review preview.
Explain that preview and ask the user to reply confirm or cancel. Activation happens only on that separate reply.
""".strip()
