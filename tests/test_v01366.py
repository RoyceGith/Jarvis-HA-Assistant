import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
SCHEMAS = (ROOT / "jarvis/app/schemas.py").read_text(encoding="utf-8")
AUTOMATIONS = (ROOT / "jarvis/app/domains/automations.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
FLOW = (ROOT / "jarvis/app/static/js/automations/flow.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class AdvancedAutomationWorkflowReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.145"', CONFIG)
        self.assertIn('version="0.13.145"', MAIN)
        self.assertIn("HUD 0.13.145", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.145")

    def test_bounded_workflow_schema_is_present(self):
        for marker in ("AutomationTriggerRequest", "AutomationConditionRequest", "AutomationActionRequest"):
            self.assertIn(f"class {marker}", SCHEMAS)
        self.assertIn("triggers: list[AutomationTriggerRequest]", SCHEMAS)
        self.assertIn("conditions: list[AutomationConditionRequest]", SCHEMAS)
        self.assertIn("actions: list[AutomationActionRequest]", SCHEMAS)

    def test_engine_supports_compatibility_and_advanced_evaluation(self):
        for marker in ("def _automation_triggers", "def _automation_conditions", "def _automation_actions", "def _automation_context_conditions_match"):
            self.assertIn(marker, AUTOMATIONS)
        self.assertIn("for step in actions:", AUTOMATIONS)
        self.assertIn('pending_key = f"{item.get(\'id\')}:{entity_id}"', AUTOMATIONS)

    def test_visual_inspector_has_repeatable_workflow_rows(self):
        self.assertIn("automation-workflow-steps", WORKSPACE)
        self.assertIn('data-workflow-add="${collection}"', WORKSPACE)
        self.assertIn("condition_mode", WORKSPACE)
        self.assertIn('i?"AND":"DO"', FLOW)
        self.assertIn("automation-flow-node-row", FLOW)

    def test_release_history_includes_v01365(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.144")


if __name__ == "__main__":
    unittest.main()
