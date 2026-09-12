import json
from pathlib import Path
import tempfile
import unittest

from zbrano.app.services import knowledge_memory


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
INDEX = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
STUDIO = (ROOT / "zbrano/app/static/js/memory/studio.js").read_text(encoding="utf-8")
STYLE = (ROOT / "zbrano/app/static/css/memory-studio.css").read_text(encoding="utf-8")
CATALOG = (ROOT / "zbrano/app/static/js/i18n/catalog-advanced.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class AutomaticEverydayMemoryReleaseTests(unittest.TestCase):
    def setUp(self):
        self.original_root = knowledge_memory.KNOWLEDGE_ROOT
        self.temporary = tempfile.TemporaryDirectory()
        knowledge_memory.configure_knowledge_memory(root=Path(self.temporary.name))

    def tearDown(self):
        knowledge_memory.configure_knowledge_memory(root=self.original_root)
        self.temporary.cleanup()

    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.225"', CONFIG)
        self.assertIn('version="0.13.225"', MAIN)
        self.assertIn("HUD 0.13.225", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.225")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.224")

    def test_ordinary_memory_is_filed_without_manual_setup(self):
        saved = knowledge_memory.remember_automatically(
            "The living-room air conditioner filter is 40 x 60 cm."
        )
        self.assertEqual((saved["area"], saved["note"]), ("Home", "Maintenance.md"))
        self.assertTrue(saved["created_space"])
        content = knowledge_memory.read_memory_note(saved["space"], saved["note"])["content"]
        self.assertIn("40 x 60 cm", content)

        duplicate = knowledge_memory.remember_automatically(
            "The living-room air conditioner filter is 40 x 60 cm."
        )
        self.assertTrue(duplicate["duplicate"])
        content = knowledge_memory.read_memory_note(saved["space"], saved["note"])["content"]
        self.assertEqual(content.count("40 x 60 cm"), 1)

    def test_existing_matching_space_is_reused(self):
        knowledge_memory.create_memory_space("Household", "Shared home details", "blank", "Home")
        saved = knowledge_memory.remember_automatically("The boiler needs a service next month.")
        self.assertEqual(saved["space"], "Household")
        self.assertFalse(saved["created_space"])

    def test_everyday_areas_and_chat_tool_are_available(self):
        categories = {item["name"] for item in knowledge_memory.list_memory_categories()["categories"]}
        self.assertTrue({"People", "Health", "Travel", "Food", "Hobbies", "General"}.issubset(categories))
        tool = knowledge_memory.knowledge_memory_tool_catalog()["save_to_memory_database"]
        self.assertEqual(tool["permission"], "write")

    def test_default_interface_hides_organization_complexity(self):
        self.assertIn('id="memory-quick-form"', STUDIO)
        self.assertIn("What should ZBRANO remember?", STUDIO)
        self.assertIn("Organize manually", STUDIO)
        self.assertIn("You do not need to set this up.", STUDIO)
        self.assertIn("usedCategories", STUDIO)
        self.assertIn(".memory-capture", STYLE)
        self.assertIn('"What should ZBRANO remember?"', CATALOG)


if __name__ == "__main__":
    unittest.main()
