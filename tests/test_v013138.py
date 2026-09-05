import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (ROOT / "jarvis" / "app" / "static" / "js" / "automations" / "workspace.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis" / "tests" / "browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis" / "release_manifest.json").read_text(encoding="utf-8"))


class V013138AdditionalTriggerEntityPickerTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.162")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.161")

    def test_additional_trigger_maps_to_its_relevant_field(self):
        self.assertIn('const workflowIndex=index-1,item=workflowDraft.triggers[workflowIndex]||{},preferredField=', WORKSPACE)
        for mapping in ('entity:"entity_id"', 'time:"at"', 'sun:"sun_event"', 'interval:"interval_minutes"', 'one_time:"one_time_at"'):
            self.assertIn(mapping, WORKSPACE)
        self.assertIn('[data-trigger-field="${preferredField}"]', WORKSPACE)

    def test_browser_clicks_second_trigger_and_waits_for_entities(self):
        self.assertIn("const secondTriggerEntity=", BROWSER)
        self.assertIn("document.activeElement?.matches", BROWSER)
        self.assertIn("secondTriggerEntity.locator", BROWSER)


if __name__ == "__main__":
    unittest.main()
