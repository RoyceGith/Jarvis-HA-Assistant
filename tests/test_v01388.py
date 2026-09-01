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
        self.assertIn('version: "0.13.116"', CONFIG)
        self.assertIn('version="0.13.116"', MAIN)
        self.assertIn("HUD 0.13.116", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.116")

    def test_layout_selector_offers_detailed_and_compact_modes(self):
        self.assertIn('id="automation-library-layout"', HTML)
        self.assertIn('<option value="detailed">Detailed</option>', HTML)
        self.assertIn('<option value="compact">Compact cards</option>', HTML)

    def test_compact_mode_is_a_responsive_overview_grid(self):
        self.assertIn("#automation-library.is-compact { grid-template-columns: repeat(auto-fill,minmax(280px,1fr))", STYLE)
        self.assertIn(".autonomy-draft > :is(.automation-flow,small,details) { display: none; }", STYLE)
        self.assertIn("#automation-library.is-compact { grid-template-columns: 1fr; }", STYLE)

    def test_layout_is_applied_and_remembered_locally(self):
        self.assertIn('layout:["detailed","compact"].includes(value.layout)', WORKSPACE)
        self.assertIn('layout:$("automation-library-layout").value', WORKSPACE)
        self.assertIn('root.classList.toggle("is-compact",layout==="compact")', WORKSPACE)
        self.assertIn('$("automation-library-layout").value=libraryPrefs.layout', WORKSPACE)

    def test_browser_exercises_compact_rendering_and_storage(self):
        self.assertIn('locator("#automation-library-layout").selectOption("compact")', BROWSER)
        self.assertIn('element.classList.contains("is-compact")', BROWSER)
        self.assertIn('getComputedStyle(element).display', BROWSER)
        self.assertIn('layout: "compact"', BROWSER)

    def test_release_history_includes_v01387(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.115")


if __name__ == "__main__":
    unittest.main()
