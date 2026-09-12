import json
from pathlib import Path
import unittest

from zbrano.app.services import workshop_approvals


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
INDEX = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")


class SingleMemorySaveApprovalTests(unittest.TestCase):
    def setUp(self):
        workshop_approvals.PENDING_MEMORY_ORGANIZATION.clear()
        workshop_approvals.configure_workshop_approvals(
            tool_permission_fn=lambda name: "write" if name == "save_to_memory_database" else "read_only",
            gmail_write_calls_fn=lambda calls: [],
        )

    def tearDown(self):
        workshop_approvals.PENDING_MEMORY_ORGANIZATION.clear()

    def test_release_alignment(self):
        self.assertIn('version: "0.13.230"', CONFIG)
        self.assertIn('version="0.13.230"', MAIN)
        self.assertIn("HUD 0.13.230", INDEX)

    def test_save_as_is_explicit_and_choice_call_is_canonicalized(self):
        self.assertTrue(workshop_approvals.is_explicit_memory_save_request(
            "save as soup recipes with beef",
        ))
        original = {
            "call_id": "first", "name": "save_to_memory_database",
            "arguments": json.dumps({
                "content": "Exact original recipes", "title": "Soup recipes with beef",
                "preferred_area": "food", "organization": "auto", "destination_note": "",
            }),
        }
        workshop_approvals.remember_memory_organization_choice("chat", original, {
            "choices": [{"id": "create_new", "destination_note": "Beef Soup Recipes.md"}],
        })
        final = {
            "call_id": "second", "name": "save_to_memory_database",
            "arguments": json.dumps({
                "content": "Regenerated recipes", "title": "Different",
                "preferred_area": "auto", "organization": "create_new",
                "destination_note": "Beef Soup Recipes.md",
            }),
        }
        self.assertTrue(workshop_approvals.memory_organization_choice_authorized("chat", [final]))
        arguments = json.loads(final["arguments"])
        self.assertEqual(arguments["content"], "Exact original recipes")
        self.assertEqual(arguments["title"], "Soup recipes with beef")
        self.assertEqual(arguments["preferred_area"], "food")


if __name__ == "__main__":
    unittest.main()
