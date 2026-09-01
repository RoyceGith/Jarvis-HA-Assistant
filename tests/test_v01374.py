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


def load_functions(names):
    tree = ast.parse(AUTOMATIONS)
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {"Any": Any}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "automations.py", "exec"), namespace)
    return namespace


class LearnedAutomationPreferenceReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.111"', CONFIG)
        self.assertIn('version="0.13.111"', MAIN)
        self.assertIn("HUD 0.13.111", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.111")

    def test_repeated_not_now_gradually_raises_suggestion_boundary(self):
        learned = load_functions({"_automation_learned_suppression"})["_automation_learned_suppression"]
        trigger = {"entity_id": "sensor.room_temperature", "operator": "above", "value": "25"}
        once = {"feedback_memory": {"consecutive_dismissals": 1}}
        self.assertTrue(learned(once, trigger, "25.3")[0])
        self.assertFalse(learned(once, trigger, "25.5")[0])
        repeated = {"feedback_memory": {"consecutive_dismissals": 3}}
        self.assertTrue(learned(repeated, trigger, "26.2")[0])
        self.assertFalse(learned(repeated, trigger, "26.5")[0])

    def test_feedback_outcomes_are_bounded_and_positive_feedback_resets_restraint(self):
        record = load_functions({"_automation_record_feedback"})["_automation_record_feedback"]
        item = {}
        for index in range(25):
            record(item, "not_now", index, {"observed_value": str(26 + index / 10)})
        feedback = item["feedback_memory"]
        self.assertEqual(feedback["dismissals"], 25)
        self.assertEqual(feedback["consecutive_dismissals"], 25)
        self.assertEqual(len(feedback["history"]), 20)
        record(item, "approved", 30, {"action_entity": "climate.room"})
        self.assertEqual(feedback["approvals"], 1)
        self.assertEqual(feedback["consecutive_dismissals"], 0)
        self.assertEqual(feedback["history"][0]["outcome"], "approved")

    def test_learning_applies_only_to_suggestion_policies(self):
        commit = AUTOMATIONS[AUTOMATIONS.index("async def _automation_commit_match"):AUTOMATIONS.index("async def _automation_delayed_match")]
        self.assertIn('policy in {"suggest", "approval_required"}', commit)
        self.assertNotIn('policy in {"autonomous", "observe"}', commit)

    def test_studio_explains_and_can_reset_rule_learning(self):
        self.assertIn("Learned feedback:", WORKSPACE)
        self.assertIn("data-auto-reset-learning", WORKSPACE)
        self.assertIn("async def reset_automation_feedback", MAIN)
        route = MAIN[MAIN.index("async def reset_automation_feedback"):MAIN.index("@app.post(\"/api/automations/suggestions", MAIN.index("async def reset_automation_feedback"))]
        self.assertIn('automation.pop("feedback_memory", None)', route)
        self.assertNotIn('automation.pop("episode_history", None)', route)

    def test_release_history_includes_v01373(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.110")


if __name__ == "__main__":
    unittest.main()
