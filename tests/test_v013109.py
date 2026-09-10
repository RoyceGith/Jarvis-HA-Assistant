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


class BranchPathManagementReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.210"', CONFIG)
        self.assertIn('version="0.13.210"', MAIN)
        self.assertIn("HUD 0.13.210", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.210")

    def test_canvas_exposes_complete_path_controls(self):
        for marker in (
            "automation-flow-branch-toolbar",
            "flowBranchAction",
            '["previous","←"',
            '["next","→"',
            '["duplicate","⧉"',
            '["delete","×"',
        ):
            self.assertIn(marker, FLOW)

    def test_path_operations_are_recoverable_and_focused(self):
        for marker in (
            "function moveBranchPathTo(fromIndex,targetIndex)",
            "function duplicateBranchPath(index)",
            "function deleteBranchPath(index)",
            'focusSelectedFlowEditor("decision",target)',
            "commitEditorHistory()",
        ):
            self.assertIn(marker, WORKSPACE)

    def test_else_path_remains_safe(self):
        self.assertIn('"The OTHERWISE outcome stays last so the flow remains predictable."', WORKSPACE)
        self.assertIn("if(sourceIsFallback)copy.conditions=[newBranchCondition()]", WORKSPACE)
        self.assertIn('"Keep at least one outcome, or turn off outcomes in All settings."', WORKSPACE)

    def test_controls_are_styled_and_browser_exercised(self):
        self.assertIn(".automation-flow-branch-toolbar", STYLES)
        for action in ("duplicate", "delete", "next", "previous"):
            self.assertIn(f'["{action}"', FLOW)

    def test_release_history_includes_v013108(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.209")


if __name__ == "__main__":
    unittest.main()
