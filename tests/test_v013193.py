import json
from pathlib import Path
import tempfile
import unittest

from zbrano.app.domains import workshop_memory
from zbrano.app.services import knowledge_memory


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
RUN = (ROOT / "zbrano/run.sh").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
MEMORY_UI = (ROOT / "zbrano/app/static/js/memory/studio.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class BuiltInKnowledgeMemoryReleaseTests(unittest.TestCase):
    def setUp(self):
        self.original_root = knowledge_memory.KNOWLEDGE_ROOT
        self.temporary = tempfile.TemporaryDirectory()
        knowledge_memory.configure_knowledge_memory(root=Path(self.temporary.name))

    def tearDown(self):
        knowledge_memory.configure_knowledge_memory(root=self.original_root)
        self.temporary.cleanup()

    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.248"', CONFIG)
        self.assertIn('version="0.13.248"', MAIN)
        self.assertEqual(MANIFEST["version"], "0.13.248")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.247")

    def test_spaces_are_generic_local_and_searchable(self):
        created = knowledge_memory.create_memory_space("Household", "Shared home knowledge", "home")
        self.assertEqual(created["space"]["template"], "home")
        knowledge_memory.write_memory_note("Household", "Appliances", "Boiler service is due in October.", "create")
        result = knowledge_memory.search_knowledge_memory("boiler", 10)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0]["relative_path"], "Spaces/Household/Appliances.md")
        self.assertNotIn("project", knowledge_memory.list_memory_spaces()["spaces"][0]["name"].lower())

    def test_note_paths_cannot_escape_local_store(self):
        knowledge_memory.create_memory_space("Home", "", "blank")
        with self.assertRaises(ValueError):
            knowledge_memory.write_memory_note("Home", "../../outside", "unsafe", "create")

    def test_backup_and_restore_round_trip(self):
        knowledge_memory.create_memory_space("Study", "Language notes", "study")
        backup = knowledge_memory.export_knowledge_memory()
        second = tempfile.TemporaryDirectory()
        try:
            knowledge_memory.configure_knowledge_memory(root=Path(second.name))
            restored = knowledge_memory.restore_knowledge_memory(backup)
            self.assertGreater(restored["restored"], 1)
            self.assertEqual(knowledge_memory.list_memory_spaces()["spaces"][0]["name"], "Study")
        finally:
            second.cleanup()

    def test_writes_remain_approval_gated(self):
        catalog = knowledge_memory.knowledge_memory_tool_catalog()
        self.assertEqual(catalog["write_memory_note"]["permission"], "write")
        self.assertEqual(catalog["create_memory_space"]["permission"], "write")
        self.assertEqual(workshop_memory.workshop_memory_tool_permission("write_project_note"), "write")

    def test_no_external_service_is_required(self):
        self.assertNotIn("workshop_memory_url:", CONFIG)
        self.assertIn("bashio::config.has_value 'workshop_memory_url'", RUN)
        self.assertIn('local_root=DATA_DIR / "knowledge-memory"', MAIN)
        self.assertIn('"knowledge_memory": export_knowledge_memory()', MAIN)
        self.assertIn("stays on this ZBRANO installation", MEMORY_UI)
        self.assertIn("Create space", MEMORY_UI)


if __name__ == "__main__":
    unittest.main()
