import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
SCHEMAS = (ROOT / "jarvis/app/schemas.py").read_text(encoding="utf-8")
AUTOMATIONS = (ROOT / "jarvis/app/domains/automations.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
FLOW = (ROOT / "jarvis/app/static/js/automations/flow.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class FocusedAutomationTaskReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.156"', CONFIG)
        self.assertIn('version="0.13.156"', MAIN)
        self.assertIn("HUD 0.13.156", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.156")

    def test_task_identity_is_bounded_and_persisted(self):
        self.assertIn("task_template: str = Field", SCHEMAS)
        self.assertIn("set_temperature|set_brightness", SCHEMAS)
        self.assertEqual(AUTOMATIONS.count('"task_template": str(item.get("task_template") or "service")'), 2)

    def test_temperature_and_brightness_have_focused_controls(self):
        for marker in ('["set_temperature","Set temperature"', '["set_brightness","Set brightness"',
                       'data-action-data-field="temperature"', 'data-action-data-field="brightness_pct"',
                       'climate.set_temperature', 'light.turn_on'):
            self.assertIn(marker, WORKSPACE)
        self.assertIn('templates={set_temperature:', FLOW)
        self.assertIn('set_brightness:[', FLOW)

    def test_presets_are_installation_aware_and_browser_covered(self):
        self.assertIn('hasDomain("climate")', WORKSPACE)
        self.assertIn('hasDomain("light")', WORKSPACE)
        self.assertIn('data-action-template="set_temperature"', BROWSER)
        self.assertIn('climate.browser_thermostat', BROWSER)
        self.assertIn('Set to 23.5°', BROWSER)

    def test_release_history_includes_v013101(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.155")


if __name__ == "__main__":
    unittest.main()
