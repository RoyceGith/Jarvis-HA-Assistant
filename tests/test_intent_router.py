import unittest

from jarvis.app.intent_router import parse_local_ha_intent


class IntentRouterTests(unittest.TestCase):
    def test_parse_control_intents(self):
        self.assertEqual(parse_local_ha_intent("Turn on workshop bench"), {
            "kind": "control", "query": "workshop bench", "turn_on": True,
        })
        self.assertEqual(parse_local_ha_intent("switch workshop bench off"), {
            "kind": "control", "query": "workshop bench", "turn_on": False,
        })

    def test_parse_state_intents_and_reject_general_chat(self):
        self.assertEqual(parse_local_ha_intent("Is workshop bench on?"), {
            "kind": "state", "query": "workshop bench", "expected": "on",
        })
        self.assertEqual(parse_local_ha_intent("What is the status of workshop bench?"), {
            "kind": "state", "query": "workshop bench",
        })
        self.assertIsNone(parse_local_ha_intent("Tell me about the workshop"))


if __name__ == "__main__":
    unittest.main()
