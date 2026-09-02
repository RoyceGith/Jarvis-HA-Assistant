import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
CORE = (ROOT / "jarvis/app/static/js/core.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class ClimateEntityStateReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.118"', CONFIG)
        self.assertIn('version="0.13.118"', MAIN)
        self.assertIn("HUD 0.13.118", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.118")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.117")

    def test_climate_attributes_are_normalized_for_inventory(self):
        for marker in (
            '"target_temperature": attributes.get("temperature")',
            '"target_temperature_low": attributes.get("target_temp_low")',
            '"target_temperature_high": attributes.get("target_temp_high")',
            '"current_temperature": attributes.get("current_temperature")',
            '"hvac_action": attributes.get("hvac_action")',
        ):
            self.assertIn(marker, MAIN)

    def test_entity_table_combines_mode_and_target_without_replacing_state(self):
        self.assertIn("function entityStateLabel(entity)", CORE)
        self.assertIn('return `${state} · set to ${target}`', CORE)
        self.assertIn('return `${state} · set to ${low}–${high}`', CORE)
        self.assertIn("stateCell.textContent = entityStateLabel(entity)", CORE)
        self.assertIn('"cool · set to 25 °C"', BROWSER)
        self.assertIn("/Current 26.2 °C · Action cooling/", BROWSER)


if __name__ == "__main__":
    unittest.main()
