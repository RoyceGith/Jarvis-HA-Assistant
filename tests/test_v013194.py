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
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class MemoryStudioReleaseTests(unittest.TestCase):
    def setUp(self):
        self.original_root = knowledge_memory.KNOWLEDGE_ROOT
        self.temporary = tempfile.TemporaryDirectory()
        knowledge_memory.configure_knowledge_memory(root=Path(self.temporary.name))

    def tearDown(self):
        knowledge_memory.configure_knowledge_memory(root=self.original_root)
        self.temporary.cleanup()

    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.227"', CONFIG)
        self.assertIn('version="0.13.227"', MAIN)
        self.assertIn("HUD 0.13.227", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.227")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.226")

    def test_custom_category_template_and_space_round_trip(self):
        category = knowledge_memory.create_memory_category("Wellness", "health", "Appointments and records")
        self.assertEqual(category["category"]["name"], "Wellness")
        saved = knowledge_memory.save_memory_template(
            "Care plan", "Reusable health notes", "Wellness", "health",
            [
                {"name": "Overview", "purpose": "Current summary", "content": "# Overview\n"},
                {"name": "Visits/Questions.md", "purpose": "Questions to ask", "content": "# Questions\n"},
            ],
        )
        self.assertFalse(saved["template"]["built_in"])
        created = knowledge_memory.create_memory_space("My care", "Private health reference", "custom:Care plan", "Wellness")
        self.assertEqual(created["space"]["category"], "Wellness")
        self.assertEqual(created["notes_created"], ["Overview.md", "Visits/Questions.md"])
        notes = knowledge_memory.list_memory_notes("My care")
        self.assertEqual(notes["count"], 2)
        self.assertEqual(knowledge_memory.read_memory_note("My care", "Visits/Questions.md")["content"], "# Questions\n")
        self.assertEqual(knowledge_memory.knowledge_memory_tool_catalog()["create_memory_category"]["permission"], "write")

    def test_database_edit_delete_and_backup_restore(self):
        knowledge_memory.create_memory_category("Journeys", "travel", "Trips and places")
        knowledge_memory.save_memory_template("Trip", "Plan a trip", "Journeys", "travel", [{"name": "Plan", "purpose": "Itinerary", "content": "# Plan\n"}])
        knowledge_memory.create_memory_space("Rome", "Autumn holiday", "custom:Trip", "Journeys")
        knowledge_memory.write_memory_note("Rome", "Plan", "# Plan\nThree days", "replace")
        self.assertIn("Three days", knowledge_memory.read_memory_note("Rome", "Plan")["content"])
        backup = knowledge_memory.export_knowledge_memory()
        paths = {item["path"] for item in backup["files"]}
        self.assertIn("categories.json", paths)
        self.assertIn("Templates/Trip/.template.json", paths)
        second = tempfile.TemporaryDirectory()
        try:
            knowledge_memory.configure_knowledge_memory(root=Path(second.name))
            knowledge_memory.restore_knowledge_memory(backup)
            self.assertEqual(knowledge_memory.list_memory_spaces()["spaces"][0]["category"], "Journeys")
            self.assertTrue(any(item["name"] == "Trip" for item in knowledge_memory.list_memory_templates()["templates"]))
            knowledge_memory.delete_memory_note("Rome", "Plan")
            self.assertEqual(knowledge_memory.list_memory_notes("Rome")["count"], 0)
            knowledge_memory.delete_memory_space("Rome")
            knowledge_memory.delete_memory_template("Trip")
            self.assertEqual(knowledge_memory.list_memory_spaces()["count"], 0)
        finally:
            second.cleanup()

    def test_studio_exposes_guided_database_and_template_workspaces(self):
        self.assertIn('data-memory-view="database"', STUDIO)
        self.assertIn('data-memory-view="templates"', STUDIO)
        self.assertIn('id="memory-create-categories"', STUDIO)
        self.assertIn('id="memory-create-templates"', STUDIO)
        self.assertIn('id="memory-note-blueprints"', STUDIO)
        self.assertIn("@media(max-width:850px)", STYLE)
        self.assertIn("HOW SHOULD IT BE ORGANIZED?", STUDIO)

    def test_builtin_layout_names_do_not_repeat_category_names(self):
        templates = knowledge_memory.list_memory_templates()["templates"]
        names = {item["id"]: item["name"] for item in templates}
        self.assertEqual(names["home"], "Household organizer")
        self.assertEqual(names["work"], "Work notebook")
        self.assertEqual(names["project"], "Project tracker")
        self.assertEqual(names["blank"], "Empty space")

    def test_template_note_paths_are_safe_and_unique(self):
        with self.assertRaises(ValueError):
            knowledge_memory.save_memory_template("Unsafe", "", "Personal", "template", [{"name": "../../outside", "purpose": "", "content": ""}])
        with self.assertRaises(ValueError):
            knowledge_memory.save_memory_template("Duplicates", "", "Personal", "template", [{"name": "One", "purpose": "", "content": ""}, {"name": "one.md", "purpose": "", "content": ""}])

    def test_studio_is_a_dedicated_responsive_workspace(self):
        self.assertIn('id="memory-tab"', INDEX)
        self.assertIn('id="memory-panel"', INDEX)
        self.assertIn("My memory", STUDIO)
        self.assertIn("Customize organization", STUDIO)
        self.assertIn("data-template-note-name", STUDIO)
        self.assertIn("stays on this zbrano installation", STUDIO.lower())
        self.assertIn(".memory-space-layout", STYLE)
        self.assertIn("@media(max-width:850px)", STYLE)


if __name__ == "__main__":
    unittest.main()
