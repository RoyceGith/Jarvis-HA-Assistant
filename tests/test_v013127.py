import ast
import json
from pathlib import Path
import secrets
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
CONTACTS = (ROOT / "zbrano/app/domains/contacts.py").read_text(encoding="utf-8")
CALENDAR_JS = (ROOT / "zbrano/app/static/js/calendar/center.js").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "zbrano/app/static/css/entity-columns.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


def load_function(source, name, namespace):
    tree = ast.parse(source)
    node = next(item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), name, "exec"), namespace)
    return namespace[name]


class BirthdayDirectoryReleaseTests(unittest.TestCase):
    def test_contact_chat_defaults_reminders_without_overwriting_choices(self):
        birthday_data = {"birthdays": []}
        sync = load_function(CONTACTS, "_sync_contact_birthday", {
            "Any": object, "_birthday_store": lambda: birthday_data,
            "_birthday_save": lambda data: None, "secrets": secrets, "time": time,
        })
        contact = {"id": "contact-1", "display_name": "Alex", "birthday": "09-03"}
        sync(contact, [7, 1])
        self.assertEqual(birthday_data["birthdays"][0]["reminder_days_before"], [7, 1])
        birthday_data["birthdays"][0]["reminder_days_before"] = [30]
        sync(contact, [7, 1])
        self.assertEqual(birthday_data["birthdays"][0]["reminder_days_before"], [30])

    def test_direct_chat_birthday_has_a_defensive_default(self):
        self.assertIn('birthday_arguments["reminder_days_before"] = [7, 1]', MAIN)
        self.assertIn('the default reminder schedule [7, 1]', (ROOT / "zbrano/app/services/calendar_intents.py").read_text(encoding="utf-8"))

    def test_people_view_contains_upcoming_and_month_sections(self):
        self.assertNotIn('data-birthday-view="upcoming"', HTML)
        self.assertIn('<h3>Next birthdays</h3>', HTML)
        self.assertIn('<h3>Birthdays by month</h3>', HTML)
        self.assertIn('const upcoming = birthdays.slice(0, 5)', CALENDAR_JS)
        self.assertIn('birthday-month-section', CALENDAR_JS)
        self.assertIn('.birthday-month-section', CSS)

    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.220")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.219")


if __name__ == "__main__":
    unittest.main()
