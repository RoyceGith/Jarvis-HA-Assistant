import json
from pathlib import Path
import ast
from datetime import datetime
import time
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = (ROOT / "zbrano/app/schemas.py").read_text(encoding="utf-8")
AUTOMATIONS = (ROOT / "zbrano/app/domains/automations.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "zbrano/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
FLOW = (ROOT / "zbrano/app/static/js/automations/flow.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class ExplicitAutomationConditionReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.238")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.237")

    def test_condition_schema_and_runtime_support_source_attributes(self):
        self.assertIn('attribute: str = Field(default="", max_length=120', SCHEMAS)
        self.assertIn('"attribute": str(item.get("attribute") or "").strip()', AUTOMATIONS)
        self.assertIn('for part in attribute.split(".")', AUTOMATIONS)

        tree = ast.parse(AUTOMATIONS)
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in {
            "_automation_condition_matches", "_automation_condition_group_matches",
        }]
        namespace = {
            "datetime": datetime,
            "time": time,
            "ha_ws": SimpleNamespace(state_cache={
                "climate.room": {"state": "cool", "attributes": {"hvac_action": "cooling"}},
            }),
        }
        exec(compile(ast.Module(body=functions, type_ignores=[]), "automations.py", "exec"), namespace)
        matched, detail = namespace["_automation_condition_group_matches"]([{
            "kind": "entity", "entity_id": "climate.room", "attribute": "hvac_action",
            "operator": "equals", "value": "cooling", "for_seconds": 0,
        }])
        self.assertTrue(matched)
        self.assertIn("climate.room.hvac_action=cooling", detail)

    def test_condition_editor_exposes_complete_labelled_comparisons(self):
        for label in (
            "Check",
            "Device or sensor",
            "Device or sensor state",
            "Must be",
            "Compared with",
            "Keep true for (seconds)",
            "First device or sensor",
            "Other device or sensor",
            "Use a specific device attribute",
            "First device attribute",
            "Other device attribute",
        ):
            self.assertIn(label, WORKSPACE)
        self.assertIn('data-condition-field="${field}"', WORKSPACE)

    def test_canvas_separates_watchers_from_decision_logic(self):
        self.assertIn("WHEN THIS HAPPENS", FLOW)
        self.assertIn('fallback?"OTHERWISE":bi?"OTHERWISE IF":"IF"', FLOW)
        self.assertIn('sayLabel.textContent="THEN SAY"', FLOW)
        self.assertNotIn('stage("trigger","CHECK THIS"', FLOW)

    def test_empty_shared_condition_stage_is_not_rendered(self):
        self.assertIn('if(checks.length)flow.append', FLOW)
        self.assertNotIn('"No additional condition"', FLOW)


if __name__ == "__main__":
    unittest.main()
