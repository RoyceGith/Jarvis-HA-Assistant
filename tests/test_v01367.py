import json
from pathlib import Path
import ast
from types import SimpleNamespace
from typing import Any
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
SCHEMAS = (ROOT / "zbrano/app/schemas.py").read_text(encoding="utf-8")
AUTOMATIONS = (ROOT / "zbrano/app/domains/automations.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "zbrano/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
FLOW = (ROOT / "zbrano/app/static/js/automations/flow.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


def load_branch_functions(states):
    names = {"_automation_conditions", "_automation_actions", "_automation_branches", "_automation_condition_matches", "_automation_condition_group_matches", "_automation_select_branch"}
    tree = ast.parse(AUTOMATIONS)
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {"Any": Any, "ha_ws": SimpleNamespace(state_cache=states)}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "automations.py", "exec"), namespace)
    return namespace


class BranchingAutomationReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.227"', CONFIG)
        self.assertIn('version="0.13.227"', MAIN)
        self.assertIn("HUD 0.13.227", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.227")

    def test_bounded_branch_schema_is_present(self):
        self.assertIn("class AutomationBranchRequest", SCHEMAS)
        self.assertIn("branches: list[AutomationBranchRequest]", SCHEMAS)
        self.assertIn("max_length=10", SCHEMAS)

    def test_engine_selects_and_preserves_branch_actions(self):
        self.assertIn("def _automation_select_branch", AUTOMATIONS)
        self.assertTrue(any(
            "first-match" in entry.get("summary", "").lower()
            for entry in MANIFEST["history_backfill"]
            if entry.get("version") == "0.13.67"
        ))
        self.assertIn('"actions": selected_actions, "branch": branch_name', AUTOMATIONS)
        self.assertIn('suggestion.get("actions")', MAIN)

    def test_first_matching_branch_and_else_fallback(self):
        functions = load_branch_functions({"sensor.temperature": {"state": "28"}})
        choose = functions["_automation_select_branch"]
        item = {"branches": [
            {"name": "Hot", "condition_mode": "all", "conditions": [{"entity_id": "sensor.temperature", "operator": "above", "value": "26"}], "actions": [{"entity_id": "climate.room", "service": "climate.turn_on"}]},
            {"name": "Else", "condition_mode": "all", "conditions": [], "actions": [{"entity_id": "light.notice", "service": "light.turn_on"}]},
        ]}
        matched, _, actions, branch = choose(item)
        self.assertTrue(matched)
        self.assertEqual(branch, "Hot")
        self.assertEqual(actions[0]["entity_id"], "climate.room")
        functions["ha_ws"].state_cache["sensor.temperature"]["state"] = "20"
        matched, _, actions, branch = choose(item)
        self.assertTrue(matched)
        self.assertEqual(branch, "Else")
        self.assertEqual(actions[0]["entity_id"], "light.notice")

    def test_visual_decision_editor_supports_nested_paths(self):
        self.assertIn("function renderBranchInspector", WORKSPACE)
        self.assertIn("data-branch-add-item", WORKSPACE)
        self.assertIn("This fallback is used only when no path above matches", WORKSPACE)
        self.assertIn("CHOOSE THE FIRST MATCHING OUTCOME", FLOW)

    def test_release_history_includes_v01366(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.226")


if __name__ == "__main__":
    unittest.main()
