import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_editable_calendar_reminders_v01273.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01273_adds_editable_reminder_api_and_chat_tool():
    for marker in (
        "class CalendarRemindersUpdateRequest",
        '"name": "update_calendar_reminders"',
        "async def _update_calendar_reminders(",
        '@app.put("/api/calendar/{appointment_id}/reminders")',
        "return await _update_calendar_reminders(appointment_id, request)",
        '"update_calendar_reminders", "cancel_calendar_appointment"',
    ):
        assert marker in PATCH


def test_v01273_preserves_delivery_state_and_validates_updates():
    assert "previous = existing.get(offset)" in PATCH
    assert "reminder = dict(previous)" in PATCH
    assert '"status": "scheduled" if due_at >= now else "missed"' in PATCH
    assert "Past appointment reminders cannot be edited" in PATCH
    assert "reminder_offsets_minutes must" not in PATCH


def test_v01273_adds_reminder_editor_ui():
    for marker in (
        'id="calendar-reminder-editor"',
        'id="calendar-reminder-custom"',
        'id="calendar-reminder-destination"',
        'id="calendar-reminder-remove-all"',
        "function openReminderEditor(",
        "function reminderEditorOffsets()",
        "async function saveReminderEditor(",
        'method:"PUT"',
    ):
        assert marker in PATCH


def test_v01273_runs_last_and_aligns_release():
    name = "apply_editable_calendar_reminders_v01273.py"
    assert f"COPY {name}" in DOCKER
    assert DOCKER.index("python3 ./apply_natural_voice_prosody_v01272.py") < DOCKER.index(f"python3 ./{name}")
    assert DOCKER.index(f"python3 ./{name}") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.73"' in CONFIG
    assert MANIFEST["version"] == "0.12.73"
    assert "ZBRANO v0.12.73" in README
    assert 'version="0.12.73"' in PATCH
