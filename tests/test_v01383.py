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


class AutomationStudioLiveValidationReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.235"', CONFIG)
        self.assertIn('version="0.13.235"', MAIN)
        self.assertIn("HUD 0.13.235", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.235")

    def test_validation_surface_and_canvas_markers_exist(self):
        self.assertIn('id="automation-studio-validation"', HTML)
        self.assertIn(".automation-studio-validation", STYLE)
        self.assertIn(".automation-flow-node.has-validation-error", STYLE)
        self.assertIn('content: "Needs attention"', STYLE)

    def test_draft_structure_is_validated_and_actionless_flows_remain_valid(self):
        self.assertIn("function editorValidationIssues()", WORKSPACE)
        self.assertIn("The extra action details have an invalid format", WORKSPACE)
        self.assertIn("Boolean(primaryEntity)!==Boolean(primaryService)", WORKSPACE)
        self.assertNotIn('if(!primaryEntity&&!primaryService)add(', WORKSPACE)

    def test_issue_navigation_and_action_guards_are_wired(self):
        self.assertIn("function focusEditorIssue(issue)", WORKSPACE)
        self.assertIn('closest("[data-validation-kind]")', WORKSPACE)
        self.assertIn("before testing", WORKSPACE)
        self.assertIn("before saving", WORKSPACE)

    def test_browser_completes_and_clears_a_real_issue(self):
        self.assertIn('locator("#automation-studio-validation:not([hidden])")', BROWSER)
        self.assertIn('locator(\'[data-validation-kind="trigger"]\')', BROWSER)
        self.assertIn('locator("#studio-automation-trigger-entity").fill', BROWSER)
        self.assertIn('locator("#automation-studio-validation").isHidden()', BROWSER)
        self.assertIn('/before testing/i', BROWSER)
        self.assertIn('/before saving/i', BROWSER)

    def test_release_history_includes_v01382(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.234")


if __name__ == "__main__":
    unittest.main()
