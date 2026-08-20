import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_google_calendar_sync_v01286.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_calendar_and_gmail_use_separate_oauth_grants() -> None:
    assert 'GOOGLE_CALENDAR_OAUTH_SCOPES = (' in PATCH
    assert 'https://www.googleapis.com/auth/calendar.calendarlist.readonly' in PATCH
    assert 'https://www.googleapis.com/auth/calendar.events' in PATCH
    assert 'if flow.get("google_service") != "gmail"' in PATCH
    assert 'flow.get("google_service") == "calendar"' in PATCH
    assert 'plugin_id = _google_calendar_plugin_id()' in PATCH
    assert 'plugin_id = _gmail_plugin_id()' in PATCH


def test_sync_is_preview_gated_and_incremental() -> None:
    assert 'async def google_calendar_preview()' in PATCH
    assert 'Preview this calendar before enabling synchronization' in PATCH
    assert 'async def google_calendar_sync_once()' in PATCH
    assert '"syncToken": sync_token' in PATCH
    assert 'getattr(exc, "status_code", 0) != 410' in PATCH
    assert 'GOOGLE_CALENDAR_SYNC_LOCK = asyncio.Lock()' in PATCH
    assert 'await asyncio.sleep(60.0)' in PATCH


def test_sync_preserves_local_reminders_and_deduplicates() -> None:
    assert 'local.setdefault("reminders", [])' in PATCH
    assert '"reminders": duplicate.get("reminders", [])' in PATCH
    assert 'abs(float(item.get("start_timestamp") or 0) - float(mapped.get("start_timestamp") or 0)) < 60' in PATCH
    assert '"google_sync_state": "pending_create"' in PATCH
    assert '"pending_delete" if appointment.get("google_event_id")' in PATCH
    assert 'def _google_calendar_merge_concurrent_local_changes' in PATCH
    assert 'getattr(exc, "status_code", 0) not in {404, 410}' in PATCH


def test_calendar_sync_api_ui_and_diagnostics_are_wired() -> None:
    for marker in (
        '/api/calendar/google/status',
        '/api/calendar/google/calendars',
        '/api/calendar/google/preview',
        '/api/calendar/google/settings',
        '/api/calendar/google/sync',
        'data-calendar-view="sync"',
        'id="google-calendar-connect"',
        'id="google-calendar-preview"',
        'id="google-calendar-enable"',
        'window.zbranoStartPluginOAuth = startPluginOAuth',
        'Google Calendar Direct synchronization',
    ):
        assert marker in PATCH


def test_release_and_build_chain_are_aligned() -> None:
    assert 'version: "0.12.86"' in CONFIG
    assert MANIFEST["version"] == "0.12.86"
    assert README.startswith("ZBRANO v0.12.86")
    copy = "COPY apply_google_calendar_sync_v01286.py ./apply_google_calendar_sync_v01286.py"
    run = "python3 ./apply_google_calendar_sync_v01286.py"
    assert copy in DOCKER
    assert run in DOCKER
    assert DOCKER.index("python3 ./apply_release_bump_v01285.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
