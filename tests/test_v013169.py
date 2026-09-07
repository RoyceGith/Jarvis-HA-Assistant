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


def load_readiness(access, blocked_entities=None):
    tree = ast.parse(AUTOMATIONS)
    names = {"_automation_triggers", "_automation_conditions", "_automation_actions", "_automation_branches", "_automation_readiness"}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    blocked = set(blocked_entities or [])
    namespace = {
        "Any": Any,
        "effective_entity_access": lambda entity_id: access.get(entity_id),
        "_automation_label_blocks_control": lambda data, entity_id: entity_id in blocked,
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "automations.py", "exec"), namespace)
    return namespace["_automation_readiness"]


class AutomationPermissionAuditReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.186"', CONFIG)
        self.assertIn('version="0.13.186"', MAIN)
        self.assertIn("HUD 0.13.186", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.186")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.185")

    def test_runtime_readiness_reports_reads_and_controls(self):
        readiness = load_readiness({
            "sensor.temp": "read_only",
            "person.owner": "read_only",
            "climate.room": "low_risk_control_proposed",
        })
        result = readiness({
            "triggers": [{"entity_id": "sensor.temp"}],
            "signal_entities": ["sensor.temp"],
            "presence_entity": "person.owner",
            "actions": [{"kind": "service", "entity_id": "climate.room", "service": "climate.turn_on"}],
        }, {})
        self.assertTrue(result["ready"])
        requirements = {(item["permission"], item["entity_id"]): item for item in result["requirements"]}
        self.assertEqual(set(requirements), {
            ("read", "sensor.temp"), ("read", "person.owner"), ("control", "climate.room"),
        })
        self.assertEqual(requirements[("read", "sensor.temp")]["sources"], ["trigger_read", "signal_read"])
        self.assertTrue(requirements[("control", "climate.room")]["allowed"])

    def test_missing_and_safety_blocked_permissions_are_explained(self):
        readiness = load_readiness(
            {"light.room": "low_risk_control_proposed", "switch.fan": "read_only"},
            blocked_entities={"light.room"},
        )
        result = readiness({
            "triggers": [{"entity_id": "sensor.missing"}],
            "actions": [
                {"kind": "service", "entity_id": "light.room", "service": "light.turn_on"},
                {"kind": "service", "entity_id": "switch.fan", "service": "switch.turn_on"},
            ],
        }, {})
        self.assertFalse(result["ready"])
        requirements = {(item["permission"], item["entity_id"]): item for item in result["requirements"]}
        self.assertFalse(requirements[("read", "sensor.missing")]["allowed"])
        self.assertTrue(requirements[("control", "light.room")]["safety_label_blocked"])
        self.assertEqual(requirements[("control", "switch.fan")]["access"], "read_only")

    def test_permission_view_is_filterable_and_actionable(self):
        for marker in (
            'data-auto-view="permissions"', 'data-auto-panel="permissions"',
            'id="automation-permission-ready"', 'id="automation-permission-attention"',
            'id="automation-permission-reads"', 'id="automation-permission-controls"',
            'id="automation-permission-filter"', "data-permission-open-entities",
            "function renderPermissions()",
        ):
            self.assertIn(marker, HTML + WORKSPACE)
        self.assertIn(".automation-permission-list", CSS)
        self.assertIn('#automation-permission-ready', BROWSER)
        self.assertIn('/Control allowed/i', BROWSER)


if __name__ == "__main__":
    unittest.main()
