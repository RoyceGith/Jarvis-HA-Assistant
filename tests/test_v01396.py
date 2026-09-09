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
        self.assertIn('version: "0.13.198"', CONFIG)
        self.assertIn('version="0.13.198"', MAIN)
        self.assertIn("HUD 0.13.198", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.198")

    def test_drop_creates_real_workflow_blocks(self):
        self.assertIn("function addStudioBlock(kind,insertionIndex=null)", WORKSPACE)
        self.assertIn('items.splice(target,0,trigger())', WORKSPACE)
        self.assertIn('workflowDraft.conditions.splice(target,0,condition())', WORKSPACE)
        self.assertIn('workflowDraft.branches.splice(target,0', WORKSPACE)
        self.assertIn('items.splice(target,0,action())', WORKSPACE)
        self.assertIn('addStudioBlock(kind,target&&target.kind===kind?target.index:null)', WORKSPACE)

    def test_incomplete_dropped_blocks_render_without_bypassing_validation(self):
        self.assertIn("const visualSnapshot=", WORKSPACE)
        self.assertIn("cloneEditorValue(workflowDraft.triggers)", WORKSPACE)
        self.assertIn("Complete its settings before saving", WORKSPACE)
        self.assertIn("automation-flow-node-row", FLOW)
        self.assertIn("Choose a device or sensor", FLOW)
        self.assertIn("automation-flow-node-row", CSS)

    def test_release_history_includes_v01395(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.197")


if __name__ == "__main__":
    unittest.main()
