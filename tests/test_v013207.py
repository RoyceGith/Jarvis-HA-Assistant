import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
INDEX = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
STUDIO = (ROOT / "jarvis/app/static/js/memory/studio.js").read_text(encoding="utf-8")
MEMORY_CSS = (ROOT / "jarvis/app/static/css/memory-studio.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class MemoryPrintHeadingReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.212"', CONFIG)
        self.assertIn('version="0.13.212"', MAIN)
        self.assertIn("HUD 0.13.212", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.212")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.211")

    def test_print_heading_uses_the_space_name(self):
        self.assertIn('title.textContent = state.selectedSpace || "My Memory";', STUDIO)
        self.assertNotIn('title.textContent = $("memory-note-name")', STUDIO)

    def test_print_heading_is_compact_and_has_no_prompt_marker(self):
        self.assertIn("font:650 13pt/1.25", MEMORY_CSS)
        self.assertIn("#memory-print-sheet h1::before,#memory-print-sheet h2::before", MEMORY_CSS)
        self.assertIn("{display:none!important;content:none!important}", MEMORY_CSS)


if __name__ == "__main__":
    unittest.main()
