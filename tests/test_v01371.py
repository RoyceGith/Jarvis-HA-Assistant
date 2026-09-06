import ast
from datetime import datetime, timedelta
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
SCHEMAS = (ROOT / "jarvis/app/schemas.py").read_text(encoding="utf-8")
AUTOMATIONS = (ROOT / "jarvis/app/domains/automations.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
FLOW = (ROOT / "jarvis/app/static/js/automations/flow.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def load_functions(names, states=None):
    tree = ast.parse(AUTOMATIONS)
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {
        "Any": Any,
        "datetime": datetime,
        "time": time,
        "ha_ws": SimpleNamespace(state_cache=states or {}),
    }
    exec(compile(ast.Module(body=selected, type_ignores=[]), "automations.py", "exec"), namespace)
    return namespace


class TimeScheduleAutomationReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.166"', CONFIG)
        self.assertIn('version="0.13.166"', MAIN)
        self.assertIn("HUD 0.13.166", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.166")

    def test_schedule_triggers_fire_once_per_slot(self):
        schedule_due = load_functions({"_automation_schedule_due"})["_automation_schedule_due"]
        local = datetime.now().astimezone().replace(second=0, microsecond=0)
        now = local.timestamp()
        item = {"created_at": now - 600, "schedule_markers": {}}
        trigger = {"kind": "time", "at": local.strftime("%H:%M"), "weekdays": [local.weekday()]}
        due, marker, _ = schedule_due(trigger, item, 0, now)
        self.assertTrue(due)
        item["schedule_markers"]["0:time"] = marker
        self.assertFalse(schedule_due(trigger, item, 0, now)[0])
        self.assertTrue(schedule_due({"kind": "interval", "interval_minutes": 5}, item, 1, now)[0])
        one_time = (local - timedelta(minutes=1)).replace(tzinfo=None).isoformat(timespec="minutes")
        self.assertTrue(schedule_due({"kind": "one_time", "one_time_at": one_time}, item, 2, now)[0])

    def test_time_sun_and_duration_conditions_use_live_context(self):
        now = time.time()
        functions = load_functions(
            {"_automation_condition_matches", "_automation_condition_group_matches"},
            {
                "sun.sun": {"state": "below_horizon"},
                "binary_sensor.door": {
                    "state": "off",
                    "last_changed": datetime.fromtimestamp(now - 120).astimezone().isoformat(),
                },
            },
        )
        match = functions["_automation_condition_group_matches"]
        weekday = time.localtime().tm_wday
        conditions = [
            {"kind": "weekday", "weekdays": [weekday]},
            {"kind": "time_window", "start_time": "00:00", "end_time": "23:59"},
            {"kind": "sun", "sun_state": "below_horizon"},
            {"kind": "entity", "entity_id": "binary_sensor.door", "operator": "equals", "value": "off", "for_seconds": 60},
        ]
        self.assertTrue(match(conditions, "all")[0])

    def test_graphical_builder_and_worker_cover_all_schedule_types(self):
        for kind in ("time", "sun", "interval", "one_time"):
            self.assertIn(f'<option value="{kind}"', HTML)
            self.assertIn(f'kind==="{kind}"', FLOW)
        for kind in ("time_window", "weekday", "sun"):
            self.assertIn(f'value="{kind}"', WORKSPACE)
        self.assertIn("async def automation_schedule_worker", AUTOMATIONS)
        self.assertIn("await asyncio.sleep(15)", AUTOMATIONS)
        self.assertIn("schedule_markers", AUTOMATIONS)
        self.assertIn("AUTOMATION_SCHEDULE_TASK", MAIN)
        self.assertIn("AutomationConditionRequest", SCHEMAS)

    def test_release_history_includes_v01370(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.165")


if __name__ == "__main__":
    unittest.main()
