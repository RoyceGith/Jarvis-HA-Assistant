import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class SimpleDeviceCategoryReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.197")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.196")

    def test_only_two_plain_device_types_are_offered(self):
        self.assertIn('<option value="informational" selected>Sensor device</option>', HTML)
        self.assertIn('<option value="controlled">Control device</option>', HTML)
        for obsolete in ("A low-impact device", "A device that needs care", "A sensitive or security device"):
            self.assertNotIn(obsolete, HTML)
        self.assertIn('value==="informational"?"Sensor device":"Control device"', WORKSPACE)

    def test_old_saved_categories_normalize_to_control_device(self):
        self.assertIn('item.risk_level==="informational"?"informational":"controlled"', WORKSPACE)

    def test_irrelevant_action_safety_fields_are_hidden(self):
        self.assertIn('const actionOnlyFields=new Set(["automation-max-actions","automation-notify-action"])', WORKSPACE)
        self.assertIn('id==="automation-reversible-only"&&!controlDevice', WORKSPACE)
        self.assertIn('"#studio-automation-reversible-only").count(), 0', BROWSER)
        self.assertIn('"#studio-automation-notify-action").count(), 0', BROWSER)


if __name__ == "__main__":
    unittest.main()
