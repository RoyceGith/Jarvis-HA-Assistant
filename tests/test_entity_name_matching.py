import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from tests.test_preferences import load_preference_functions
from zbrano.app.intent_router import parse_local_ha_intent
from zbrano.app.services import entity_policy


def record(name, access="low_risk_control_proposed", enabled=True, aliases=None):
    return {"friendly_name": name, "domain": "climate", "access": access, "enabled": enabled, "aliases": aliases or []}


class EntityNameMatchingTests(unittest.TestCase):
    def setUp(self):
        self.policy = {
            "climate.living": record("Living room Air Conditioner Thermostat"),
            "climate.bedroom": record("Bedroom AirCondition Thermostat"),
            "climate.generic": record("ZBRANO Aircondition"),
        }
        self.patches = patch.multiple(entity_policy, load_entity_policy=lambda: self.policy,
                                      _automation_store=lambda: {}, HA_READ_ENTITIES=set(), HA_CONTROL_ENTITIES=set())
        self.patches.start()
        self.addCleanup(self.patches.stop)

    def route(self, message):
        functions = load_preference_functions()
        power = AsyncMock(return_value={"verified_state": "off", "friendly_name": "Living room Air Conditioner Thermostat"})
        functions.update(PENDING_LOW_RISK_ACTIONS={}, get_session_entity=lambda session: None,
                         is_entity_followup=lambda message: False, parse_local_ha_intent=parse_local_ha_intent,
                         find_approved_entities=entity_policy.find_approved_entities,
                         load_preferences=lambda: {"confirmation_strictness": "standard"},
                         ha_set_power=power, remember_session_entity=lambda *args: None)
        result = asyncio.run(functions["try_local_ha_route"](message, "matching-test"))
        return result, power

    def test_joined_spaced_and_hyphenated_forms_resolve_same_device(self):
        for query in ["livingroom aircondition", "living room aircondition", "living-room air-conditioner", "living_room air conditioning", "LivingRoom AirCondition"]:
            with self.subTest(query=query):
                lookup = entity_policy.find_approved_entities(query)
                self.assertEqual(lookup["recommended_unique_match"]["entity_id"], "climate.living")
                result, power = self.route("turn off " + query)
                power.assert_awaited_once_with("climate.living", False)
                self.assertIn("now off", result["reply"])

    def test_missing_disabled_or_read_only_room_never_controls_another_room(self):
        for replacement in [None, record("Living room Air Conditioner Thermostat", enabled=False), record("Living room Air Conditioner Thermostat", access="read_only")]:
            with self.subTest(replacement=replacement):
                self.policy.pop("climate.living", None)
                if replacement is not None: self.policy["climate.living"] = replacement
                result, power = self.route("turn off livingroom aircondition")
                power.assert_not_awaited()
                self.assertIn("could not find", result["reply"])

    def test_real_room_ambiguity_still_asks(self):
        self.policy["climate.second"] = record("Living Room Air Conditioner Thermostat")
        result, power = self.route("turn off livingroom aircondition")
        power.assert_not_awaited()
        self.assertIn("Which one?", result["reply"])
        self.assertNotIn("Bedroom", result["reply"])

    def test_aliases_are_normalized_without_changing_saved_text(self):
        self.policy["climate.living"]["aliases"] = ["DiningRoom AirCon"]
        result = entity_policy.find_approved_entities("dining room air conditioner")
        self.assertEqual(result["recommended_unique_match"]["entity_id"], "climate.living")
        self.assertEqual(self.policy["climate.living"]["aliases"], ["DiningRoom AirCon"])

    def test_short_generic_name_cannot_outscore_explicit_room(self):
        self.policy["climate.generic"] = record("Aircondition")
        result, power = self.route("turn off livingroom aircondition")
        power.assert_awaited_once_with("climate.living", False)
        self.assertIn("now off", result["reply"])
