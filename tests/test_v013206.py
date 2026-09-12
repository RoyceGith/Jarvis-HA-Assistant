import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
INDEX = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
MEMORY_CSS = (ROOT / "zbrano/app/static/css/memory-studio.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class MemoryEditorSpacingReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.230"', CONFIG)
        self.assertIn('version="0.13.230"', MAIN)
        self.assertIn("HUD 0.13.230", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.230")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.229")

    def test_content_editor_starts_directly_below_its_label(self):
        self.assertIn("grid-template-rows:auto minmax(0,1fr)", MEMORY_CSS)
        self.assertIn(".memory-editor textarea{box-sizing:border-box;width:100%;height:auto;min-height:0", MEMORY_CSS)
        self.assertNotIn(".memory-editor textarea{box-sizing:border-box;width:100%;height:100%", MEMORY_CSS)


if __name__ == "__main__":
    unittest.main()
