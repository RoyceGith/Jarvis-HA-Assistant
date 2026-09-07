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


class BranchConditionPresetReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.189"', CONFIG)
        self.assertIn('version="0.13.189"', MAIN)
        self.assertIn("HUD 0.13.189", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.189")

    def test_canvas_offers_direct_path_creation(self):
        self.assertIn("flowAddBranch", FLOW)
        self.assertIn("automation-flow-add-path", FLOW)
        self.assertIn("function addBranchPath()", WORKSPACE)
        self.assertIn("fallbackIndex", WORKSPACE)
        self.assertIn('locator("[data-branch-add]")', BROWSER)

    def test_if_menu_offers_typed_condition_presets(self):
        for marker in (
            '["entity","Device or sensor"]',
            '["time_window","Time of day"]',
            '["weekday","Day of week"]',
            '["sun","Sunrise / sunset"]',
            "flowBranchConditionTemplate",
        ):
            self.assertIn(marker, FLOW)

    def test_presets_preserve_position_and_focus(self):
        for marker in (
            'newBranchCondition(template="entity")',
            'addBranchCondition(branchIndex,insertionIndex,template="entity")',
            "branchQuickInsertion(\"branch-condition\",branchIndex)",
            'focusSelectedFlowEditor("branch-condition",target,branchIndex)',
        ):
            self.assertIn(marker, WORKSPACE)

    def test_condition_menu_and_path_control_are_styled(self):
        self.assertIn(".automation-flow-add-path", STYLES)
        self.assertIn(".automation-flow-branch-condition-menu", STYLES)
        self.assertIn(".automation-flow-branch-condition-choices", STYLES)

    def test_release_history_includes_v013107(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.188")


if __name__ == "__main__":
    unittest.main()
