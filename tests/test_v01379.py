import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
CORE = (ROOT / "jarvis/app/static/js/core.js").read_text(encoding="utf-8")
STYLE = (ROOT / "jarvis/app/static/css/workspace-modern.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class ModernWorkspaceReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.148"', CONFIG)
        self.assertIn('version="0.13.148"', MAIN)
        self.assertIn("HUD 0.13.148", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.148")

    def test_automation_studio_precedes_chat_creation(self):
        studio = HTML.index('class="autonomy-card automation-studio-preview"')
        chat = HTML.index('class="autonomy-card automation-chat-builder"')
        self.assertLess(studio, chat)
        self.assertIn("Automation Studio must appear before Create with ZBRANO", BROWSER)

    def test_settings_use_grouped_icon_navigation(self):
        self.assertGreaterEqual(HTML.count('class="settings-nav-group"'), 4)
        self.assertIn('class="settings-nav-icon"', HTML)
        self.assertIn("grid-template-columns: minmax(210px, 250px) minmax(0, 1fr)", STYLE)
        self.assertIn(".settings-nav-group[open] > summary::after", STYLE)

    def test_settings_keyboard_navigation_supports_vertical_sidebar(self):
        self.assertIn("'ArrowUp', 'ArrowDown'", CORE)
        self.assertIn('tab.closest("details")?.setAttribute("open", "")', CORE)

    def test_primary_navigation_is_hover_driven_and_responsive(self):
        self.assertIn("cursor: pointer", STYLE)
        self.assertIn("body > main > nav button.active::after", STYLE)
        self.assertIn("@media (max-width: 820px)", STYLE)
        self.assertIn("primary-labeled-tab", HTML)

    def test_release_history_includes_v01378(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.147")


if __name__ == "__main__":
    unittest.main()
