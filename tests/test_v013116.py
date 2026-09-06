import ast
from datetime import datetime
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
SCHEMAS = (ROOT / "jarvis/app/schemas.py").read_text(encoding="utf-8")
AUTOMATIONS = (ROOT / "jarvis/app/domains/automations.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
FLOW = (ROOT / "jarvis/app/static/js/automations/flow.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def load_automation_functions(states):
    names = {
        "_automation_condition_matches", "_automation_record_value",
        "_automation_condition_group_matches", "_automation_conditions",
        "_automation_actions", "_automation_branches", "_automation_select_branch",
        "_automation_branch_suggestion", "_automation_branch_delivery",
    }
    tree = ast.parse(AUTOMATIONS)
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {
        "Any": Any, "datetime": datetime, "time": time,
        "ha_ws": SimpleNamespace(state_cache=states),
    }
    exec(compile(ast.Module(body=selected, type_ignores=[]), "automations.py", "exec"), namespace)
    return namespace


class SingleFlowConditionalSuggestionReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.172"', CONFIG)
        self.assertIn('version="0.13.172"', MAIN)
        self.assertIn("HUD 0.13.172", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.172")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.171")

    def test_live_temperature_can_be_compared_with_thermostat_target(self):
        now = time.time()
        states = {
            "sensor.living_room_temperature": {"state": "27", "last_changed": datetime.fromtimestamp(now - 120).astimezone().isoformat()},
            "climate.living_room": {"state": "cool", "attributes": {"temperature": 25}, "last_changed": datetime.fromtimestamp(now - 1000).astimezone().isoformat()},
        }
        functions = load_automation_functions(states)
        matches = functions["_automation_condition_group_matches"]
        conditions = [
            {"kind": "entity_compare", "entity_id": "sensor.living_room_temperature", "operator": "above", "compare_entity_id": "climate.living_room", "compare_attribute": "temperature"},
            {"kind": "entity", "entity_id": "climate.living_room", "operator": "not_equals", "value": "off", "for_seconds": 900},
        ]
        matched, detail = matches(conditions, "all")
        self.assertTrue(matched)
        self.assertIn("climate.living_room.temperature=25", detail)
        self.assertIn("for 900s", detail)

    def test_first_matching_path_returns_its_own_suggestion(self):
        now = time.time()
        states = {
            "sensor.living_room_temperature": {"state": "27", "last_changed": datetime.fromtimestamp(now - 120).astimezone().isoformat()},
            "climate.living_room": {"state": "cool", "attributes": {"temperature": 25}, "last_changed": datetime.fromtimestamp(now - 1000).astimezone().isoformat()},
        }
        select_branch = load_automation_functions(states)["_automation_select_branch"]
        automation = {"branches": [
            {"name": "Start cooling", "suggestion": "Switch on the air conditioner?", "condition_mode": "all", "conditions": [{"kind": "entity", "entity_id": "climate.living_room", "operator": "equals", "value": "off"}], "actions": [{"kind": "service", "entity_id": "climate.living_room", "service": "climate.turn_on"}]},
            {"name": "Check openings", "suggestion": "Check for open doors or windows.", "condition_mode": "all", "conditions": [{"kind": "entity_compare", "entity_id": "sensor.living_room_temperature", "operator": "above", "compare_entity_id": "climate.living_room", "compare_attribute": "temperature"}, {"kind": "entity", "entity_id": "climate.living_room", "operator": "not_equals", "value": "off", "for_seconds": 900}], "actions": []},
        ]}
        matched, _, actions, branch = select_branch(automation)
        suggestion = load_automation_functions(states)["_automation_branch_suggestion"](automation, branch)
        self.assertTrue(matched)
        self.assertEqual(branch, "Check openings")
        self.assertEqual(suggestion, "Check for open doors or windows.")
        self.assertEqual(actions, [])

    def test_studio_exposes_comparison_and_per_path_suggestion(self):
        self.assertIn('value="entity_compare"', WORKSPACE)
        self.assertIn('data-branch-suggestion=', WORKSPACE)
        self.assertIn('compare_attribute', SCHEMAS)
        self.assertIn('txt(branch.suggestion', FLOW)
        self.assertIn('data-condition-field="for_seconds"', BROWSER)
        self.assertIn('fill("1200")', BROWSER)

    def test_each_path_can_choose_its_own_message_delivery(self):
        delivery = load_automation_functions({})["_automation_branch_delivery"]
        automation = {
            "delivery_voice": True,
            "delivery_notification_center": False,
            "delivery_ha_push": True,
            "branches": [
                {"name": "Quiet", "delivery_voice": False, "delivery_notification_center": True, "delivery_ha_push": False},
                {"name": "Legacy"},
            ],
        }
        self.assertFalse(delivery(automation, "Quiet", "delivery_voice"))
        self.assertTrue(delivery(automation, "Quiet", "delivery_notification_center"))
        self.assertFalse(delivery(automation, "Quiet", "delivery_ha_push"))
        self.assertTrue(delivery(automation, "Legacy", "delivery_voice"))
        self.assertFalse(delivery(automation, "Legacy", "delivery_notification_center"))


if __name__ == "__main__":
    unittest.main()
