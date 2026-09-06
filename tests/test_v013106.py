import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
FLOW = (ROOT / "jarvis/app/static/js/automations/flow.js").read_text(encoding="utf-8")
STYLES = (ROOT / "jarvis/app/static/css/automation-studio.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class VisualBranchConditionReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.179"', CONFIG)
        self.assertIn('version="0.13.179"', MAIN)
        self.assertIn("HUD 0.13.179", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.179")

    def test_branch_conditions_are_visible_flow_cards(self):
        for marker in (
            "automation-flow-branch-conditions",
            'card.dataset.flowKind="branch-condition"',
            "branchConditionLogic",
            "No checks — use when nothing else matches",
        ):
            self.assertIn(marker, FLOW)

    def test_branch_conditions_support_direct_editing(self):
        for marker in (
            "moveBranchCondition(source,target)",
            'addBranchCondition(branchIndex,insertionIndex,template="entity")',
            'kind==="branch-condition"',
            "Branch condition duplicated",
            "branch.conditions.splice(index,1)",
        ):
            self.assertIn(marker, WORKSPACE)

    def test_branch_condition_drop_targets_are_styled_and_covered(self):
        self.assertIn("automation-flow-branch-conditions.is-branch-drop-target", STYLES)
        self.assertIn('data-branch-collection="conditions"', BROWSER)
        self.assertIn('data-branch-index="1"', BROWSER)
        self.assertIn("moved into the selected outcome", WORKSPACE)

    def test_release_history_includes_v013105(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.178")


if __name__ == "__main__":
    unittest.main()
