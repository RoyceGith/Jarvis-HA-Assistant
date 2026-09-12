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


class BranchQuickBuilderReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.241"', CONFIG)
        self.assertIn('version="0.13.241"', MAIN)
        self.assertIn("HUD 0.13.241", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.241")

    def test_each_interactive_path_has_direct_build_controls(self):
        for marker in (
            "flowBranchAddCondition",
            "automation-flow-branch-task-menu",
            "flowBranchTaskTemplate",
            'taskLabel.textContent="THEN DO"',
            'checkLabel.textContent=fallback?"FALLBACK":"USE THIS WHEN"',
        ):
            self.assertIn(marker, FLOW)

    def test_branch_task_menu_exposes_supported_presets(self):
        for marker in (
            '["turn_on","Turn on"]',
            '["set_temperature","Set temperature"]',
            '["notification","Send notification"]',
            '["delay","Wait"]',
            '["wait","Wait until"]',
            '["service","Custom action"]',
        ):
            self.assertIn(marker, FLOW)

    def test_quick_add_uses_selected_position_and_focused_settings(self):
        for marker in (
            "branchQuickInsertion(kind,branchIndex)",
            "addBranchActionTemplate(branchIndex,template,insertionIndex)",
            'focusSelectedFlowEditor("branch-condition",target,branchIndex)',
            'focusSelectedFlowEditor("branch-action",target,branchIndex)',
            "flowBranchConditionTemplate",
            "flowBranchTaskTemplate",
        ):
            self.assertIn(marker, WORKSPACE if marker.startswith(("branch", "add", "focus")) else FLOW)

    def test_touch_friendly_controls_are_styled(self):
        self.assertIn(".automation-flow-branch-add", STYLES)
        self.assertIn(".automation-flow-branch-task-choices", STYLES)
        self.assertIn("cursor:pointer", STYLES)

    def test_release_history_includes_v013106(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.240")


if __name__ == "__main__":
    unittest.main()
