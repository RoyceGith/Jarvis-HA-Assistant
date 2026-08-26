import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class BrowserBuildRepairReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.52"', CONFIG)
        self.assertIn('version="0.13.52"', MAIN)
        self.assertIn("HUD 0.13.52", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.52")

    def test_browser_opens_editor_and_waits_for_inventory_before_template(self):
        open_editor = BROWSER.index('locator(".automation-advanced summary").click()')
        wait_inventory = BROWSER.index('locator("#automation-entity-options option").nth(47).waitFor({state: "attached"})')
        click_template = BROWSER.index('locator(\'[data-auto-template="comfort"]\').click()')
        self.assertLess(open_editor, wait_inventory)
        self.assertLess(wait_inventory, click_template)

    def test_release_history_includes_v01350(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.51")


if __name__ == "__main__":
    unittest.main()
