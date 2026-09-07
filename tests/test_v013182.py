import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
CORE = (ROOT / "jarvis/app/static/js/core.js").read_text(encoding="utf-8")
ABOUT = (ROOT / "jarvis/app/static/js/about.js").read_text(encoding="utf-8")
ABOUT_CSS = (ROOT / "jarvis/app/static/css/about.css").read_text(encoding="utf-8")
AUTOMATIONS = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
DEVELOPER = (ROOT / "jarvis/app/static/js/developer/mode.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class AboutProductShowcaseReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.184"', CONFIG)
        self.assertIn('version="0.13.184"', MAIN)
        self.assertIn("HUD 0.13.184", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.184")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.183")

    def test_about_is_a_top_level_feature_showcase(self):
        self.assertIn('<script src="js/about.js"></script>', HTML)
        self.assertIn('tab.id = "about-tab"', ABOUT)
        self.assertIn('panel.id = "about-panel"', ABOUT)
        self.assertIn('panel.setAttribute("aria-labelledby", "about-title")', ABOUT)
        self.assertEqual(ABOUT.count('class="about-feature"'), 6)
        for marker in (
            "Natural conversation",
            "Home awareness and control",
            "Visual automations",
            "Memory and organization",
            "Connected services",
            "Safety and ownership",
            "From a connected home to useful action",
            "DESIGNED TO STAY YOURS",
        ):
            self.assertIn(marker, ABOUT)

    def test_about_actions_open_real_product_workspaces(self):
        for control in ("about-start-chat", "about-open-setup", "about-open-devices", "about-open-automations"):
            self.assertIn(f'id="{control}"', ABOUT)
            self.assertIn(f'getElementById("{control}")', CORE)
        self.assertIn('const showAbout = panel === "about"', CORE)
        self.assertIn('showPanel("about")', CORE)
        self.assertIn('"about-panel"', AUTOMATIONS)
        self.assertIn('"about-panel"', DEVELOPER)

    def test_showcase_is_responsive_and_browser_covered(self):
        self.assertIn("grid-template-columns: repeat(3", ABOUT_CSS)
        self.assertIn("@media (max-width: 920px)", ABOUT_CSS)
        self.assertIn("@media (max-width: 560px)", ABOUT_CSS)
        self.assertIn("overflow-y: auto", ABOUT_CSS)
        self.assertIn('page.locator("#about-tab").click()', BROWSER)
        self.assertIn('page.locator("#about-panel .about-feature").count(), 6', BROWSER)
        self.assertIn("About showcase must scroll inside its panel", BROWSER)


if __name__ == "__main__":
    unittest.main()
