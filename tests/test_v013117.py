import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "zbrano/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
STYLE = (ROOT / "zbrano/app/static/css/automation-studio.css").read_text(encoding="utf-8")
NAV_STYLE = (ROOT / "zbrano/app/static/css/workspace-modern.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class AutomationNavigationReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.243"', CONFIG)
        self.assertIn('version="0.13.243"', MAIN)
        self.assertIn("HUD 0.13.243", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.243")

    def test_studio_subcategories_are_independent_left_navigation_views(self):
        self.assertIn('data-auto-view="studio"', HTML)
        self.assertIn('class="automation-nav-sub" type="button" data-auto-view="library"', HTML)
        self.assertIn('class="automation-nav-sub" type="button" data-auto-view="memory"', HTML)
        self.assertIn('data-auto-panel="library"', HTML)
        self.assertIn('data-auto-panel="memory"', HTML)
        self.assertIn('button.automation-nav-sub', NAV_STYLE)

    def test_saved_automations_are_compact_and_expand_independently(self):
        self.assertIn('id="automation-library" class="autonomy-list is-compact"', HTML)
        self.assertIn('flowDisclosure.className="automation-library-flow"', WORKSPACE)
        self.assertIn('View flow diagram', WORKSPACE)
        self.assertIn('.automation-library-flow[open] .automation-library-flow-arrow', STYLE)
        self.assertNotIn('id="automation-library-layout"', HTML)

    def test_release_history_includes_v013116(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.242")


if __name__ == "__main__":
    unittest.main()
