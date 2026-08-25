from __future__ import annotations

import re
from typing import Any


CALENDAR_INTENT_TERMS = (
    "calendar", "appointment", "dentist", "doctor", "meeting", "reservation",
    "schedule", "reschedule", "agenda", "remind me on", "remind me at",
)

_workshop_tools: list[dict[str, Any]] = []


def configure_calendar_intents(*, workshop_tools: list[dict[str, Any]]) -> None:
    global _workshop_tools
    _workshop_tools = workshop_tools


def is_calendar_intent(message: str) -> bool:
    normalized = " ".join(str(message or "").casefold().split())
    if any(term in normalized for term in CALENDAR_INTENT_TERMS):
        return True
    has_date = bool(re.search(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{4}\b", normalized))
    has_time = bool(re.search(r"\b(?:[01]?\d|2[0-3])[:.]\d{2}\b", normalized))
    return has_date and has_time


def calendar_priority_tools() -> list[dict[str, Any]]:
    names = {
        "create_calendar_appointment", "list_calendar_appointments",
        "update_calendar_reminders", "cancel_calendar_appointment",
    }
    return [tool for tool in _workshop_tools if str(tool.get("name") or "") in names]


def calendar_system_instructions(base: str) -> str:
    return base + """

ZBRANO CALENDAR WORKFLOW.
When the user gives an appointment or dated event, collect only missing essentials before creating it: title,
calendar date, start time, and reminder preference. Treat DD.MM.YYYY as day-month-year and HH.MM as local
24-hour time. Treat a terse title plus date and time as an explicit request to add that appointment. Do not invent
a UTC offset when it is unknown; preserve the user's local wall-clock time. Duration defaults to 60 minutes and
location is optional; mention those defaults instead of asking unnecessary questions. If reminder timing is absent,
ask: same day (default two hours before), one day before,
both, custom timing, or none. Use offsets 120, 1440, [1440, 120], a user-specified minute offset, or []. Once the
user explicitly asks to add the appointment and the missing details are resolved, call create_calendar_appointment
without another approval prompt. Never claim it was saved unless the tool succeeds. Use list_calendar_appointments
for schedule questions and before cancelling an ambiguous event. When the user asks to change reminder timing,
list the appointments if necessary, then call update_calendar_reminders with the complete replacement schedule. An empty
offset list removes all reminders. Preserve delivered reminders at an unchanged offset so they are never resent accidentally.
Calendar reminders are delivered through the Notification Center default channel, including Telegram when configured.
""".strip()
