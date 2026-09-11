import ast
from datetime import datetime
import json
from pathlib import Path
import time
from types import SimpleNamespace
from typing import Any
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "zbrano/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
STUDIO_CSS = (ROOT / "zbrano/app/static/css/automation-studio.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))
AUTOMATIONS = (ROOT / "zbrano/app/domains/automations.py").read_text(encoding="utf-8")


def load_test_flow(states):
    names = {
        "_automation_triggers", "_automation_conditions", "_automation_actions", "_automation_branches",
        "_automation_condition_matches", "_automation_condition_group_matches", "_automation_context_conditions_match",
        "_automation_select_branch", "_automation_presence_confirmed", "_automation_effective_policy", "_automation_test_flow",
        "_automation_schedule_due",
    }
    constants = {"AUTOMATION_POLICY_ORDER", "AUTOMATION_GLOBAL_POLICIES"}
    tree = ast.parse(AUTOMATIONS)
    selected = [node for node in tree.body if (
        isinstance(node, ast.FunctionDef) and node.name in names
    ) or (
        isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id in constants for target in node.targets)
    )]
    namespace = {
        "Any": Any,
        "ha_ws": SimpleNamespace(state_cache=states),
        "datetime": datetime,
        "time": time,
        "_automation_expected_zone": lambda data, item: "",
        "_automation_context_key": lambda value: str(value or "").casefold(),
    }
    exec(compile(ast.Module(body=selected, type_ignores=[]), "automations.py", "exec"), namespace)
    return namespace["_automation_test_flow"]


class AutomationTestFlowReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.217"', CONFIG)
        self.assertIn('version="0.13.217"', MAIN)
        self.assertIn("HUD 0.13.217", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.217")

    def test_dry_run_uses_live_state_without_executing_actions(self):
        test_flow = load_test_flow({
            "sensor.room_temperature": {"state": "28"},
            "binary_sensor.window": {"state": "off"},
        })
        item = {
            "triggers": [{"entity_id": "sensor.room_temperature", "operator": "above", "value": "25"}],
            "conditions": [{"entity_id": "binary_sensor.window", "operator": "equals", "value": "off"}],
            "condition_mode": "all",
            "actions": [{"kind": "service", "entity_id": "climate.room", "service": "climate.turn_on"}],
            "execution_policy": "suggest",
        }
        data = {"area_context": {"entities": []}}
        result = test_flow(item, {"operating_mode": "suggest_only", "require_presence": False}, data)
        self.assertTrue(result["safe_dry_run"])
        self.assertEqual(result["actions_executed"], 0)
        self.assertEqual(result["status"], "ready")
        self.assertEqual([step["kind"] for step in result["trace"]], ["trigger", "context", "decision", "action"])
        self.assertIn("Would call climate.turn_on", result["trace"][-1]["detail"])

    def test_change_trigger_waits_for_a_real_event(self):
        result = load_test_flow({"light.room": {"state": "on"}})(
            {"triggers": [{"entity_id": "light.room", "operator": "changes_to", "value": "on"}]},
            {"operating_mode": "suggest_only", "require_presence": False},
            {"area_context": {"entities": []}},
        )
        self.assertEqual(result["status"], "waiting_for_event")
        self.assertEqual(result["trace"][0]["status"], "waiting")

    def test_test_flow_is_wired_graphically(self):
        self.assertIn('@app.post("/api/automations/test-flow")', MAIN)
        self.assertIn('id="automation-studio-test"', HTML)
        self.assertIn('id="automation-studio-test-results"', HTML)
        self.assertIn('api("api/automations/test-flow"', WORKSPACE)
        self.assertIn("0 actions executed", WORKSPACE)
        self.assertIn(".automation-studio-test-step", STUDIO_CSS)

    def test_release_history_includes_v01369(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.216")


if __name__ == "__main__":
    unittest.main()
