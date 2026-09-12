import json
from pathlib import Path
import tempfile
import unittest

from zbrano.app.services import knowledge_memory


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
INDEX = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
CORE = (ROOT / "zbrano/app/static/js/core.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class StructuredAutomaticMemoryReleaseTests(unittest.TestCase):
    def setUp(self):
        self.original_root = knowledge_memory.KNOWLEDGE_ROOT
        self.temporary = tempfile.TemporaryDirectory()
        knowledge_memory.configure_knowledge_memory(root=Path(self.temporary.name))

    def tearDown(self):
        knowledge_memory.configure_knowledge_memory(root=self.original_root)
        self.temporary.cleanup()

    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.243"', CONFIG)
        self.assertIn('version="0.13.243"', MAIN)
        self.assertIn("HUD 0.13.243", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.243")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.242")

    def test_new_automatic_entry_uses_sections_and_deduplicates_its_title(self):
        entry = knowledge_memory._automatic_memory_entry(
            "Creamy Chicken & Potato Soup",
            "Creamy Chicken & Potato Soup (4–6 servings)\n\n**Ingredients**\n\n- chicken",
        )
        self.assertTrue(entry.startswith("## Creamy Chicken & Potato Soup (4–6 servings)\n"))
        self.assertNotIn("- **Creamy Chicken", entry)
        self.assertEqual(entry.count("Creamy Chicken & Potato Soup"), 1)

    def test_opening_a_note_upgrades_legacy_list_wrapped_entries(self):
        knowledge_memory.create_memory_space("Food & Recipes", "Recipes", "blank", "Food")
        legacy = (
            "# Soup Recipes\n\n"
            "- **Beef Soup:** Beef Soup (serves 4)\n"
            "  \n  **Ingredients**\n  \n  - beef\n  - stock\n"
        )
        knowledge_memory.write_memory_note("Food & Recipes", "Soup Recipes", legacy, "create")
        opened = knowledge_memory.read_memory_note("Food & Recipes", "Soup Recipes")["content"]
        self.assertIn("## Beef Soup (serves 4)", opened)
        self.assertIn("\n- beef\n- stock\n", opened)
        self.assertNotIn("- **Beef Soup:**", opened)

    def test_fully_bold_numbered_step_remains_a_numbered_step(self):
        self.assertIn("standaloneBoldNumbered", CORE)
        self.assertIn("<li value=", CORE)


if __name__ == "__main__":
    unittest.main()
