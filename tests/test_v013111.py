import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CALENDAR = (ROOT / "jarvis/app/domains/calendar.py").read_text(encoding="utf-8")
INTENTS = (ROOT / "jarvis/app/services/calendar_intents.py").read_text(encoding="utf-8")
SCHEMAS = (ROOT / "jarvis/app/schemas.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
SCRIPT = (ROOT / "jarvis/app/static/js/calendar/center.js").read_text(encoding="utf-8")
STYLES = (ROOT / "jarvis/app/static/css/entity-columns.css").read_text(encoding="utf-8")
NOTIFICATIONS = (ROOT / "jarvis/app/domains/notifications.py").read_text(encoding="utf-8")
INBOX = (ROOT / "jarvis/app/static/js/notifications/inbox.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class BirthdayCalendarReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.210"', CONFIG)
        self.assertIn('version="0.13.210"', MAIN)
        self.assertIn("HUD 0.13.210", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.210")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.209")

    def test_birthdays_are_a_separate_persistent_calendar_domain(self):
        self.assertIn('BIRTHDAY_STORAGE_PATH = Path("/data/zbrano_birthdays.json")', CALENDAR)
        for marker in ("def birthday_store", "def list_birthdays", "async def _create_birthday", "async def _update_birthday", "def _delete_birthday"):
            self.assertIn(marker, CALENDAR)
        self.assertIn('"birthdays": birthday_store()', MAIN)
        self.assertIn("_birthday_save(birthdays)", MAIN)

    def test_annual_occurrence_and_delivery_are_bounded(self):
        self.assertIn("calendar_module.monthrange(year, month)", CALENDAR)
        self.assertIn('delivery_key = f"{occurrence_year}:{int(days_before)}"', CALENDAR)
        self.assertIn('previous.get("status") in {"delivered", "suppressed"}', CALENDAR)
        self.assertIn("await _process_birthday_reminders(time.time())", CALENDAR)

    def test_api_and_chat_workflows_are_wired(self):
        for route in ('@app.get("/api/birthdays")', '@app.post("/api/birthdays")', '@app.put("/api/birthdays/{birthday_id}")', '@app.delete("/api/birthdays/{birthday_id}")'):
            self.assertIn(route, MAIN)
        for tool in ('"name": "create_birthday"', '"name": "list_birthdays"', '"name": "update_birthday_details"'):
            self.assertIn(tool, MAIN)
        self.assertIn('"birthday", "birthdays", "gift idea"', INTENTS)
        self.assertIn("class BirthdayRequest", SCHEMAS)

    def test_calendar_has_people_and_add_views(self):
        self.assertIn('data-calendar-view="birthdays"', HTML)
        for view in ('data-birthday-view="people"', 'data-birthday-view="add"'):
            self.assertIn(view, HTML)
        self.assertNotIn('data-birthday-view="upcoming"', HTML)
        self.assertIn("function renderBirthdays()", SCRIPT)
        self.assertIn("function editBirthday(id)", SCRIPT)
        self.assertIn(".birthday-grid", STYLES)
        self.assertIn("Calendar birthdays", BROWSER)

    def test_top_bar_notification_inbox_tracks_persistent_unread_state(self):
        self.assertIn('id="notification-inbox-toggle"', HTML)
        self.assertIn('id="notification-inbox-popover"', HTML)
        self.assertIn('src="js/notifications/inbox.js"', HTML)
        self.assertIn("def notification_inbox", NOTIFICATIONS)
        self.assertIn("def mark_notification_deliveries_read", NOTIFICATIONS)
        self.assertIn('"read_at": 0.0', NOTIFICATIONS)
        self.assertIn('@app.get("/api/notifications/inbox")', MAIN)
        self.assertIn('@app.put("/api/notifications/inbox/read")', MAIN)
        self.assertIn("function openPopover()", INBOX)
        self.assertIn("Open Notification Center", HTML)
        self.assertIn("notification inbox", BROWSER)


if __name__ == "__main__":
    unittest.main()
