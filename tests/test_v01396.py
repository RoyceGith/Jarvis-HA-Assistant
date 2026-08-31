import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
FLOW = (ROOT / "jarvis/app/static/js/automations/flow.js").read_text(encoding="utf-8")
CSS = (ROOT / "jarvis/app/static/css/automation-studio.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class AutomationStudioDropReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.103"', CONFIG)
        self.assertIn('version="0.13.103"', MAIN)
        self.assertIn("HUD 0.13.103", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.103")

    def test_drop_creates_real_workflow_blocks(self):
        self.assertIn("function addStudioBlock(kind)", WORKSPACE)
        self.assertIn("workflowDraft.triggers.push(trigger())", WORKSPACE)
        self.assertIn("workflowDraft.conditions.push(condition())", WORKSPACE)
        self.assertIn("workflowDraft.branches.push", WORKSPACE)
        self.assertIn("workflowDraft.actions.push(action())", WORKSPACE)
        self.assertIn("addStudioBlock(kind)", WORKSPACE)

    def test_incomplete_dropped_blocks_render_without_bypassing_validation(self):
        self.assertIn("const visualSnapshot=", WORKSPACE)
        self.assertIn("cloneEditorValue(workflowDraft.triggers)", WORKSPACE)
        self.assertIn("Complete its settings before saving", WORKSPACE)
        self.assertIn("automation-flow-node-row", FLOW)
        self.assertIn("Choose a trigger entity", FLOW)
        self.assertIn("automation-flow-node-row", CSS)

    def test_release_history_includes_v01395(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.102")


if __name__ == "__main__":
    unittest.main()
