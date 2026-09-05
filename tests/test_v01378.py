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
AUTOMATIONS = (ROOT / "jarvis/app/domains/automations.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def load_recorder():
    tree = ast.parse(AUTOMATIONS)
    node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_automation_record_decision")
    namespace = {"Any": Any, "time": time}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "automations.py", "exec"), namespace)
    return namespace["_automation_record_decision"]


class AutomationDecisionJournalReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.152"', CONFIG)
        self.assertIn('version="0.13.152"', MAIN)
        self.assertIn("HUD 0.13.152", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.152")

    def test_decision_journal_is_bounded_and_keeps_latest(self):
        record = load_recorder()
        item = {}
        for index in range(35):
            record(item, f"outcome_{index}", f"detail {index}", evidence="sensor.test", policy="suggest", branch="Comfort")
        self.assertEqual(len(item["decision_history"]), 30)
        self.assertEqual(item["decision_history"][0]["outcome"], "outcome_34")
        self.assertEqual(item["decision_history"][-1]["outcome"], "outcome_5")
        self.assertEqual(item["last_decision"], item["decision_history"][0])

    def test_engine_records_all_material_decision_classes(self):
        commit = AUTOMATIONS[AUTOMATIONS.index("async def _automation_commit_match"):AUTOMATIONS.index("async def _automation_delayed_match")]
        for outcome in (
            "suppressed_presence", "suppressed_context", "suppressed_branch",
            "already_satisfied", "deferred_not_now", "blocked_permission",
            "paused_failure", "deferred_learning", "rate_limited", "observed",
        ):
            self.assertIn(f'"{outcome}"', commit)
        execute = AUTOMATIONS[AUTOMATIONS.index("async def _automation_execute_action"):AUTOMATIONS.index("async def _automation_commit_match")]
        self.assertIn('item, "executed"', execute)
        self.assertIn('item, item["status"]', execute)

    def test_studio_shows_bounded_per_automation_journal(self):
        self.assertIn("Decision journal", WORKSPACE)
        self.assertIn("item.decision_history", WORKSPACE)
        self.assertIn(".slice(0,5)", WORKSPACE)

    def test_release_history_includes_v01377(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.151")


if __name__ == "__main__":
    unittest.main()
