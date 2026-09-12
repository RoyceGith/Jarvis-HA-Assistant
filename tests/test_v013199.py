import json
from pathlib import Path
import tempfile
import unittest

from zbrano.app.services import knowledge_memory, workshop_approvals


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
INDEX = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class FriendlyMemoryToolNameReleaseTests(unittest.TestCase):
    def setUp(self):
        self.original_root = knowledge_memory.KNOWLEDGE_ROOT
        self.temporary = tempfile.TemporaryDirectory()
        knowledge_memory.configure_knowledge_memory(root=Path(self.temporary.name))

    def tearDown(self):
        knowledge_memory.configure_knowledge_memory(root=self.original_root)
        self.temporary.cleanup()

    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.242"', CONFIG)
        self.assertIn('version="0.13.242"', MAIN)
        self.assertIn("HUD 0.13.242", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.242")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.241")

    def test_friendly_tool_name_is_advertised(self):
        catalog = knowledge_memory.knowledge_memory_tool_catalog()
        self.assertIn("save_to_memory_database", catalog)
        self.assertNotIn("remember_automatically", catalog)
        self.assertEqual(catalog["save_to_memory_database"]["permission"], "write")

    def test_approval_uses_human_readable_label(self):
        self.assertEqual(
            workshop_approvals.workshop_tool_display_name("save_to_memory_database"),
            "Save to Memory Database",
        )

    def test_old_internal_name_remains_compatible(self):
        arguments = {"content": "The spare keys are in the hall drawer.", "preferred_area": "home"}
        current = knowledge_memory.call_local_knowledge_tool("save_to_memory_database", arguments)
        legacy = knowledge_memory.call_local_knowledge_tool("remember_automatically", arguments)
        self.assertTrue(current["saved"])
        self.assertTrue(legacy["duplicate"])


if __name__ == "__main__":
    unittest.main()
