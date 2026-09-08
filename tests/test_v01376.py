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
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def load_function(name):
    tree = ast.parse(AUTOMATIONS)
    node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
    namespace = {"Any": Any}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "automations.py", "exec"), namespace)
    return namespace[name]


class AutomationFailureCircuitReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.194"', CONFIG)
        self.assertIn('version="0.13.194"', MAIN)
        self.assertIn("HUD 0.13.194", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.194")

    def test_failure_circuit_opens_within_configured_window(self):
        circuit = load_function("_automation_failure_circuit")
        item = {"failure_limit": 3, "failure_window_minutes": 60, "feedback_memory": {"failure_timestamps": [900, 800, 700], "history": [
            {"outcome": "action_failure", "created_at": 900},
            {"outcome": "action_failure", "created_at": 800},
            {"outcome": "action_failure", "created_at": 700},
            {"outcome": "approved", "created_at": 950},
        ]}}
        opened, detail, count = circuit(item, 1000)
        self.assertTrue(opened)
        self.assertEqual(count, 3)
        self.assertIn("3/3", detail)
        self.assertTrue(item["recovery_state"]["circuit_open"])

    def test_explicit_recovery_acknowledgment_closes_without_erasing_history(self):
        circuit = load_function("_automation_failure_circuit")
        history = [{"outcome": "action_failure", "created_at": value} for value in (700, 800, 900)]
        item = {"failure_limit": 3, "failure_window_minutes": 60, "feedback_memory": {"failure_timestamps": [900, 800, 700], "history": history, "failure_acknowledged_at": 950}}
        opened, _, count = circuit(item, 1000)
        self.assertFalse(opened)
        self.assertEqual(count, 0)
        self.assertEqual(item["feedback_memory"]["history"], history)

    def test_circuit_guards_approval_and_automatic_execution_only(self):
        commit = AUTOMATIONS[AUTOMATIONS.index("async def _automation_commit_match"):AUTOMATIONS.index("async def _automation_delayed_match")]
        self.assertIn('circuit_open and policy in {"approval_required", "autonomous"}', commit)
        approval = MAIN[MAIN.index("async def approve_automation_suggestion"):MAIN.index("@app.post(\"/api/automations/suggestions/{suggestion_id}/dismiss", MAIN.index("async def approve_automation_suggestion"))]
        self.assertIn("_automation_failure_circuit", approval)
        self.assertIn("status_code=409", approval)

    def test_studio_exposes_failure_policy_and_recovery(self):
        for marker in ("failure_limit", "failure_window_minutes"):
            self.assertIn(marker, SCHEMAS)
        for marker in ("automation-failure-limit", "automation-failure-window"):
            self.assertIn(marker, HTML)
            self.assertIn(marker, WORKSPACE)
        self.assertIn("Failure circuit:", WORKSPACE)
        self.assertIn("data-auto-recover", WORKSPACE)

    def test_recovery_route_preserves_audit_history(self):
        route = MAIN[MAIN.index("async def recover_automation_failures"):MAIN.index("@app.post(\"/api/automations/suggestions", MAIN.index("async def recover_automation_failures"))]
        self.assertIn('feedback["failure_acknowledged_at"]', route)
        self.assertIn('feedback["recovery_resets"]', route)
        self.assertNotIn('feedback.pop("history"', route)

    def test_release_history_includes_v01375(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.193")


if __name__ == "__main__":
    unittest.main()
