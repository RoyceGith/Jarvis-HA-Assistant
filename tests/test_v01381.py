import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
STYLE = (ROOT / "jarvis/app/static/css/automation-studio.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class AutomationStudioEditHistoryReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.147"', CONFIG)
        self.assertIn('version="0.13.147"', MAIN)
        self.assertIn("HUD 0.13.147", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.147")

    def test_visible_history_controls_are_accessible(self):
        self.assertIn('id="automation-studio-undo"', HTML)
        self.assertIn('id="automation-studio-redo"', HTML)
        self.assertIn('aria-label="Flow edit history"', HTML)
        self.assertIn(".automation-studio-history-controls", STYLE)

    def test_history_is_bounded_and_restores_full_editor_state(self):
        self.assertIn("if(editorHistory.length>50)editorHistory.shift()", WORKSPACE)
        self.assertIn("workflowDraft:cloneEditorValue(workflowDraft)", WORKSPACE)
        self.assertIn("workflowDraft=cloneEditorValue(snapshot.workflowDraft||", WORKSPACE)
        self.assertIn("resetEditorHistory()", WORKSPACE)

    def test_keyboard_and_browser_workflow_are_covered(self):
        self.assertIn('if(event.shiftKey)redoEditor();else undoEditor()', WORKSPACE)
        self.assertIn('else if(key==="y")', WORKSPACE)
        self.assertIn('page.locator("#automation-studio-undo").click()', BROWSER)
        self.assertIn('page.locator("#automation-studio-redo").click()', BROWSER)

    def test_release_history_includes_v01380(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.146")


if __name__ == "__main__":
    unittest.main()
