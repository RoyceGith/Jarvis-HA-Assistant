import json
from pathlib import Path
import unittest

from zbrano.app.services.entity_policy import entity_permission_setup_detail


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
ONBOARDING = (ROOT / "zbrano/app/static/js/onboarding.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "zbrano/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class PlainDeviceAccessOnboardingReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.216"', CONFIG)
        self.assertIn('version="0.13.216"', MAIN)
        self.assertIn("HUD 0.13.216", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.216")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.215")

    def test_device_counts_use_the_same_sensor_and_control_concepts(self):
        self.assertEqual(entity_permission_setup_detail(1, 0), "1 sensor device · 0 control devices selected")
        self.assertEqual(entity_permission_setup_detail(2, 1), "2 sensor devices · 1 control device selected")
        self.assertIn('"title": "Device access"', MAIN)
        self.assertIn("entity_permission_setup_detail(read_count, control_count)", MAIN)

    def test_empty_access_explains_what_is_unavailable(self):
        detail = entity_permission_setup_detail(0, 0)
        self.assertIn("ZBRANO can chat", detail)
        self.assertIn("cannot read sensors or control devices yet", detail)

    def test_onboarding_actions_avoid_entity_policy_jargon(self):
        self.assertIn('entities: "Choose devices"', ONBOARDING)
        self.assertIn('entities: "Check choices"', ONBOARDING)
        self.assertIn('eyebrow: "DEVICE ACCESS"', ONBOARDING)
        self.assertIn("Device access: 3 sensor devices / 1 control devices", BROWSER)
        self.assertIn("/Device access/i", BROWSER)


if __name__ == "__main__":
    unittest.main()
