import ast
import json
from pathlib import Path
from typing import Any
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
AUTOMATIONS = (ROOT / "jarvis/app/domains/automations.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def load_readiness(access, label_blocked=False):
    tree = ast.parse(AUTOMATIONS)
    names = {"_automation_triggers", "_automation_conditions", "_automation_actions", "_automation_branches", "_automation_readiness"}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {
        "Any": Any,
        "effective_entity_access": lambda entity_id: access.get(entity_id),
        "_automation_label_blocks_control": lambda data, entity_id: label_blocked,
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "automations.py", "exec"), namespace)
    return namespace["_automation_readiness"]


class AutomationReadinessReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.86"', CONFIG)
        self.assertIn('version="0.13.86"', MAIN)
        self.assertIn("HUD 0.13.86", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.86")

    def test_live_read_and_control_permissions_are_ready(self):
        ready = load_readiness({"sensor.temp": "read_only", "climate.room": "low_risk_control_proposed"})
        result = ready({
            "triggers": [{"entity_id": "sensor.temp"}],
            "actions": [{"kind": "service", "entity_id": "climate.room", "service": "climate.turn_on"}],
        }, {})
        self.assertTrue(result["ready"])
        self.assertEqual(result["issues"], [])

    def test_read_only_action_and_missing_trigger_are_blocked(self):
        ready = load_readiness({"climate.room": "read_only"})
        result = ready({
            "triggers": [{"entity_id": "sensor.temp"}],
            "actions": [{"kind": "service", "entity_id": "climate.room", "service": "climate.turn_on"}],
        }, {})
        self.assertFalse(result["ready"])
        self.assertEqual({item["kind"] for item in result["issues"]}, {"trigger_read", "action_control"})

    def test_home_assistant_safety_label_blocks_control(self):
        ready = load_readiness({"light.room": "low_risk_control_proposed"}, label_blocked=True)
        result = ready({
            "actions": [{"kind": "service", "entity_id": "light.room", "service": "light.turn_on"}],
        }, {})
        self.assertFalse(result["ready"])
        self.assertEqual(result["issues"][0]["kind"], "safety_label")

    def test_execution_and_approval_recheck_current_readiness(self):
        commit = AUTOMATIONS[AUTOMATIONS.index("async def _automation_commit_match"):AUTOMATIONS.index("async def _automation_delayed_match")]
        self.assertIn('policy in {"approval_required", "autonomous"}', commit)
        self.assertIn('item["status"] = "blocked_permission"', commit)
        approval = MAIN[MAIN.index("async def approve_automation_suggestion"):MAIN.index('@app.post("/api/automations/suggestions/{suggestion_id}/dismiss', MAIN.index("async def approve_automation_suggestion"))]
        self.assertIn("_automation_readiness", approval)
        self.assertIn("status_code=403", approval)

    def test_studio_exposes_live_readiness(self):
        self.assertIn("Live readiness:", WORKSPACE)
        self.assertIn("blocked_permission", WORKSPACE)
        self.assertIn('item["readiness"] = _automation_readiness', MAIN)

    def test_release_history_includes_v01376(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.85")


if __name__ == "__main__":
    unittest.main()
