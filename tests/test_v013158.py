import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FLOW = (ROOT / "zbrano/app/static/js/automations/flow.js").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "zbrano/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
CSS = (ROOT / "zbrano/app/static/css/automation-studio.css").read_text(encoding="utf-8")
AUTOMATIONS = (ROOT / "zbrano/app/domains/automations.py").read_text(encoding="utf-8")
BROWSER = (ROOT / "zbrano/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class IndependentAutomationBranchesReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.218")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.217")

    def test_branch_title_cards_are_removed_and_conditions_identify_paths(self):
        self.assertIn("if(result)result.remove()", FLOW)
        self.assertIn('conditionIndex?"AND":fallback?"ELSE":index?"ELSE IF":"IF"', FLOW)
        self.assertIn("firstChecks.length?firstChecks:[newBranchCondition()]", WORKSPACE)
        self.assertIn("conditions:[newBranchCondition()]", WORKSPACE)

    def test_each_speaking_path_owns_its_message(self):
        self.assertIn("suggestion:firstMessage", WORKSPACE)
        self.assertIn("message_enabled:Boolean(firstMessage)", WORKSPACE)
        self.assertIn("function branchMessageEditor", WORKSPACE)
        self.assertIn("message task: write its message", WORKSPACE)
        self.assertNotIn("Leave blank to use the main message", WORKSPACE)
        self.assertIn('"" if _automation_branches(item) else item.get("proposal_template")', AUTOMATIONS)

    def test_branch_messages_are_independent_from_action_authority(self):
        self.assertGreaterEqual(FLOW.count('["observe","autonomous"]'), 1)
        self.assertIn("const showMessages=true", WORKSPACE)
        self.assertIn("friendlyResultsStage(branches,name,visual,interactive,true)", FLOW)
        self.assertIn('branch-message', BROWSER)

    def test_task_menu_opens_upward_and_is_browser_checked(self):
        self.assertIn(".automation-flow-branch-task-menu .automation-flow-branch-task-choices", CSS)
        self.assertIn("bottom:calc(100% + .3rem)", CSS)
        self.assertIn("taskChoicesBox.y<taskSummaryBox.y", BROWSER)


if __name__ == "__main__":
    unittest.main()
