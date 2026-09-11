import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "zbrano/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
FLOW = (ROOT / "zbrano/app/static/js/automations/flow.js").read_text(encoding="utf-8")
STYLES = (ROOT / "zbrano/app/static/css/automation-studio.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "zbrano/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class VisualBranchTaskLaneReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.216"', CONFIG)
        self.assertIn('version="0.13.216"', MAIN)
        self.assertIn("HUD 0.13.216", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.216")

    def test_branches_render_real_task_lanes(self):
        for marker in (
            "function branchesStage(branches,name,visual,interactive)",
            "automation-flow-branch-lane",
            "automation-flow-branch-actions",
            'node("branch-action",ii',
            "NOT CONNECTED — WILL NOT RUN",
        ):
            self.assertIn(marker, FLOW)

    def test_actions_can_be_assigned_and_ordered_in_branches(self):
        for marker in (
            "moveActionToBranch(source,target)",
            "addBranchAction(branchIndex,insertionIndex)",
            'source.kind==="branch-action"',
            'kind==="action"&&target?.kind==="branch-action"',
            "application/x-zbrano-flow-card",
        ):
            self.assertIn(marker, WORKSPACE)

    def test_branch_cards_share_safe_direct_controls(self):
        self.assertIn('kind==="branch-action"', WORKSPACE)
        self.assertIn("Branch task duplicated", WORKSPACE)
        self.assertIn("branch.actions.splice(index,1)", WORKSPACE)
        self.assertIn("is-branch-drop-target", STYLES)
        self.assertIn("automation-flow-branch-empty", STYLES)

    def test_browser_covers_branch_assignment_and_reordering(self):
        self.assertIn('data-flow-branch-drop="0"', BROWSER)
        self.assertIn('data-branch-collection="actions"', BROWSER)
        self.assertIn("Power off task added", BROWSER)
        self.assertIn("Wait 2 sec", BROWSER)
        self.assertIn('data-flow-kind="action"]\').count(), 0', BROWSER)

    def test_release_history_includes_v013104(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.215")


if __name__ == "__main__":
    unittest.main()
