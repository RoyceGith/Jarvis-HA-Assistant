import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_month_reminder_status_v01288.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_month_cards_show_reminder_state() -> None:
    assert "function appointmentReminderSummary" in PATCH
    assert 'class="calendar-month-reminder-state"' in PATCH
    assert 'data-state="${esc(reminder.state)}"' in PATCH
    assert 'calendar-day-event-title' in PATCH
    assert 'return {state:"none", label:"No reminder"}' in PATCH


def test_mixed_and_selected_day_status_are_visible() -> None:
    assert 'parts.push(`${counts.pending > 1 ? counts.pending + " " : ""}Pending`)' in PATCH
    assert 'parts.push(`${counts.completed > 1 ? counts.completed + " " : ""}Completed`)' in PATCH
    assert 'parts.push(`${counts.attention > 1 ? counts.attention + " " : ""}Attention`)' in PATCH
    assert 'class="calendar-reminder-state"' in PATCH
    assert 'class="calendar-reminder-badges"' in PATCH
    assert 'const canEdit = Number(item.end_timestamp' in PATCH


def test_release_and_build_order_are_aligned() -> None:
    config_version = re.search(r'^version: "([0-9.]+)"$', CONFIG, re.MULTILINE)
    assert config_version
    assert tuple(map(int, config_version.group(1).split("."))) >= (0, 12, 88)
    assert tuple(map(int, MANIFEST["version"].split("."))) >= (0, 12, 88)
    copy = "COPY apply_month_reminder_status_v01288.py ./apply_month_reminder_status_v01288.py"
    run = "python3 ./apply_month_reminder_status_v01288.py"
    assert copy in DOCKER
    assert run in DOCKER
    assert DOCKER.index("python3 ./apply_calendar_reminder_status_v01287.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
