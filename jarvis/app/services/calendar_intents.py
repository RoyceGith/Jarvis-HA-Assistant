from __future__ import annotations

import re
from typing import Any


CALENDAR_INTENT_TERMS = (
    "calendar", "appointment", "dentist", "doctor", "meeting", "reservation",
    "schedule", "reschedule", "agenda", "remind me on", "remind me at", "birthday", "birthdays", "gift idea",
    "contact", "contacts", "phone number", "email address", "iban", "bank account",
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
        "create_birthday", "list_birthdays", "update_birthday_details",
        "list_contacts", "save_contact",
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

BIRTHDAY WORKFLOW.
Birthdays are annual local records linked to Contacts and separate from appointments. Before saving a birthday, call
list_contacts with the supplied name. If it returns multiple people, ask the user to choose from a numbered list using
the returned full names; accept a reply containing only that number. If there is one match, update that contact with
save_contact so its birthday stays synchronized. If there is no match, create the contact. Require only the person's
name and month/day. Birth year, relationship, notes, gift ideas, and reminder timing are optional. Use
the default reminder schedule [7, 1] when the user does not specify one and a Notification Center destination is
available. Use list_birthdays for upcoming-birthday questions and before changing notes or gift ideas. Never create
a normal calendar appointment for a birthday, and never claim birthday details were saved unless the tool succeeds.

CONTACT WORKFLOW.
Contacts are private local records for people and companies. Always call list_contacts before saving details for a named
identity. When two or more plausible matches exist, never guess: show every plausible match as a numbered list and accept
the user's numeric reply. Use save_contact only after identity is unique. Ordinary searches must set include_sensitive to
false. Set it to true only when the user explicitly asks for bank or account details. Never repeat sensitive banking data
unless explicitly requested in that turn.
""".strip()
