from __future__ import annotations

from typing import Any


FAST_MEMORY_INTENT_TERMS = (
    "remember this", "remember that", "remember my", "remember i", "fast memory",
    "what do you remember", "what do you know about me", "forget this", "forget that",
    "forget what", "forget about", "remove this memory", "save this to memory",
    "keep this in memory", "remember for later", "personal profile", "memory profile",
)

_workshop_tools: list[dict[str, Any]] = []


def configure_fast_memory_intents(*, workshop_tools: list[dict[str, Any]]) -> None:
    global _workshop_tools
    _workshop_tools = workshop_tools


def is_fast_memory_intent(message: str) -> bool:
    normalized = " ".join(str(message or "").casefold().split())
    if "workshop memory" in normalized:
        return False
    return any(term in normalized for term in FAST_MEMORY_INTENT_TERMS)


def fast_memory_priority_tools() -> list[dict[str, Any]]:
    names = {"remember_fast_memory", "search_fast_memory", "forget_fast_memory"}
    return [tool for tool in _workshop_tools if str(tool.get("name") or "") in names]
