import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
STYLE = (ROOT / "jarvis/app/static/css/automation-studio.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class AutomationLibraryLayoutReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.200"', CONFIG)
        self.assertIn('version="0.13.200"', MAIN)
        self.assertIn("HUD 0.13.200", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.200")

    def test_library_and_memory_are_left_navigation_subcategories(self):
        self.assertIn('class="automation-nav-sub" type="button" data-auto-view="library"', HTML)
        self.assertIn('class="automation-nav-sub" type="button" data-auto-view="memory"', HTML)
        self.assertNotIn('data-automation-library-view=', HTML)

    def test_compact_library_uses_collapsed_per_automation_flows(self):
        self.assertIn('#automation-library.is-compact { grid-template-columns: 1fr', STYLE)
        self.assertIn('.automation-library-flow > summary', STYLE)
        self.assertIn('flowDisclosure.className="automation-library-flow"', WORKSPACE)
        self.assertIn('View flow diagram', WORKSPACE)

    def test_compact_layout_is_applied_without_a_global_layout_switch(self):
        self.assertIn('root.classList.add("is-compact")', WORKSPACE)
        self.assertNotIn('automation-library-layout', HTML)
        self.assertNotIn('automation-library-layout', WORKSPACE)

    def test_browser_exercises_compact_rendering_and_disclosure(self):
        self.assertIn('element.classList.contains("is-compact")', BROWSER)
        self.assertIn('automation-library-flow summary', BROWSER)
        self.assertIn('automation-flow").first().isVisible()', BROWSER)

    def test_release_history_includes_v01387(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.199")


if __name__ == "__main__":
    unittest.main()
