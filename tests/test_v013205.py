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


class MemoryCategoryNavigationReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.213"', CONFIG)
        self.assertIn('version="0.13.213"', MAIN)
        self.assertIn("HUD 0.13.213", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.213")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.212")

    def test_entering_a_space_opens_its_first_note(self):
        self.assertIn("if (payload.notes?.length) await openNote(payload.notes[0]);", STUDIO)

    def test_categories_remain_available_above_the_note(self):
        self.assertIn('class="memory-space-category-tabs"', STUDIO)
        self.assertIn("data-open-memory-category", STUDIO)
        self.assertIn("if (matches.length === 1)", STUDIO)
        self.assertIn(".memory-space-category-tabs", MEMORY_CSS)

    def test_note_workspace_uses_more_available_space(self):
        self.assertIn("grid-template-columns:11.5rem minmax(0,1fr)", MEMORY_CSS)
        self.assertIn("minmax(30rem,1fr)", MEMORY_CSS)
        self.assertIn(":has(.memory-details-open)", MEMORY_CSS)


if __name__ == "__main__":
    unittest.main()
