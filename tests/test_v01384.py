import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "zbrano/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
STYLE = (ROOT / "zbrano/app/static/css/automation-studio.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "zbrano/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class AutomationStudioDirtyStateReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.247"', CONFIG)
        self.assertIn('version="0.13.247"', MAIN)
        self.assertIn("HUD 0.13.247", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.247")

    def test_unsaved_state_is_visible_and_derived_from_baseline(self):
        self.assertIn('id="automation-studio-dirty"', HTML)
        self.assertIn("Unsaved changes", HTML)
        self.assertIn(".automation-studio-dirty", STYLE)
        self.assertIn("function editorHasUnsavedChanges()", WORKSPACE)
        self.assertIn("JSON.stringify(editorHistoryState())!==editorHistoryBaseline", WORKSPACE)

    def test_replacement_paths_share_one_confirmation_contract(self):
        self.assertIn("function confirmEditorReplacement(action)", WORKSPACE)
        self.assertIn('confirm(`Discard unsaved automation changes and ${action}?`)', WORKSPACE)
        for action in ("load this template", "open another automation", "cancel editing", "start a new flow"):
            self.assertIn(action, WORKSPACE)

    def test_templates_and_recovery_remain_dirty_until_saved_or_discarded(self):
        self.assertIn("fillEditor(templates[name]);markEditorAsUnsaved()", WORKSPACE)
        self.assertIn("recoverLocalEditorDraft(localDraftRecovery)", WORKSPACE)
        self.assertIn("persistLocalEditorDraft(current)", WORKSPACE)

    def test_browser_confirms_and_preserves_a_real_dirty_flow(self):
        self.assertIn('locator("#automation-studio-dirty").isVisible()', BROWSER)
        self.assertIn('page.waitForEvent("dialog")', BROWSER)
        self.assertIn('/Discard unsaved automation changes/i', BROWSER)
        self.assertIn("await dialog.dismiss()", BROWSER)

    def test_release_history_includes_v01383(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.246")


if __name__ == "__main__":
    unittest.main()
