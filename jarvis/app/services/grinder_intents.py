from __future__ import annotations

from typing import Any


GRINDER_DIAGNOSTIC_INTENT_TERMS = (
    "incident", "freeze", "freezes", "froze", "frozen", "stuck", "reboot",
    "restarted", "reset reason", "telemetry", "heartbeat", "hx711",
    "measuring", "measurement", "flight recorder", "pre-failure",
    "pre failure", "boot id", "grinder status", "grinder monitor",
)

_grinder_monitor_tools: list[dict[str, Any]] = []


def configure_grinder_intents(*, grinder_monitor_tools: list[dict[str, Any]]) -> None:
    global _grinder_monitor_tools
    _grinder_monitor_tools = grinder_monitor_tools


def is_grinder_diagnostic_intent(message: str) -> bool:
    normalized = " ".join(str(message or "").casefold().split())
    if "grinder" not in normalized and "espresso_grinder-" not in normalized:
        return False
    return any(term in normalized for term in GRINDER_DIAGNOSTIC_INTENT_TERMS)


def grinder_priority_tools() -> list[dict[str, Any]]:
    return list(_grinder_monitor_tools)


def grinder_system_instructions(base: str) -> str:
    return base + """

GRINDER DIAGNOSTIC INTENT IS ACTIVE.
Use the provided local grinder diagnostic tools before answering. They are the authoritative runtime source and
are not Workshop Memory tools. When an incident identifier is present, call get_grinder_incident with that exact
identifier. Otherwise call list_grinder_incidents, select the incident matching the user's timing description,
then call get_grinder_incident. Analyze the bounded pre_failure_window rather than asking the user for an export.
If the user says they manually removed power after a freeze, treat the later POWER ON reset as operator-caused and
exclude it from classification of the initiating failure. Compare telemetry sequence, weight, HX711 data age, loop
timing, state age, heap, Wi-Fi/MQTT state, relay command, boot identifier, and reset evidence. Clearly separate
measured evidence from inference. Never claim these tools are unavailable when they are present in this request.
The grinder diagnostic tools are read-only and must never issue control commands.
""".strip()
