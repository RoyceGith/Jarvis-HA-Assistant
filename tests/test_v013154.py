import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
FLOW = (ROOT / "jarvis/app/static/js/automations/flow.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class PowerTriggerSelectionReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.170")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.169")

    def test_power_preset_depends_on_explicit_state_not_device_domain(self):
        self.assertIn('isPowerState=["changes_to","equals"].includes(operator)', WORKSPACE)
        self.assertNotIn('powerDomain=["switch","light","fan","input_boolean"]', WORKSPACE)
        self.assertIn('power=["changes_to","equals"].includes(item.operator||"changes_to")', FLOW)

    def test_power_preset_removes_comparison_fields(self):
        self.assertIn('preset.startsWith("power_")', WORKSPACE)
        self.assertIn('fields.delete("automation-trigger-operator")', WORKSPACE)
        self.assertIn('if(preset.startsWith("power_"))return', WORKSPACE)

    def test_switching_timed_events_to_sensor_clears_stale_power_state(self):
        self.assertIn('resetComparison=wasPower||(current.kind||"entity")!=="entity"', WORKSPACE)

    def test_browser_covers_primary_and_additional_climate_power_events(self):
        self.assertIn('fill("climate.browser_thermostat")', BROWSER)
        self.assertIn('fill("climate.browser_fixture")', BROWSER)
        self.assertIn('data-trigger-preset="power_on"', BROWSER)
        self.assertIn('data-trigger-preset="power_off"', BROWSER)
        self.assertIn('What should it do\\?|Compared with what value\\?', BROWSER)


if __name__ == "__main__":
    unittest.main()
