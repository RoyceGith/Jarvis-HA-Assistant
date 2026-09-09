import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
ENTITY_SEARCH = (ROOT / "jarvis/app/static/js/automations/entity-search.js").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class WhenCardEntityPickerReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.196"', CONFIG)
        self.assertIn('version="0.13.196"', MAIN)
        self.assertIn("HUD 0.13.196", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.196")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.195")

    def test_entity_picker_can_attach_to_the_visual_trigger_clone(self):
        self.assertIn("function attach(input)", ENTITY_SEARCH)
        self.assertIn("window.zbranoEntitySearch={attach", ENTITY_SEARCH)
        self.assertIn('entityPickerFieldIds=new Set(["automation-trigger-entity","automation-presence","automation-signals","automation-action-entity"])', WORKSPACE)
        self.assertIn("window.zbranoEntitySearch?.attach(input)", WORKSPACE)
        self.assertIn('preferredField=({entity:"entity_id",time:"at",sun:"sun_event",interval:"interval_minutes",one_time:"one_time_at"})', WORKSPACE)

    def test_browser_covers_search_selection_and_trigger_sync(self):
        self.assertIn('fill("Browser Fixture 1")', BROWSER)
        self.assertIn('hasText:"sensor.browser_fixture_1"', BROWSER)
        self.assertIn('inputValue(), "sensor.browser_fixture_1"', BROWSER)
        self.assertIn("const secondTriggerEntity=", BROWSER)


if __name__ == "__main__":
    unittest.main()
