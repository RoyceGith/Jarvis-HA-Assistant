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


class AutomationDuplicateReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.160"', CONFIG)
        self.assertIn('version="0.13.160"', MAIN)
        self.assertIn("HUD 0.13.160", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.160")

    def test_every_library_rule_exposes_duplicate(self):
        self.assertIn('data-auto-duplicate="${esc(item.id)}"', WORKSPACE)
        self.assertIn(">Duplicate</button>", WORKSPACE)

    def test_copy_is_independent_disabled_and_unsaved(self):
        self.assertIn("const copy=cloneEditorValue(item)", WORKSPACE)
        self.assertIn('copy.id=""', WORKSPACE)
        self.assertIn('copy.name=`${item.name||"Automation"} copy`', WORKSPACE)
        self.assertIn("copy.enabled=false", WORKSPACE)
        self.assertIn("copy.review_required=true", WORKSPACE)
        self.assertIn("markEditorAsUnsaved()", WORKSPACE)

    def test_duplicate_protects_an_existing_open_draft(self):
        self.assertIn('confirmEditorReplacement("duplicate another automation")', WORKSPACE)
        self.assertIn("Independent disabled copy ready", WORKSPACE)

    def test_browser_exercises_identity_state_and_discard_protection(self):
        self.assertIn('data-auto-duplicate="active-flow"', BROWSER)
        self.assertIn('locator("#automation-edit-id").inputValue()', BROWSER)
        self.assertIn('"Active lighting copy"', BROWSER)
        self.assertIn('locator("#automation-enabled").isChecked()', BROWSER)
        self.assertIn("duplicateDialog.accept()", BROWSER)

    def test_release_history_includes_v01388(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.159")


if __name__ == "__main__":
    unittest.main()
