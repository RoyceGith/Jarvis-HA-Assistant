import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (ROOT / "zbrano/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
FLOW = (ROOT / "zbrano/app/static/js/automations/flow.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "zbrano/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class WhenCardAndAutomaticFlowReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.227")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.226")

    def test_when_step_has_dedicated_event_choices(self):
        for preset in ("sensor", "power_on", "power_off", "time", "sun", "interval", "one_time"):
            self.assertIn(f'"{preset}"', WORKSPACE)
        self.assertIn("What does this When block watch?", WORKSPACE)
        self.assertIn("POWER ${value.toUpperCase()}", FLOW)
        self.assertIn("Turns ${value}", FLOW)

    def test_inspector_renders_only_the_selected_additional_trigger(self):
        self.assertIn("automation-selected-block-settings", WORKSPACE)
        self.assertIn("workflowIndex=selectedIndex-1", WORKSPACE)
        self.assertIn("items[workflowIndex]", WORKSPACE)
        self.assertIn("This When block", WORKSPACE)
        self.assertIn("'.automation-workflow-step').count(), 1", BROWSER)
        self.assertIn("'#studio-automation-trigger-entity').count(), 0", BROWSER)

    def test_branch_messages_remain_connected_regardless_of_task_authority(self):
        self.assertIn('showMessages=!["observe","autonomous"].includes(a.execution_policy)', FLOW)
        self.assertIn("if(showMessages)flow.append", FLOW)
        self.assertIn("friendlyResultsStage(branches,name,visual,interactive,true)", FLOW)
        self.assertIn('data-flow-kind="branch-message"', BROWSER)


if __name__ == "__main__":
    unittest.main()
