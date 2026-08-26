from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
AUTOMATIONS = (ROOT / "jarvis/app/domains/automations.py").read_text(encoding="utf-8")


class ProductDefaultSeparationTests(unittest.TestCase):
    def test_product_defaults_do_not_embed_owner_entity_ids(self):
        for entity_id in (
            "binary_sensor.workshop_presence",
            "sensor.workshop_temperature",
            "sensor.workshop_humidity",
            "sensor.workshop_co2",
            "sensor.workshop_voc",
            "sensor.workshop_pm25",
            "binary_sensor.workshop_door",
            "binary_sensor.workshop_window",
            "switch.workshop_equipment",
            "sensor.workshop_illuminance",
            "climate.workshop",
            "fan.workshop_extractor",
            "light.workshop",
        ):
            self.assertNotIn(entity_id, WORKSPACE)
            self.assertNotIn(entity_id, HTML)

    def test_quick_designs_use_installed_entity_inventory(self):
        for marker in (
            "function inventoryMatches",
            'state.settings?.presence_entity||""',
            'domains:["climate"]',
            'domains:["light"]',
            'deviceClasses:["temperature"]',
            'deviceClasses:["illuminance"]',
            'execution_policy:"approval_required"',
        ):
            self.assertIn(marker, WORKSPACE)
        self.assertIn('<strong>Comfort advisor</strong>', HTML)
        self.assertIn("Matches available presence, temperature, humidity, and climate entities", HTML)

    def test_existing_stored_automation_defaults_remain_compatible(self):
        self.assertIn('"presence_entity": ""', AUTOMATIONS)
        self.assertIn('"operating_mode": "suggest_only"', AUTOMATIONS)
        self.assertIn('"automations": data.get("automations")', AUTOMATIONS)


if __name__ == "__main__":
    unittest.main()
