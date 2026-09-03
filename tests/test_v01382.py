import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class AutomationStudioDraftRecoveryReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.136"', CONFIG)
        self.assertIn('version="0.13.136"', MAIN)
        self.assertIn("HUD 0.13.136", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.136")

    def test_recovery_is_local_expiring_and_size_bounded(self):
        self.assertIn('localDraftKey="zbrano.automation-studio.unsaved.v1"', WORKSPACE)
        self.assertIn("localDraftMaxAge=7*24*60*60*1000", WORKSPACE)
        self.assertIn("localDraftMaxBytes=100000", WORKSPACE)
        self.assertIn("localStorage.setItem(localDraftKey,payload)", WORKSPACE)
        self.assertIn("raw.length>localDraftMaxBytes", WORKSPACE)

    def test_recovery_restores_and_flushes_pending_edits(self):
        self.assertIn("function recoverLocalEditorDraft(payload)", WORKSPACE)
        self.assertIn('window.addEventListener("pagehide",commitEditorHistory)', WORKSPACE)
        self.assertIn("Recovered unsaved flow from", WORKSPACE)
        self.assertIn("renderStudioInspector();resetEditorHistory()", WORKSPACE)

    def test_real_page_reload_recovery_is_browser_covered(self):
        self.assertIn('page.reload({waitUntil: "domcontentloaded"})', BROWSER)
        self.assertIn('/Recovered unsaved flow/i', BROWSER)
        self.assertIn('inputValue(), "27"', BROWSER)

    def test_release_history_includes_v01381(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.135")


if __name__ == "__main__":
    unittest.main()
