import ast
import json
from pathlib import Path
from typing import Any
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


def load_action_functions():
    names = {"_automation_actions", "_automation_condition_matches"}
    tree = ast.parse(AUTOMATIONS)
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {"Any": Any}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "automations.py", "exec"), namespace)
    return namespace


class AutomationFlowControlReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.158"', CONFIG)
        self.assertIn('version="0.13.158"', MAIN)
        self.assertIn("HUD 0.13.158", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.158")

    def test_typed_step_schema_is_bounded(self):
        self.assertIn('pattern="^(service|notification|delay|wait_state)$"', SCHEMAS)
        self.assertIn("timeout_seconds: int = Field(default=30, ge=1, le=300)", SCHEMAS)
        self.assertIn("wait_operator", SCHEMAS)

    def test_compatibility_filter_recognizes_all_step_types(self):
        actions = load_action_functions()["_automation_actions"]({"actions": [
            {"kind": "delay", "delay_seconds": 2},
            {"kind": "wait_state", "entity_id": "binary_sensor.ready"},
            {"kind": "service", "entity_id": "light.room", "service": "light.turn_on"},
        ]})
        self.assertEqual([item["kind"] for item in actions], ["delay", "wait_state", "service"])

    def test_engine_and_visual_editor_support_flow_control(self):
        self.assertIn('if kind == "wait_state"', AUTOMATIONS)
        self.assertIn("Wait Until timed out", AUTOMATIONS)
        self.assertIn('value="wait_state"', WORKSPACE)
        self.assertIn("Wait until", WORKSPACE)
        self.assertIn('`Wait ${Number(item.delay_seconds||0)||"?"} sec`', FLOW)

    def test_release_history_includes_v01367(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.157")


if __name__ == "__main__":
    unittest.main()
