import ast
import json
import time
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTOMATIONS = ROOT / "jarvis" / "app" / "domains" / "automations.py"
SCHEMAS = (ROOT / "jarvis" / "app" / "schemas.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis" / "app" / "static" / "js" / "automations" / "workspace.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis" / "release_manifest.json").read_text(encoding="utf-8"))


def load_sleep_hours_helper():
    module = ast.parse(AUTOMATIONS.read_text(encoding="utf-8"))
    function = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "_automation_sleep_hours_active")
    namespace = {"Any": object, "time": time}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), str(AUTOMATIONS), "exec"), namespace)
    return namespace["_automation_sleep_hours_active"]


class Release013162Tests(unittest.TestCase):
    def test_release_markers_and_sleep_controls(self):
        self.assertEqual(MANIFEST["version"], "0.13.181")
        self.assertIn("sleep_hours_enabled", SCHEMAS)
        self.assertIn('"automation-sleep-hours-enabled"', WORKSPACE)
        self.assertIn('"automation-run-during-sleep-hours"', WORKSPACE)

    def test_sleep_hours_are_per_automation_and_support_security_override(self):
        active = load_sleep_hours_helper()
        timestamp = time.mktime(datetime(2026, 9, 6, 23, 30).timetuple())
        daytime = time.mktime(datetime(2026, 9, 6, 12, 0).timetuple())
        rule = {"sleep_hours_enabled": True, "sleep_hours_start": "22:00", "sleep_hours_end": "07:00"}
        self.assertTrue(active(rule, timestamp)[0])
        self.assertFalse(active(rule, daytime)[0])
        self.assertFalse(active({**rule, "run_during_sleep_hours": True}, timestamp)[0])
        self.assertFalse(active({**rule, "sleep_hours_enabled": False}, timestamp)[0])

    def test_branch_validation_is_card_specific(self):
        self.assertIn("branchCardNeedsAttention", WORKSPACE)
        self.assertIn('collection==="actions"&&field==="entity_id"', WORKSPACE)
        self.assertIn('item.service=domain?`${domain}.${item.task_template}`', WORKSPACE)


if __name__ == "__main__":
    unittest.main()
