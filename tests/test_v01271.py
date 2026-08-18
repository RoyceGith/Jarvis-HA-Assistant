import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_calendar_center_v01271.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01271_adds_calendar_chat_workflow():
    for marker in (
        '"name": "create_calendar_appointment"',
        '"name": "list_calendar_appointments"',
        '"name": "cancel_calendar_appointment"',
        "ZBRANO CALENDAR WORKFLOW",
        "same day (default two hours before)",
        "without another approval prompt",
        "return calendar_priority_tools()",
    ):
        assert marker in PATCH


def test_v01271_persists_events_and_delivers_reminders():
    for marker in (
        'CALENDAR_STORAGE_PATH = Path("/data/zbrano_calendar.json")',
        "async def calendar_reminder_worker()",
        "await test_notification_channel(NotificationTestRequest(",
        'name="zbrano-calendar-reminders"',
        '"calendar": calendar_store()',
        '"calendar": _tab_activity_revision(CALENDAR_STORAGE_PATH)',
        "deduplicated",
    ):
        assert marker in PATCH


def test_v01271_adds_calendar_interface_and_header_shortcut():
    for marker in (
        'id="calendar-quick-open"',
        'id="calendar-tab"',
        'id="calendar-panel"',
        'data-calendar-view="upcoming"',
        'data-calendar-view="reminders"',
        'id="calendar-form"',
        'id="zbrano-v01271-calendar-center"',
        'showPanel("calendar")',
        "@media(max-width:620px)",
    ):
        assert marker in PATCH


def test_v01271_runs_last_and_aligns_release():
    name = "apply_calendar_center_v01271.py"
    assert f"COPY {name}" in DOCKER
    assert DOCKER.index("python3 ./apply_continuous_voice_playback_v01270.py") < DOCKER.index(f"python3 ./{name}")
    assert DOCKER.index(f"python3 ./{name}") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.71"' in CONFIG
    assert MANIFEST["version"] == "0.12.71"
    assert "ZBRANO v0.12.71" in README
    assert 'version="0.12.71"' in PATCH
