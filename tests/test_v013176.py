import json
from pathlib import Path
import unittest

from zbrano.app.services.entity_policy import classify_entity_risk


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
CORE = (ROOT / "zbrano/app/static/js/core.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "zbrano/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class PlainEntityAccessReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.232"', CONFIG)
        self.assertIn('version="0.13.232"', MAIN)
        self.assertIn("HUD 0.13.232", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.232")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.231")

    def test_inventory_uses_plain_access_choices(self):
        self.assertIn('"Sensor device · read information"', CORE)
        self.assertIn('"Sensor device · read status only"', CORE)
        self.assertIn('"Control device · allow actions"', CORE)
        self.assertIn('"Do not allow"', CORE)
        self.assertNotIn('["read_only", "read_only"]', CORE)
        self.assertNotIn('["confirmation_required", "confirmation_required"]', CORE)

    def test_legacy_values_remain_visible_until_owner_replaces_them(self):
        self.assertIn("function entityAccessOptions(entity, currentAccess)", CORE)
        self.assertIn('options.push([currentAccess, "Legacy setting · choose a new access level"])', CORE)

    def test_hvac_status_sensors_are_never_recommended_for_control(self):
        self.assertEqual(
            classify_entity_risk(
                "binary_sensor",
                None,
                "binary_sensor.living_room_air_conditioner_status",
                "Living room air conditioner status",
            ),
            "read_only",
        )
        self.assertEqual(
            classify_entity_risk("climate", None, "climate.living_room", "Living room thermostat"),
            "low_risk_control_proposed",
        )
        self.assertIn("explicitSensorRow", BROWSER)


if __name__ == "__main__":
    unittest.main()
