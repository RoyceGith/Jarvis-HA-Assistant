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
FLOW = (ROOT / "jarvis/app/static/js/automations/flow.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def load_functions(names):
    tree = ast.parse(AUTOMATIONS)
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {"Any": Any}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "automations.py", "exec"), namespace)
    return namespace


class EpisodeAwareAutomationReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.134"', CONFIG)
        self.assertIn('version="0.13.134"', MAIN)
        self.assertIn("HUD 0.13.134", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.134")

    def test_numeric_episode_tracks_direction_and_extremes(self):
        functions = load_functions({"_automation_trigger_active", "_automation_trigger_reset", "_automation_numeric_episode_update"})
        update = functions["_automation_numeric_episode_update"]
        trigger = {"entity_id": "sensor.room_temperature", "operator": "above", "value": "25"}
        item = {}
        self.assertTrue(update(item, trigger, "26.0", 1))
        self.assertTrue(update(item, trigger, "26.3", 2))
        self.assertEqual(item["active_episode"]["trend"], "worsening")
        self.assertTrue(update(item, trigger, "26.1", 3))
        self.assertEqual(item["active_episode"]["trend"], "improving")
        self.assertEqual(item["active_episode"]["worst_value"], 26.3)
        self.assertEqual(item["active_episode"]["sample_count"], 3)

    def test_reset_margin_keeps_deadband_then_closes_episode(self):
        functions = load_functions({"_automation_trigger_active", "_automation_trigger_reset", "_automation_numeric_episode_update"})
        update = functions["_automation_numeric_episode_update"]
        trigger = {"entity_id": "sensor.room_temperature", "operator": "above", "value": "25"}
        item = {"reset_delta": 0.5}
        update(item, trigger, "26", 1)
        self.assertFalse(update(item, trigger, "24.8", 2))
        self.assertIn("active_episode", item)
        self.assertTrue(update(item, trigger, "24.5", 3))
        self.assertNotIn("active_episode", item)
        self.assertEqual(item["episode_history"][0]["reset_value"], 24.5)

    def test_custom_worsening_margin_controls_reoffer(self):
        functions = load_functions({"_automation_dismissal_suppression"})
        suppress = functions["_automation_dismissal_suppression"]
        trigger = {"entity_id": "sensor.room_temperature", "operator": "above", "value": "25"}
        item = {"reoffer_delta": 1.0, "dismissal_context": {"trigger_kind": "entity", "trigger_entity": trigger["entity_id"], "trigger_operator": "above", "observed_value": "26.7"}}
        self.assertTrue(suppress(item, trigger, "27.2")[0])
        self.assertFalse(suppress(item, trigger, "27.7")[0])

    def test_feedback_memory_and_studio_controls_are_wired(self):
        self.assertIn('"not_now": "dismissals"', AUTOMATIONS)
        self.assertIn('_automation_record_feedback(item, "manual_resolution"', AUTOMATIONS)
        self.assertIn('_automation_record_feedback(item, "approved"', AUTOMATIONS)
        for marker in ("automation-reoffer-delta", "automation-reset-delta"):
            self.assertIn(marker, HTML)
            self.assertIn(marker, WORKSPACE)
        self.assertIn("Active episode:", WORKSPACE)
        self.assertIn("automation-reoffer-delta", WORKSPACE)

    def test_release_history_includes_v01372(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.133")


if __name__ == "__main__":
    unittest.main()
