from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis" / "apply_visual_calendar_v01273.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis" / "Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis" / "config.yaml").read_text(encoding="utf-8")
MANIFEST = (ROOT / "jarvis" / "release_manifest.json").read_text(encoding="utf-8")


def test_visual_month_and_day_agenda_are_wired():
    for marker in (
        'data-calendar-view="month"',
        'id="calendar-month-grid"',
        'id="calendar-day-appointments"',
        "function renderMonthCalendar()",
        "function renderSelectedCalendarDay()",
        "cell.dataset.calendarDay = key",
    ):
        assert marker in PATCH


def test_calendar_loads_history_but_keeps_upcoming_filtered():
    assert 'api("api/calendar?include_past=true")' in PATCH
    assert "allAppointments: complete.appointments || []" in PATCH
    assert "Number(item.end_timestamp || item.start_timestamp || 0) >= now" in PATCH


def test_month_controls_and_responsive_layout_are_present():
    for marker in (
        'id="calendar-month-previous"',
        'id="calendar-month-next"',
        'id="calendar-month-today"',
        "calendar-month-layout",
        "@media(max-width:680px)",
    ):
        assert marker in PATCH


def test_visual_calendar_v01273_release_alignment():
    assert 'version: "0.12.73"' in CONFIG
    assert '"version": "0.12.73"' in MANIFEST
    assert "COPY apply_visual_calendar_v01273.py" in DOCKER
    assert "python3 ./apply_visual_calendar_v01273.py" in DOCKER
    assert DOCKER.index("apply_editable_calendar_reminders_v01273.py") < DOCKER.index("apply_visual_calendar_v01273.py")
