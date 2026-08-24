from __future__ import annotations

import asyncio
from pathlib import Path
import time
from typing import Any

from fastapi import HTTPException

from ..schemas import CalendarAppointmentRequest, CalendarRemindersUpdateRequest, NotificationTestRequest


def configure_calendar_domain(
    *, plugin_load, plugin_save, notification_store_fn,
    notification_channels_fn, google_sync_store_fn,
    notification_quiet_now_fn, notification_test_fn,
) -> None:
    global _plugin_load, _plugin_save, notification_store, notification_channels
    global google_calendar_sync_store, _notification_quiet_now, test_notification_channel
    _plugin_load = plugin_load
    _plugin_save = plugin_save
    notification_store = notification_store_fn
    notification_channels = notification_channels_fn
    google_calendar_sync_store = google_sync_store_fn
    _notification_quiet_now = notification_quiet_now_fn
    test_notification_channel = notification_test_fn


CALENDAR_STORAGE_PATH = Path("/data/zbrano_calendar.json")

CALENDAR_MAX_APPOINTMENTS = 500

CALENDAR_REMINDER_OFFSETS = {
    0: "At appointment time",
    30: "30 minutes before",
    120: "Same day · 2 hours before",
    1440: "One day before",
    10080: "One week before",
}

def calendar_store() -> dict[str, Any]:
    data = _plugin_load(CALENDAR_STORAGE_PATH) or {}
    appointments = data.get("appointments") if isinstance(data.get("appointments"), list) else []
    return {"version": 1, "appointments": appointments[:CALENDAR_MAX_APPOINTMENTS]}

def _calendar_save(data: dict[str, Any]) -> None:
    appointments = list(data.get("appointments") or [])[:CALENDAR_MAX_APPOINTMENTS]
    appointments.sort(key=lambda item: float(item.get("start_timestamp") or 0))
    _plugin_save(CALENDAR_STORAGE_PATH, {"version": 1, "appointments": appointments})

def _calendar_start(value: str) -> tuple[Any, float]:
    from datetime import datetime

    raw = str(value or "").strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Appointment start must be a valid ISO-8601 date and time") from exc
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    timestamp = parsed.timestamp()
    if timestamp < time.time() - 60:
        raise HTTPException(status_code=400, detail="Appointment start must be in the future")
    return parsed, timestamp

def _calendar_public(appointment: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in appointment.items()
        if key not in {"last_error"} or value
    }

def list_calendar_appointments(include_past: bool = False) -> dict[str, Any]:
    now = time.time()
    appointments = [
        _calendar_public(item) for item in calendar_store()["appointments"]
        if item.get("status") != "cancelled"
        and (include_past or float(item.get("end_timestamp") or item.get("start_timestamp") or 0) >= now)
    ]
    appointments.sort(key=lambda item: float(item.get("start_timestamp") or 0))
    return {"appointments": appointments, "count": len(appointments), "generated_at": now}

