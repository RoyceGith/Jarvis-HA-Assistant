import ast
import json
from pathlib import Path
import time
from typing import Any
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
SCHEMAS = (ROOT / "jarvis/app/schemas.py").read_text(encoding="utf-8")
AUTOMATIONS = (ROOT / "jarvis/app/domains/automations.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def load_functions(names):
    tree = ast.parse(AUTOMATIONS)
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {"Any": Any, "time": time}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "automations.py", "exec"), namespace)
    return namespace


class AutomationLifecycleRecoveryReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.87"', CONFIG)
        self.assertIn('version="0.13.87"', MAIN)
        self.assertIn("HUD 0.13.87", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.87")

    def test_unanswered_suggestion_expires_and_unblocks_rule(self):
        functions = load_functions({"_automation_event", "_automation_record_feedback", "_automation_expire_stale_suggestions"})
        expire = functions["_automation_expire_stale_suggestions"]
        item = {"id": "rule-1", "name": "Comfort", "enabled": True, "status": "approval_required", "suggestion_timeout_minutes": 10}
        suggestion = {"id": "s1", "automation_id": "rule-1", "status": "approval_required", "created_at": 100}
        data = {"suggestions": [suggestion], "timeline": []}
        self.assertEqual(expire(data, item, 699), 0)
        self.assertEqual(expire(data, item, 700), 1)
        self.assertEqual(suggestion["status"], "expired")
        self.assertEqual(item["status"], "armed")
        self.assertEqual(item["feedback_memory"]["expired_suggestions"], 1)

    def test_orphaned_execution_is_marked_failed_for_recovery(self):
        functions = load_functions({"_automation_event", "_automation_record_feedback", "_automation_expire_stale_suggestions"})
        expire = functions["_automation_expire_stale_suggestions"]
        item = {"id": "rule-1", "name": "Comfort", "enabled": True, "status": "executing", "suggestion_timeout_minutes": 1}
        suggestion = {"automation_id": "rule-1", "status": "executing", "created_at": 1}
        data = {"suggestions": [suggestion], "timeline": []}
        self.assertEqual(expire(data, item, 61), 1)
        self.assertEqual(suggestion["status"], "interrupted")
        self.assertEqual(item["status"], "failed")
        self.assertEqual(item["feedback_memory"]["action_failures"], 1)

    def test_success_and_failure_outcomes_are_recorded(self):
        execute = AUTOMATIONS[AUTOMATIONS.index("async def _automation_execute_action"):AUTOMATIONS.index("async def _automation_commit_match")]
        self.assertIn('"action_failure"', execute)
        self.assertIn('"autonomous_success"', execute)
        self.assertIn('source == "selective_autonomy"', execute)

    def test_response_window_and_health_are_exposed_in_studio(self):
        self.assertIn("suggestion_timeout_minutes", SCHEMAS)
        self.assertIn("automation-suggestion-timeout", HTML)
        self.assertIn("automation-suggestion-timeout", WORKSPACE)
        self.assertIn("Outcome health:", WORKSPACE)
        self.assertIn('["dismissed","expired"]', WORKSPACE)

    def test_read_route_runs_recovery_under_engine_lock(self):
        route = MAIN[MAIN.index("async def read_autonomous_automations"):MAIN.index("@app.put(\"/api/automations/settings", MAIN.index("async def read_autonomous_automations"))]
        self.assertIn("async with AUTOMATION_ENGINE_LOCK", route)
        self.assertIn("_automation_expire_stale_suggestions", route)
        self.assertIn("_automation_save(data)", route)

    def test_release_history_includes_v01374(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.86")


if __name__ == "__main__":
    unittest.main()
