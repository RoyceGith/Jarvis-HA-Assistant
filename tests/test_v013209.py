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


class CompactMemoryLandingReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.213"', CONFIG)
        self.assertIn('version="0.13.213"', MAIN)
        self.assertIn("HUD 0.13.213", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.213")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.212")

    def test_landing_page_uses_compact_overview(self):
        self.assertIn('class="memory-overview-bar"', STUDIO)
        self.assertIn('<span>Areas</span>', STUDIO)
        self.assertIn('<span>Notes</span>', STUDIO)
        self.assertIn(".memory-overview-bar{display:grid", MEMORY_CSS)
        self.assertIn("min-height:3.6rem", MEMORY_CSS)
        self.assertIn(".memory-card h3{font-size:.88rem", MEMORY_CSS)

    def test_compact_overview_remains_responsive(self):
        self.assertIn("@media(max-width:1050px){.memory-overview-bar{grid-template-columns:1fr}", MEMORY_CSS)


if __name__ == "__main__":
    unittest.main()
