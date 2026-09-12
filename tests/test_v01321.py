from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class WorkshopMemoryStartupWiringTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.234"', CONFIG)
        self.assertIn('version="0.13.234"', MAIN)
        self.assertIn("HUD 0.13.234", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.234")

    def test_startup_uses_built_in_knowledge_memory(self):
        import_block = MAIN.split("from .domains.workshop_memory import (", 1)[1].split(")", 1)[0]
        self.assertNotIn("get_mcp_client,", import_block)
        self.assertIn("await migrate_legacy_workshop_memory()", MAIN)
        self.assertIn('local_root=DATA_DIR / "knowledge-memory"', MAIN)


if __name__ == "__main__":
    unittest.main()
