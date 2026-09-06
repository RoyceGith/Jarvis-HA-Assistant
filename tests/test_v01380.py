import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
STYLE = (ROOT / "jarvis/app/static/css/workspace-modern.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class CompactScrollableWorkspaceReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.164"', CONFIG)
        self.assertIn('version="0.13.164"', MAIN)
        self.assertIn("HUD 0.13.164", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.164")

    def test_settings_controls_are_compact(self):
        self.assertIn("repeat(2, minmax(220px, 380px))", STYLE)
        self.assertIn('input[type="range"] { width: min(100%, 380px)', STYLE)
        self.assertIn("textarea:not(#message) { width: min(100%, 760px)", STYLE)

    def test_automations_use_settings_style_sidebar(self):
        self.assertIn('class="automation-nav-title"', HTML)
        self.assertGreaterEqual(HTML.count('class="automation-nav-icon"'), 6)
        self.assertIn("grid-template-columns: minmax(210px, 240px) minmax(0, 1fr)", STYLE)
        self.assertIn("#automations-panel .autonomy-tabs button.active", STYLE)

    def test_full_height_views_own_scrolling(self):
        self.assertIn("#settings-panel", STYLE)
        self.assertIn("overflow-y: auto", STYLE)
        self.assertIn(":is(#files-panel, #plugins-panel, #calendar-panel, #developer-panel)", STYLE)
        self.assertIn('Voice settings panel must accept vertical scrolling', BROWSER)

    def test_release_history_includes_v01379(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.163")


if __name__ == "__main__":
    unittest.main()
