from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class WorkshopMemoryStartupWiringTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.27"', CONFIG)
        self.assertIn('version="0.13.27"', MAIN)
        self.assertIn("HUD 0.13.27", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.27")

    def test_startup_mcp_client_is_imported_from_domain(self):
        import_block = MAIN.split("from .domains.workshop_memory import (", 1)[1].split(")", 1)[0]
        self.assertIn("get_mcp_client,", import_block)
        self.assertIn("await get_mcp_client()", MAIN)


if __name__ == "__main__":
    unittest.main()
