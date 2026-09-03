import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FLOW = (ROOT / "jarvis/app/static/js/automations/flow.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class AutomationObjectiveTaskSeparationTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.132")

    def test_objective_is_not_used_as_process_task(self):
        self.assertIn('text(automation.proposal_template,"Choose a suggestion or task")', FLOW)
        self.assertNotIn('text(automation.proposal_template,text(automation.objective', FLOW)

    def test_previous_release_is_in_history(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.131")


if __name__ == "__main__":
    unittest.main()
