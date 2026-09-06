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


class ContextualAutomationInspectorReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.169"', CONFIG)
        self.assertIn('version="0.13.169"', MAIN)
        self.assertIn("HUD 0.13.169", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.169")

    def test_primary_trigger_fields_are_filtered_by_type_and_operator(self):
        self.assertIn("function inspectorFields(panelConfig)", WORKSPACE)
        for kind in ("entity", "time", "sun", "interval", "one_time"):
            self.assertIn(f"{kind}:new Set", WORKSPACE)
        self.assertIn('operator!=="any_change"', WORKSPACE)
        self.assertIn('fields.add("automation-trigger-value")', WORKSPACE)

    def test_dynamic_workflow_conditions_and_actions_remain_contextual(self):
        self.assertIn('function triggerStepHtml(item,attributes)', WORKSPACE)
        self.assertIn('function conditionStepHtml(item,attributes)', WORKSPACE)
        self.assertIn('function actionStepHtml(item,attributes)', WORKSPACE)
        self.assertIn('if(field==="kind")renderStudioInspector()', WORKSPACE)

    def test_browser_checks_irrelevant_fields_are_absent(self):
        self.assertIn('studio-automation-trigger-sun-event', BROWSER)
        self.assertIn('studio-automation-trigger-at', BROWSER)
        self.assertIn('studio-automation-trigger-value', BROWSER)
        self.assertIn('selectOption("any_change")', BROWSER)

    def test_release_history_includes_v013117(self):
        self.assertEqual(MANIFEST["history_backfill"][-52]["version"], "0.13.117")


if __name__ == "__main__":
    unittest.main()
