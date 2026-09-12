import ast
import json
from pathlib import Path
import secrets
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
CALENDAR = (ROOT / "zbrano/app/domains/calendar.py").read_text(encoding="utf-8")
CONTACTS = (ROOT / "zbrano/app/domains/contacts.py").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


def load_function(source, name, namespace):
    tree = ast.parse(source)
    node = next(item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), name, "exec"), namespace)
    return namespace[name]


class BirthdayPersistenceReleaseTests(unittest.TestCase):
    def test_linked_contact_recovers_a_missing_birthday_card(self):
        contact_data = {"contacts": [{
            "id": "contact-1", "display_name": "Alex", "birthday": "09-03",
            "birth_year": 1990, "relationship": "Friend", "birthday_id": "birthday-1",
        }]}
        birthday_data = {"birthdays": []}
        reconcile = load_function(CONTACTS, "reconcile_birthday_contacts", {
            "contacts_store": lambda: contact_data, "_birthday_store": lambda: birthday_data,
            "_contacts_save": lambda data: None, "_birthday_save": lambda data: None,
            "_normalize_contact": lambda data: data, "secrets": secrets, "time": time,
        })
        reconcile()
        self.assertEqual(len(birthday_data["birthdays"]), 1)
        self.assertEqual(birthday_data["birthdays"][0]["id"], "birthday-1")
        self.assertEqual(birthday_data["birthdays"][0]["birthday"], "09-03")

    def test_delivery_merge_preserves_other_current_birthdays(self):
        birthday_data = {"birthdays": [
            {"id": "birthday-1", "name": "Alex", "birthday": "09-03", "deliveries": {}},
            {"id": "birthday-2", "name": "Sam", "birthday": "10-04", "deliveries": {}},
        ]}
        save = load_function(CALENDAR, "_save_birthday_delivery", {
            "birthday_store": lambda: birthday_data, "_birthday_save": lambda data: None, "time": time,
        })
        self.assertTrue(save("birthday-1", "2026:1", {"status": "delivered", "at": 1.0}))
        self.assertEqual({item["id"] for item in birthday_data["birthdays"]}, {"birthday-1", "birthday-2"})
        self.assertEqual(birthday_data["birthdays"][0]["deliveries"]["2026:1"]["status"], "delivered")

    def test_birthday_read_repairs_links_before_listing(self):
        route = MAIN[MAIN.index('async def read_birthdays'):MAIN.index('@app.post("/api/birthdays")')]
        self.assertIn("reconcile_birthday_contacts()", route)

    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.237")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.236")


if __name__ == "__main__":
    unittest.main()
