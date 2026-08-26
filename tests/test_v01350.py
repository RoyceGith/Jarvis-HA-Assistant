import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class ProductDefaultSeparationReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.52"', CONFIG)
        self.assertIn('version="0.13.52"', MAIN)
        self.assertIn("HUD 0.13.52", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.52")

    def test_automation_templates_are_installation_derived_and_browser_checked(self):
        self.assertIn("function inventoryMatches", WORKSPACE)
        self.assertNotIn("sensor.workshop_temperature", WORKSPACE)
        self.assertNotIn("binary_sensor.workshop_presence", WORKSPACE)
        self.assertIn('execution_policy:"approval_required"', WORKSPACE)
        self.assertIn('locator(\'[data-auto-template="comfort"]\').click()', BROWSER)
        self.assertIn("sensor.browser_fixture_", BROWSER)

    def test_release_history_includes_previous_release(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.51")


if __name__ == "__main__":
    unittest.main()
