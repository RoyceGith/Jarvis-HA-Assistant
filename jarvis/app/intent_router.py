from __future__ import annotations

import re
from typing import Any


def parse_local_ha_intent(message: str) -> dict[str, Any] | None:
    """Recognize narrow, low-risk Home Assistant requests without an LLM."""
    normalized = " ".join(message.lower().strip().rstrip("?.!").split())

    control_patterns = (
        r"^(?:please )?(?:turn|switch) (?P<action>on|off) (?P<query>.+)$",
        r"^(?:please )?(?:turn|switch) (?P<query>.+?) (?P<action>on|off)$",
    )
    for pattern in control_patterns:
        match = re.fullmatch(pattern, normalized)
        if match:
            return {
                "kind": "control",
                "query": match.group("query").strip(),
                "turn_on": match.group("action") == "on",
            }

    state_match = re.fullmatch(
        r"^(?:is|are) (?P<query>.+?) (?P<expected>on|off)$",
        normalized,
    )
    if state_match:
        return {
            "kind": "state",
            "query": state_match.group("query").strip(),
            "expected": state_match.group("expected"),
        }

    state_patterns = (
        r"^(?:what is|what's) (?:the )?(?:state|status) of (?P<query>.+)$",
        r"^(?:check|get) (?:the )?(?:state|status) of (?P<query>.+)$",
    )
    for pattern in state_patterns:
        match = re.fullmatch(pattern, normalized)
        if match:
            return {"kind": "state", "query": match.group("query").strip()}

    return None
