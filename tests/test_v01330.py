import json
import ast
from pathlib import Path
import unittest
from typing import Any

from jarvis.app.services import entity_policy


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
ENTITY_POLICY = (APP / "services/entity_policy.py").read_text(encoding="utf-8")
HA_CONTROL = (APP / "services/ha_control.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def load_ha_control_helpers():
    tree = ast.parse(HA_CONTROL)
    selected = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"normalize_ha_state", "_ha_power_state_matches"}
    ]
    namespace = {"Any": Any}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "<ha_control>", "exec"), namespace)
    return namespace


class HomeAssistantServiceBoundaryTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.39"', CONFIG)
        self.assertIn('version="0.13.39"', MAIN)
        self.assertIn("HUD 0.13.39", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.39")

    def test_both_services_are_outside_composition_root_and_configured(self):
        self.assertNotIn("def load_entity_policy(", MAIN)
        self.assertNotIn("async def ha_set_power(", MAIN)
        self.assertIn("def load_entity_policy(", ENTITY_POLICY)
        self.assertIn("async def ha_set_power(", HA_CONTROL)
        self.assertIn("configure_entity_policy_service(", MAIN)
        self.assertIn("configure_ha_control_service(", MAIN)

    def test_entity_access_and_control_ceiling_are_preserved(self):
        original_loader = entity_policy.load_entity_policy
        try:
            entity_policy.load_entity_policy = lambda: {
                "sensor.room_temp": {"enabled": True, "access": "read_only"},
                "light.room": {"enabled": True, "access": "low_risk_control_proposed"},
                "lock.front": {"enabled": True, "access": "low_risk_control_proposed"},
            }
            entity_policy.ensure_read_allowed("sensor.room_temp")
            self.assertEqual(entity_policy.ensure_control_allowed("light.room"), "light")
            with self.assertRaises(PermissionError):
                entity_policy.ensure_control_allowed("lock.front")
        finally:
            entity_policy.load_entity_policy = original_loader

    def test_alias_aware_search_and_state_helpers_are_preserved(self):
        original_loader = entity_policy.load_entity_policy
        try:
            entity_policy.load_entity_policy = lambda: {
                "light.lounge": {
                    "enabled": True,
                    "access": "low_risk_control_proposed",
                    "friendly_name": "Living Room Light",
                    "aliases": ["sofa lamp"],
                }
            }
            result = entity_policy.find_approved_entities("sofa lamp")
            self.assertEqual(result["recommended_unique_match"]["entity_id"], "light.lounge")
        finally:
            entity_policy.load_entity_policy = original_loader

        helpers = load_ha_control_helpers()
        normalized = helpers["normalize_ha_state"]({
            "entity_id": "light.lounge",
            "state": "on",
            "attributes": {"friendly_name": "Living Room Light"},
        })
        self.assertEqual(normalized["friendly_name"], "Living Room Light")
        matches = helpers["_ha_power_state_matches"]
        self.assertTrue(matches("light", "on", True))
        self.assertTrue(matches("climate", "cool", True))
        self.assertFalse(matches("climate", "off", True))


if __name__ == "__main__":
    unittest.main()
