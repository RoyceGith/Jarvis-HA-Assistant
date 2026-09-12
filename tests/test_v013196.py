import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
INDEX = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
STYLE = (ROOT / "zbrano/app/static/css/memory-studio.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "zbrano/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class MemoryStudioScrollingReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.233"', CONFIG)
        self.assertIn('version="0.13.233"', MAIN)
        self.assertIn("HUD 0.13.233", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.233")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.232")

    def test_memory_workspace_overrides_global_main_sizing(self):
        self.assertIn("position:static", STYLE)
        self.assertIn("height:100%;max-height:100%", STYLE)
        self.assertIn("overflow-y:auto", STYLE)
        self.assertIn("-webkit-overflow-scrolling:touch", STYLE)

    def test_browser_covers_every_memory_scroll_owner(self):
        self.assertIn("Memory Database must accept vertical scrolling", BROWSER)
        self.assertIn("Template Studio must accept vertical scrolling", BROWSER)
        self.assertIn("Compact Memory Studio must accept vertical scrolling", BROWSER)


if __name__ == "__main__":
    unittest.main()
