import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
INDEX = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
STUDIO = (ROOT / "zbrano/app/static/js/memory/studio.js").read_text(encoding="utf-8")
SERVICE = (ROOT / "zbrano/app/services/knowledge_memory.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "zbrano/Dockerfile").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class MemoryLayoutClarityReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.217"', CONFIG)
        self.assertIn('version="0.13.217"', MAIN)
        self.assertIn("HUD 0.13.217", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.217")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.216")

    def test_categories_and_layouts_have_distinct_jobs(self):
        self.assertIn("HOW SHOULD IT BE ORGANIZED?", STUDIO)
        self.assertIn('item.category === state.createCategory', STUDIO)
        self.assertIn('"name": "Household organizer"', SERVICE)
        self.assertIn('"name": "Work notebook"', SERVICE)
        self.assertIn('"name": "Project tracker"', SERVICE)
        self.assertIn('"name": "Empty space"', SERVICE)

    def test_browser_smoke_runs_once_on_native_architecture(self):
        self.assertIn('if [ "$BUILD_ARCH" = "aarch64" ]', DOCKER)
        self.assertIn("node ./tests/browser_smoke.cjs", DOCKER)
        self.assertIn("Python compilation, and API test", DOCKER)


if __name__ == "__main__":
    unittest.main()