async def _create_calendar_appointment(request: CalendarAppointmentRequest, source: str = "interface") -> dict[str, Any]:
    import secrets

    parsed, start_timestamp = _calendar_start(request.start_at)
    offsets = sorted({int(value) for value in request.reminder_offsets_minutes}, reverse=True)
    if any(value < 0 or value > 525600 for value in offsets):
        raise HTTPException(status_code=400, detail="Reminder offsets must be between 0 and 525600 minutes")
    destination = request.destination.strip().lower() or str(notification_store()["settings"].get("default_channel") or "")
    if offsets:
        channels = await notification_channels()
        if not destination:
            raise HTTPException(status_code=400, detail="Choose a default Notification Center channel before adding reminders")
        if not any(item["entity_id"] == destination for item in channels):
            raise HTTPException(status_code=400, detail="Calendar reminder destination is unavailable")

    data = calendar_store()
    normalized_title = " ".join(request.title.split())
    duplicate = next((
        item for item in data["appointments"]
        if item.get("status") != "cancelled"
        and str(item.get("title") or "").casefold() == normalized_title.casefold()
        and abs(float(item.get("start_timestamp") or 0) - start_timestamp) < 60
    ), None)
    if duplicate:
        return {"created": False, "deduplicated": True, "appointment": _calendar_public(duplicate)}

    now = time.time()
    appointment_id = secrets.token_hex(12)
    reminders = [
        {
            "id": secrets.token_hex(8),
            "offset_minutes": offset,
            "label": CALENDAR_REMINDER_OFFSETS.get(offset, f"{offset} minutes before"),
            "due_at": start_timestamp - offset * 60,
            "status": "scheduled",
            "last_attempt_at": 0.0,
            "delivered_at": 0.0,
        }
        for offset in offsets
    ]
    appointment = {
        "id": appointment_id,
        "title": normalized_title,
        "start_at": parsed.isoformat(),
        "start_timestamp": start_timestamp,
        "end_timestamp": start_timestamp + request.duration_minutes * 60,
        "duration_minutes": request.duration_minutes,
        "location": request.location.strip(),
        "notes": request.notes.strip(),
        "destination": destination,
        "status": "scheduled",
        "source": source,
        "google_sync_state": "pending_create" if google_calendar_sync_store()["enabled"] else "local_only",
        "created_at": now,
        "updated_at": now,
        "reminders": reminders,
    }
    data["appointments"].append(appointment)
    _calendar_save(data)
    return {"created": True, "deduplicated": False, "appointment": _calendar_public(appointment)}

async def _update_calendar_reminders(
    appointment_id: str, request: CalendarRemindersUpdateRequest, source: str = "interface",
) -> dict[str, Any]:
    import secrets

    offsets = sorted({int(value) for value in request.reminder_offsets_minutes}, reverse=True)
    if any(value < 0 or value > 525600 for value in offsets):
        raise HTTPException(status_code=400, detail="Reminder offsets must be between 0 and 525600 minutes")
    destination = request.destination.strip().lower() or str(notification_store()["settings"].get("default_channel") or "")
    if offsets:
        channels = await notification_channels()
        if not destination:
            raise HTTPException(status_code=400, detail="Choose a default Notification Center channel before adding reminders")
        if not any(item["entity_id"] == destination for item in channels):
            raise HTTPException(status_code=400, detail="Calendar reminder destination is unavailable")

    data = calendar_store()
    appointment = next((item for item in data["appointments"] if item.get("id") == appointment_id), None)
    if not appointment or appointment.get("status") == "cancelled":
        raise HTTPException(status_code=404, detail="Calendar appointment not found")
    if float(appointment.get("end_timestamp") or 0) < time.time():
        raise HTTPException(status_code=400, detail="Past appointment reminders cannot be edited")

    existing = {
        int(item.get("offset_minutes") or 0): item
        for item in appointment.get("reminders") or []
    }
    start_timestamp = float(appointment.get("start_timestamp") or 0)
    now = time.time()
    reminders = []
    for offset in offsets:
        previous = existing.get(offset)
        due_at = start_timestamp - offset * 60
        if previous:
            reminder = dict(previous)
            reminder["due_at"] = due_at
            reminder["label"] = CALENDAR_REMINDER_OFFSETS.get(offset, f"{offset} minutes before")
        else:
            reminder = {
                "id": secrets.token_hex(8),
                "offset_minutes": offset,
                "label": CALENDAR_REMINDER_OFFSETS.get(offset, f"{offset} minutes before"),
                "due_at": due_at,
                "status": "scheduled" if due_at >= now else "missed",
                "last_attempt_at": 0.0,
                "delivered_at": 0.0,
            }
        reminders.append(reminder)

    appointment["destination"] = destination
    appointment["reminders"] = reminders
    appointment["updated_at"] = now
    appointment["reminders_updated_by"] = source
    _calendar_save(data)
    return {"updated": True, "appointment": _calendar_public(appointment)}

