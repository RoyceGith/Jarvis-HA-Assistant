import ast
import asyncio
from pathlib import Path
import re
import unittest
from typing import Any
from unittest.mock import AsyncMock


MAIN_PATH = Path(__file__).resolve().parents[1] / "jarvis/app/main.py"


def load_preference_functions():
    tree = ast.parse(MAIN_PATH.read_text(encoding="utf-8"))
    selected = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in {"try_local_ha_route", "apply_pronunciation_dictionary"}
    ]
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
