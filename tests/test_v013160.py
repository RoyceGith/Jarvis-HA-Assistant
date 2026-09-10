import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENTITY_SEARCH = (ROOT / "jarvis/app/static/js/automations/entity-search.js").read_text(encoding="utf-8")
FLOW = (ROOT / "jarvis/app/static/js/automations/flow.js").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class BranchTaskEntityNameReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.200")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.199")

    def test_entity_picker_synchronizes_nested_editors(self):
        input_event = 'input.dispatchEvent(new Event("input",{bubbles:true}))'
        change_event = 'input.dispatchEvent(new Event("change",{bubbles:true}))'
        self.assertIn(input_event, ENTITY_SEARCH)
        self.assertIn(change_event, ENTITY_SEARCH)
        self.assertLess(ENTITY_SEARCH.index(input_event), ENTITY_SEARCH.index(change_event))

    def test_flow_never_presents_a_partial_entity_query_as_a_device_name(self):
        self.assertIn("function validEntity(value)", FLOW)
        self.assertIn('validEntity(item.entity_id)?name(item.entity_id):"Choose a device"', FLOW)

    def test_incomplete_task_entities_are_not_saved(self):
        self.assertIn("function validEntityId(value)", WORKSPACE)
        self.assertIn("Boolean(validEntityId(item.entity_id)&&item.service)", WORKSPACE)
        self.assertIn("select a complete device name", WORKSPACE)

    def test_browser_selects_and_displays_the_complete_device_name(self):
        self.assertIn('branchActionEntity.fill("Browser Fixture Li")', BROWSER)
        self.assertIn('hasText:"Browser Fixture Light"', BROWSER)
        self.assertIn('/Browser Fixture Light/i', BROWSER)


if __name__ == "__main__":
    unittest.main()
