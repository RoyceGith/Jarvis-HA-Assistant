import ast
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
AUTOMATIONS = (ROOT / "jarvis/app/domains/automations.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def load_functions(names, states=None):
    tree = ast.parse(AUTOMATIONS)
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {"Any": Any, "ha_ws": SimpleNamespace(state_cache=states or {})}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "automations.py", "exec"), namespace)
    return namespace


class ContextAwareAutomationFeedbackReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.208"', CONFIG)
        self.assertIn('version="0.13.208"', MAIN)
        self.assertIn("HUD 0.13.208", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.208")

    def test_declined_above_threshold_suggestion_respects_trend(self):
        suppress = load_functions({"_automation_dismissal_suppression"})["_automation_dismissal_suppression"]
        trigger = {"kind": "entity", "entity_id": "sensor.room_temperature", "operator": "above", "value": "25"}
        context = {
            "trigger_kind": "entity", "trigger_entity": "sensor.room_temperature",
            "trigger_operator": "above", "trigger_value": "25", "observed_value": "26.7",
        }
        self.assertTrue(suppress({"dismissal_context": dict(context)}, trigger, "26.6")[0])
        self.assertTrue(suppress({"dismissal_context": dict(context)}, trigger, "26.9")[0])
        worsened = {"dismissal_context": dict(context)}
        self.assertFalse(suppress(worsened, trigger, "27.2")[0])
        self.assertIn("dismissal_context", worsened, "context remains until a replacement suggestion actually passes cooldown and policy")

    def test_condition_reset_rearms_the_automation(self):
        functions = load_functions({"_automation_trigger_active", "_automation_trigger_reset", "_automation_clear_dismissal_if_reset"})
        trigger = {"entity_id": "sensor.room_temperature", "operator": "above", "value": "25"}
        item = {"status": "deferred", "dismissal_context": {"trigger_entity": trigger["entity_id"], "trigger_operator": "above"}}
        self.assertTrue(functions["_automation_clear_dismissal_if_reset"](item, trigger, "24.9"))
        self.assertEqual(item["status"], "armed")
        self.assertNotIn("dismissal_context", item)

    def test_proposed_action_is_skipped_when_device_already_satisfies_it(self):
        states = {
            "climate.living_room": {"state": "cool", "attributes": {"temperature": 23}},
            "light.living_room": {"state": "on"},
        }
        satisfied = load_functions({"_automation_action_satisfaction"}, states)["_automation_action_satisfaction"]
        self.assertTrue(satisfied([{"kind": "service", "entity_id": "climate.living_room", "service": "climate.turn_on"}])[0])
        self.assertTrue(satisfied([{"kind": "service", "entity_id": "light.living_room", "service": "light.turn_on"}])[0])
        states["climate.living_room"]["state"] = "off"
        self.assertFalse(satisfied([{"kind": "service", "entity_id": "climate.living_room", "service": "climate.turn_on"}])[0])

    def test_dismissal_route_persists_context_under_engine_lock(self):
        self.assertIn("def _automation_record_suggestion_dismissal", AUTOMATIONS)
        self.assertIn('item["status"] = "deferred"', AUTOMATIONS)
        route = MAIN[MAIN.index("async def dismiss_automation_suggestion"):MAIN.index("@app.post(\"/api/automations/discoveries", MAIN.index("async def dismiss_automation_suggestion"))]
        self.assertIn("async with AUTOMATION_ENGINE_LOCK", route)
        self.assertIn("_automation_record_suggestion_dismissal", route)
        self.assertIn("improving or unchanged conditions will not repeat", route)
        self.assertIn("Why ${esc(item.status)}", WORKSPACE)

    def test_release_history_includes_v01371(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.207")


if __name__ == "__main__":
    unittest.main()
