import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
INDEX = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
STUDIO = (ROOT / "jarvis/app/static/js/memory/studio.js").read_text(encoding="utf-8")
SERVICE = (ROOT / "jarvis/app/services/knowledge_memory.py").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class MemoryLayoutClarityReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.195"', CONFIG)
        self.assertIn('version="0.13.195"', MAIN)
        self.assertIn("HUD 0.13.195", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.195")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.194")

    def test_categories_and_layouts_have_distinct_jobs(self):
        self.assertIn("HOW SHOULD IT BE ORGANIZED?", STUDIO)
        self.assertIn('item.category === state.createCategory', STUDIO)
        self.assertIn('"name": "Household organizer"', SERVICE)
        self.assertIn('"name": "Work notebook"', SERVICE)
        self.assertIn('"name": "Project tracker"', SERVICE)
        self.assertIn('"name": "Empty space"', SERVICE)


if __name__ == "__main__":
    unittest.main()
