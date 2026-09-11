import ast
import asyncio
from pathlib import Path
import re
import unittest
from typing import Any
from unittest.mock import AsyncMock


MAIN_PATH = Path(__file__).resolve().parents[1] / "zbrano/app/main.py"
SETTINGS_PATH = Path(__file__).resolve().parents[1] / "zbrano/app/domains/settings.py"


def load_preference_functions():
    main_tree = ast.parse(MAIN_PATH.read_text(encoding="utf-8"))
    settings_tree = ast.parse(SETTINGS_PATH.read_text(encoding="utf-8"))
    selected = [node for node in main_tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "try_local_ha_route"]
    selected.extend(node for node in settings_tree.body if isinstance(node, ast.FunctionDef) and node.name == "apply_pronunciation_dictionary")
    for node in selected:
        node.decorator_list = []
    namespace = {"re": re, "Any": Any}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(MAIN_PATH), "exec"), namespace)
    return namespace


class PreferenceBehaviorTests(unittest.TestCase):
    def test_cautious_mode_requires_confirmation_before_control(self):
        functions = load_preference_functions()
        entity = {"entity_id": "light.bench", "friendly_name": "Bench light"}
        set_power = AsyncMock(return_value={"verified_state": "on", "friendly_name": "Bench light"})
        functions.update(
            {
                "PENDING_LOW_RISK_ACTIONS": {},
                "get_session_entity": lambda session_id: None,
                "is_entity_followup": lambda message: False,
                "parse_local_ha_intent": lambda message: {"kind": "control", "query": "bench", "turn_on": True},
                "find_approved_entities": lambda query: {"recommended_unique_match": entity},
                "load_preferences": lambda: {"confirmation_strictness": "cautious"},
                "ha_set_power": set_power,
                "remember_session_entity": lambda *args: None,
            }
        )

        proposal = asyncio.run(functions["try_local_ha_route"]("turn on bench", "test"))
        self.assertIn("Confirm:", proposal["reply"])
        set_power.assert_not_awaited()

        confirmed = asyncio.run(functions["try_local_ha_route"]("confirm", "test"))
        self.assertIn("now on", confirmed["reply"])
        set_power.assert_awaited_once_with("light.bench", True)

    def test_control_intent_prefers_the_control_device_over_matching_sensors(self):
        functions = load_preference_functions()
        thermostat = {
            "entity_id": "climate.living_room_air_conditioner",
            "friendly_name": "Living room Air Conditioner",
            "control_approved": True,
            "score": 80,
        }
        set_power = AsyncMock(return_value={
            "verified_state": "cool",
            "friendly_name": thermostat["friendly_name"],
        })
        functions.update(
            {
                "PENDING_LOW_RISK_ACTIONS": {},
                "get_session_entity": lambda session_id: None,
                "is_entity_followup": lambda message: False,
                "parse_local_ha_intent": lambda message: {
                    "kind": "control", "query": "living room air conditioner", "turn_on": True,
                },
                "find_approved_entities": lambda query: {
                    "recommended_unique_match": None,
                    "matches": [
                        {
                            "entity_id": "sensor.living_room_air_conditioner_temperature",
                            "friendly_name": "Living room Air Conditioner Temperature",
                            "control_approved": False,
                            "score": 100,
                        },
                        {
                            "entity_id": "binary_sensor.living_room_air_conditioner_status",
                            "friendly_name": "Living room Air Conditioner Status",
                            "control_approved": False,
                            "score": 100,
                        },
                        thermostat,
                    ],
                },
                "load_preferences": lambda: {"confirmation_strictness": "standard"},
                "ha_set_power": set_power,
                "remember_session_entity": lambda *args: None,
            }
        )

        result = asyncio.run(functions["try_local_ha_route"](
            "turn on the living room air conditioner", "test"
        ))

        self.assertIn("now cool", result["reply"])
        self.assertEqual(result["tool_calls"][0]["route"], "local")
        set_power.assert_awaited_once_with(thermostat["entity_id"], True)

    def test_air_conditioner_power_ignores_status_temperature_and_mode_helpers(self):
        functions = load_preference_functions()
        thermostat = {
            "entity_id": "climate.living_room_air_conditioner_thermostat",
            "friendly_name": "Living room Air Conditioner Thermostat",
            "domain": "climate",
            "control_approved": True,
            "score": 80,
        }
        helpers = [
            ("binary_sensor.living_room_air_conditioner_device_status", "binary_sensor", "Living room Air Conditioner Device Status"),
            ("sensor.living_room_air_conditioner_indoor_temperature", "sensor", "Living room Air Conditioner Indoor Temperature"),
            ("select.living_room_air_conditioner_running_mode", "select", "Living room Air Conditioner Running Mode"),
        ]
        set_power = AsyncMock(return_value={
            "verified_state": "off",
            "friendly_name": thermostat["friendly_name"],
        })
        functions.update(
            {
                "PENDING_LOW_RISK_ACTIONS": {},
                "get_session_entity": lambda session_id: None,
                "is_entity_followup": lambda message: False,
                "parse_local_ha_intent": lambda message: {
                    "kind": "control", "query": "living room air condition", "turn_on": False,
                },
                "find_approved_entities": lambda query: {
                    "recommended_unique_match": None,
                    "matches": [
                        *[
                            {
                                "entity_id": entity_id,
                                "friendly_name": name,
                                "domain": domain,
                                "control_approved": True,
                                "score": 100,
                            }
                            for entity_id, domain, name in helpers
                        ],
                        thermostat,
                    ],
                },
                "load_preferences": lambda: {"confirmation_strictness": "standard"},
                "ha_set_power": set_power,
                "remember_session_entity": lambda *args: None,
            }
        )

        result = asyncio.run(functions["try_local_ha_route"](
            "turn off living room air condition", "test"
        ))

        self.assertIn("now off", result["reply"])
        set_power.assert_awaited_once_with(thermostat["entity_id"], False)

    def test_pronunciation_rules_do_not_change_unrelated_words(self):
        functions = load_preference_functions()
        functions["load_preferences"] = lambda: {
            "pronunciation_dictionary": "HA = H A\nNicosia = Nee-koh-see-ah"
        }
        self.assertEqual(
            functions["apply_pronunciation_dictionary"]("HA status in Nicosia"),
            "H A status in Nee-koh-see-ah",
        )


if __name__ == "__main__":
    unittest.main()
