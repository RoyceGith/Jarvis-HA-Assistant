import json
import ast
import asyncio
from pathlib import Path
import unittest
from typing import Any
from unittest.mock import AsyncMock

from zbrano.app.services import entity_policy, ha_control


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "zbrano/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
ENTITY_POLICY = (APP / "services/entity_policy.py").read_text(encoding="utf-8")
HA_CONTROL = (APP / "services/ha_control.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


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
        self.assertIn('version: "0.13.237"', CONFIG)
        self.assertIn('version="0.13.237"', MAIN)
        self.assertIn("HUD 0.13.237", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.237")

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

    def test_successful_websocket_control_is_never_replayed_over_rest(self):
        class FakeClient:
            state_cache = {}

            def __init__(self):
                self.call_service = AsyncMock(return_value={"success": True})

        client = FakeClient()
        original_client = ha_control._ha_client
        original_token = ha_control.SUPERVISOR_TOKEN
        original_control = ha_control._ensure_control_allowed
        original_wait = ha_control._wait_for_ha_power_state
        original_rest_state = ha_control.ha_get_state_rest
        try:
            ha_control._ha_client = client
            ha_control.SUPERVISOR_TOKEN = "test-token"
            ha_control._ensure_control_allowed = lambda entity_id: "climate"
            ha_control._wait_for_ha_power_state = AsyncMock(return_value=None)
            ha_control.ha_get_state_rest = AsyncMock(return_value={
                "entity_id": "climate.living_room_air_conditioner",
                "state": "cool",
                "attributes": {"friendly_name": "Living room Air Conditioner"},
            })

            result = asyncio.run(ha_control.ha_set_power(
                "climate.living_room_air_conditioner", True
            ))
        finally:
            ha_control._ha_client = original_client
            ha_control.SUPERVISOR_TOKEN = original_token
            ha_control._ensure_control_allowed = original_control
            ha_control._wait_for_ha_power_state = original_wait
            ha_control.ha_get_state_rest = original_rest_state

        client.call_service.assert_awaited_once()
        self.assertEqual(result["transport"], "websocket")
        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()
