import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEARCH = (ROOT / "jarvis/app/static/js/automations/entity-search.js").read_text(encoding="utf-8")
CSS = (ROOT / "jarvis/app/static/css/entity-columns.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class EntityPickerReadingReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.186")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.185")

    def test_picker_retains_reading_fields(self):
        for field in ("state", "unit", "current_temperature", "temperature_unit"):
            self.assertIn(field, SEARCH)
        self.assertIn("const readingFor=item=>", SEARCH)

    def test_result_has_distinct_current_value_badge(self):
        self.assertIn('reading.className="automation-entity-reading"', SEARCH)
        self.assertIn("Current value:", SEARCH)
        self.assertIn(".automation-entity-reading", CSS)

    def test_readings_participate_in_search(self):
        self.assertIn("${readingFor(item)}", SEARCH)

    def test_browser_verifies_sensor_and_climate_readings(self):
        self.assertIn("20\\.1\\s*°C", BROWSER)
        self.assertIn("26\\.2\\s*°C", BROWSER)
        self.assertGreaterEqual(BROWSER.count('.automation-entity-reading'), 2)


if __name__ == "__main__":
    unittest.main()