def _cancel_calendar_appointment(appointment_id: str) -> dict[str, Any]:
    data = calendar_store()
    appointment = next((item for item in data["appointments"] if item.get("id") == appointment_id), None)
    if not appointment:
        raise HTTPException(status_code=404, detail="Calendar appointment not found")
    appointment["status"] = "cancelled"
    appointment["google_sync_state"] = "pending_delete" if appointment.get("google_event_id") and google_calendar_sync_store()["enabled"] else appointment.get("google_sync_state", "local_only")
    appointment["updated_at"] = time.time()
    for reminder in appointment.get("reminders") or []:
        if reminder.get("status") == "scheduled":
            reminder["status"] = "cancelled"
    _calendar_save(data)
    return {"cancelled": True, "appointment": _calendar_public(appointment)}

def _calendar_reminder_message(appointment: dict[str, Any], reminder: dict[str, Any]) -> str:
    from datetime import datetime

    local_start = datetime.fromtimestamp(float(appointment.get("start_timestamp") or 0)).astimezone()
    when = local_start.strftime("%A, %d %B %Y at %H:%M")
    parts = [f"{appointment.get('title')}", f"When: {when}"]
    if appointment.get("location"):
        parts.append(f"Where: {appointment['location']}")
    if reminder.get("label"):
        parts.append(f"Reminder: {reminder['label']}")
    return "\n".join(parts)

async def calendar_reminder_worker() -> None:
    while True:
        await asyncio.sleep(15.0)
        data = calendar_store()
        now = time.time()
        changed = False
        pending_deliveries: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = []
        for appointment in data["appointments"]:
            if appointment.get("status") != "scheduled":
                continue
            if now >= float(appointment.get("end_timestamp") or 0):
                appointment["status"] = "completed"
                appointment["updated_at"] = now
                for reminder in appointment.get("reminders") or []:
                    if reminder.get("status") == "scheduled":
                        reminder["status"] = "missed"
                changed = True
                continue
            for reminder in appointment.get("reminders") or []:
                if reminder.get("status") != "scheduled" or now < float(reminder.get("due_at") or 0):
                    continue
                due_at = float(reminder.get("due_at") or 0)
                if now - due_at > 86400:
                    reminder["status"] = "missed"
                    changed = True
                    continue
                if now - float(reminder.get("last_attempt_at") or 0) < 60:
                    continue
                reminder["last_attempt_at"] = now
                changed = True
                if _notification_quiet_now("information", now):
                    reminder["status"] = "suppressed"
                    continue
                appointment["updated_at"] = time.time()
                pending_deliveries.append((
                    str(appointment.get("id") or ""), str(reminder.get("id") or ""),
                    dict(appointment), dict(reminder),
                ))
        if changed:
            _calendar_save(data)
        for appointment_id, reminder_id, appointment, reminder in pending_deliveries:
            delivered = False
            error = ""
            try:
                await test_notification_channel(NotificationTestRequest(
                    target=str(appointment.get("destination") or ""),
                    severity="information",
                    title=f"Calendar · {appointment.get('title')}",
                    message=_calendar_reminder_message(appointment, reminder),
                ))
                delivered = True
            except (HTTPException, RuntimeError, OSError, ValueError) as exc:
                error = str(getattr(exc, "detail", exc))[:500]
            fresh = calendar_store()
            fresh_appointment = next((item for item in fresh["appointments"] if item.get("id") == appointment_id), None)
            fresh_reminder = next((
                item for item in (fresh_appointment.get("reminders") or [])
                if item.get("id") == reminder_id
            ), None) if fresh_appointment else None
            if not fresh_reminder:
                continue
            if delivered:
                fresh_reminder["status"] = "delivered"
                fresh_reminder["delivered_at"] = time.time()
                fresh_reminder.pop("last_error", None)
            else:
                fresh_reminder["status"] = "scheduled"
                fresh_reminder["last_error"] = error
            fresh_appointment["updated_at"] = time.time()
            _calendar_save(fresh)
