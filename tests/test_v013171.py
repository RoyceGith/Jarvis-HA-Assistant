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
CSS = (ROOT / "jarvis/app/static/css/automation-studio.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def load_evaluation():
    tree = ast.parse(AUTOMATIONS)
    node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_automation_evaluation")
    namespace = {"Any": Any}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "automations.py", "exec"), namespace)
    return namespace["_automation_evaluation"]


class AutomationEvaluationReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.213"', CONFIG)
        self.assertIn('version="0.13.213"', MAIN)
        self.assertIn("HUD 0.13.213", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.213")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.212")

    def test_evaluation_states_have_explicit_evidence_boundaries(self):
        evaluate = load_evaluation()
        cases = (
            ({}, "learning"),
            ({"feedback_memory": {"dismissals": 4, "approvals": 1}}, "tune"),
            ({"feedback_memory": {"expired_suggestions": 4, "approvals": 1}}, "delivery"),
            ({"feedback_memory": {"action_failures": 3, "autonomous_successes": 1}}, "reliability"),
            ({"feedback_memory": {"approvals": 3, "dismissals": 1}}, "healthy"),
            ({"readiness": {"ready": False}, "feedback_memory": {"approvals": 5}}, "attention"),
            ({"recovery_state": {"circuit_open": True}, "feedback_memory": {"approvals": 5}}, "attention"),
        )
        for item, expected in cases:
            with self.subTest(expected=expected, item=item):
                self.assertEqual(evaluate(item)["state"], expected)

    def test_rates_and_monitor_only_evidence_are_transparent(self):
        evaluate = load_evaluation()
        result = evaluate({
            "feedback_memory": {"approvals": 2, "manual_resolutions": 1, "dismissals": 1, "expired_suggestions": 1},
            "decision_history": [{"outcome": "observed"} for _ in range(8)],
        })
        self.assertEqual(result["accepted"], 3)
        self.assertEqual(result["acceptance_rate"], 0.75)
        self.assertEqual(result["response_rate"], 0.8)
        self.assertEqual(result["recent_matches"], 8)
        self.assertEqual(result["evidence_count"], 8)

    def test_api_and_activity_expose_filterable_results(self):
        self.assertIn('item["evaluation"] = _automation_evaluation(item)', MAIN)
        for marker in (
            'id="automation-results-filter"', 'id="automation-results-evaluated"',
            'id="automation-results-attention"', 'id="automation-results-learning"',
            'id="automation-results-healthy"', 'id="automation-results-list"',
            "function renderEvaluation()", "evaluationAttentionStates",
            "accepted when answered", "response rate",
        ):
            self.assertIn(marker, WORKSPACE)
        self.assertIn(".automation-results-list", CSS)
        self.assertIn("#automation-results-evaluated", BROWSER)
        self.assertIn("/Narrow its When or IF checks/i", BROWSER)


if __name__ == "__main__":
    unittest.main()
