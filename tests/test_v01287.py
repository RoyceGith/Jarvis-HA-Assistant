import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_calendar_reminder_status_v01287.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_reminder_status_dashboard_is_present() -> None:
    for marker in (
        'id="calendar-reminder-all-count"',
        'id="calendar-reminder-pending-count"',
        'id="calendar-reminder-completed-count"',
        'id="calendar-reminder-attention-count"',
        'data-reminder-filter="pending"',
        'data-reminder-filter="completed"',
        'data-reminder-filter="attention"',
    ):
        assert marker in PATCH


def test_status_classification_and_history_are_deterministic() -> None:
    assert 'if (status === "delivered") return "completed"' in PATCH
    assert 'if (status === "scheduled") return "pending"' in PATCH
    assert 'return "attention"' in PATCH
    assert 'state.allAppointments || state.appointments' in PATCH
    assert 'reminder.delivered_at' in PATCH
    assert 'displayState === "pending"' in PATCH


def test_release_and_build_order_are_aligned() -> None:
    assert 'version: "0.12.87"' in CONFIG
    assert MANIFEST["version"] == "0.12.87"
    copy = "COPY apply_calendar_reminder_status_v01287.py ./apply_calendar_reminder_status_v01287.py"
    run = "python3 ./apply_calendar_reminder_status_v01287.py"
    assert copy in DOCKER
    assert run in DOCKER
    assert DOCKER.index("python3 ./apply_google_calendar_sync_v01286.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
