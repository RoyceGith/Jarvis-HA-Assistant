import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
INDEX = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
ABOUT = (ROOT / "zbrano/app/static/js/about.js").read_text(encoding="utf-8")
CORE = (ROOT / "zbrano/app/static/js/core.js").read_text(encoding="utf-8")
CSS = (ROOT / "zbrano/app/static/css/about.css").read_text(encoding="utf-8")
CATALOG = (ROOT / "zbrano/app/static/js/i18n/catalog-advanced.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class UpdatedAboutShowcaseReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.221"', CONFIG)
        self.assertIn('version="0.13.221"', MAIN)
        self.assertIn("HUD 0.13.221", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.221")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.220")

    def test_about_represents_current_product(self):
        self.assertEqual(ABOUT.count('class="about-feature"'), 8)
        for phrase in ("Memory and knowledge", "Files and everyday organization", "Language and personalization", "Your choice of AI"):
            self.assertIn(phrase, ABOUT)

    def test_about_opens_memory_and_files(self):
        for control, tab in (("about-open-memory", "memory-tab"), ("about-open-files", "files-tab")):
            self.assertIn(f'id="{control}"', ABOUT)
            self.assertIn(f'getElementById("{control}")', CORE)
            self.assertIn(f'getElementById("{tab}")', CORE)

    def test_showcase_is_refined_responsive_and_translated(self):
        self.assertIn(".about-feature:hover", CSS)
        self.assertIn("grid-template-columns: repeat(4", CSS)
        self.assertIn("@media (max-width: 1120px)", CSS)
        for phrase in ("Files and everyday organization", "Language and personalization", "Browse files"):
            self.assertIn(f'"{phrase}"', CATALOG)


if __name__ == "__main__":
    unittest.main()
