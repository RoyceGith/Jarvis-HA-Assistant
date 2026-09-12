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
MEMORY_CSS = (ROOT / "zbrano/app/static/css/memory-studio.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class EditableMemoryWorkspaceReleaseTests(unittest.TestCase):
    def setUp(self):
        self.original_root = knowledge_memory.KNOWLEDGE_ROOT
        self.temporary = tempfile.TemporaryDirectory()
        knowledge_memory.configure_knowledge_memory(root=Path(self.temporary.name))

    def tearDown(self):
        knowledge_memory.configure_knowledge_memory(root=self.original_root)
        self.temporary.cleanup()

    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.228"', CONFIG)
        self.assertIn('version="0.13.228"', MAIN)
        self.assertIn("HUD 0.13.228", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.228")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.227")

    def test_first_specific_recipe_save_offers_broad_and_specific_names(self):
        choice = knowledge_memory.remember_automatically("Beef soup recipe with barley and carrots.")
        self.assertTrue(choice["choice_required"])
        self.assertEqual(choice["existing_note"], "Soup Recipes.md")
        self.assertEqual(choice["new_note"], "Beef Soup Recipes.md")
        self.assertEqual([item["label"] for item in choice["choices"]], [
            "Use Soup Recipes", "Create Beef Soup Recipes",
        ])

    def test_existing_note_and_builtin_category_can_be_renamed(self):
        knowledge_memory.create_memory_space("Kitchen", "Recipes", "blank", "Food")
        knowledge_memory.write_memory_note("Kitchen", "Soups", "Beef soup", "create")
        renamed = knowledge_memory.update_memory_note("Kitchen", "Soups", "Winter Soups", "Beef soup\nBarley soup")
        self.assertEqual(renamed["note"], "Winter Soups.md")
        self.assertFalse((Path(self.temporary.name) / "Spaces" / "Kitchen" / "Soups.md").exists())
        category = knowledge_memory.update_memory_category("Food", "Recipes", "recipes", "My recipes")
        self.assertEqual(category["category"]["name"], "Recipes")
        self.assertEqual(knowledge_memory.list_memory_spaces()["spaces"][0]["category"], "Recipes")

    def test_my_memory_has_focused_editing_and_print_controls(self):
        self.assertIn('classList.add("memory-details-open")', STUDIO)
        self.assertIn('id="memory-print-note"', STUDIO)
        self.assertIn("displayNote(payload.note)", STUDIO)
        self.assertIn("original_note:state.selectedNote", STUDIO)
        self.assertIn("data-edit-category", STUDIO)
        self.assertIn("#memory-print-sheet", MEMORY_CSS)
        self.assertIn("memory-details-open", MEMORY_CSS)


if __name__ == "__main__":
    unittest.main()
