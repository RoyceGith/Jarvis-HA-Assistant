import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "zbrano/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
STYLE = (ROOT / "zbrano/app/static/css/automation-studio.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "zbrano/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class AutomationLibrarySummaryReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.236"', CONFIG)
        self.assertIn('version="0.13.236"', MAIN)
        self.assertIn("HUD 0.13.236", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.236")

    def test_visual_summary_exposes_live_status_categories(self):
        self.assertIn('id="automation-library-summary"', HTML)
        for value in ("all", "active", "attention", "disabled", "autonomous"):
            self.assertIn(f'data-library-quick-filter="{value}"', HTML)
            self.assertIn(f'id="automation-library-{value}-count"', HTML)

    def test_summary_counts_share_filter_semantics(self):
        self.assertIn("function automationNeedsAttention(item)", WORKSPACE)
        self.assertIn("active:all.filter(item=>item.enabled).length", WORKSPACE)
        self.assertIn("attention:all.filter(automationNeedsAttention).length", WORKSPACE)
        self.assertIn("disabled:all.filter(item=>!item.enabled).length", WORKSPACE)
        self.assertIn('item.execution_policy==="autonomous"', WORKSPACE)

    def test_quick_filters_are_accessible_and_synchronized(self):
        self.assertIn('aria-pressed="true"', HTML)
        self.assertIn('button.setAttribute("aria-pressed"', WORKSPACE)
        self.assertIn('$("automation-library-filter").value=button.dataset.libraryQuickFilter', WORKSPACE)
        self.assertIn("persistLibraryPrefs();renderLibrary()", WORKSPACE)

    def test_summary_is_graphical_and_responsive(self):
        self.assertIn(".automation-library-summary { display: grid", STYLE)
        self.assertIn('button[aria-pressed="true"]', STYLE)
        self.assertIn("grid-template-columns: repeat(2,minmax(0,1fr))", STYLE)

    def test_browser_exercises_counts_and_quick_filter(self):
        self.assertIn('locator("#automation-library-all-count")', BROWSER)
        self.assertIn('locator("#automation-library-attention-count")', BROWSER)
        self.assertIn('data-library-quick-filter="disabled"', BROWSER)
        self.assertIn('getAttribute("aria-pressed")', BROWSER)

    def test_release_history_includes_v01386(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.235")


if __name__ == "__main__":
    unittest.main()
