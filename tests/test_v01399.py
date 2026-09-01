import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
FLOW = (ROOT / "jarvis/app/static/js/automations/flow.js").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
AUTOMATIONS = (ROOT / "jarvis/app/domains/automations.py").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "jarvis/tests/test_app_integration.py").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class AppSheetStyleAutomationStudioReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.113"', CONFIG)
        self.assertIn('version="0.13.113"', MAIN)
        self.assertIn("HUD 0.13.113", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.113")

    def test_canvas_renders_independent_staged_cards_and_logic_control(self):
        for marker in (
            "automation-flow-stage",
            "automation-flow-node-row",
            "automation-flow-logic-select",
            "dataset.flowIndex",
            '"WHEN THIS HAPPENS"',
            '"RUN THIS PROCESS"',
            '"DO THESE TASKS"',
        ):
            self.assertIn(marker, FLOW)
        self.assertIn('workflowDraft.trigger_mode=triggerLogic.value==="all"?"all":"any"', WORKSPACE)

    def test_and_relationship_is_persisted_and_enforced(self):
        self.assertIn('payload["trigger_mode"] = "all"', AUTOMATIONS)
        self.assertIn("_automation_trigger_group_active", AUTOMATIONS)
        self.assertIn('"trigger_mode": "all"', INTEGRATION)
        self.assertIn('self.assertEqual(reloaded["trigger_mode"], "all")', INTEGRATION)

    def test_release_history_includes_v01398(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.112")


if __name__ == "__main__":
    unittest.main()
