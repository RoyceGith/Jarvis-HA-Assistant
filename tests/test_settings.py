import ast
import json
from pathlib import Path
import tempfile
import time
import unittest
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = ROOT / "jarvis/app/main.py"


def load_settings_functions(storage_path: Path):
    source = MAIN_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {
        "load_general_instructions",
        "save_general_instructions",
        "append_general_instruction",
    }
    selected = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    namespace = {
        "Any": Any,
        "Path": Path,
        "json": json,
        "time": time,
        "SETTINGS_STORAGE_PATH": storage_path,
        "GENERAL_INSTRUCTIONS_MAX_CHARS": 12000,
    }
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(MAIN_PATH), "exec"), namespace)
    return namespace


class SettingsTests(unittest.TestCase):
    def test_round_trip_append_and_deduplicate(self):
        with tempfile.TemporaryDirectory() as temporary:
            storage = Path(temporary) / "jarvis_settings.json"
            functions = load_settings_functions(storage)
            functions["save_general_instructions"]("- Keep answers concise.")
            result = functions["append_general_instruction"](
                "When giving options, recommend one and explain why."
            )
            self.assertTrue(result["saved"])
            saved = functions["load_general_instructions"]()
            self.assertIn("Keep answers concise.", saved)
            self.assertIn("recommend one and explain why", saved)

            duplicate = functions["append_general_instruction"]("Keep answers concise.")
            self.assertFalse(duplicate["saved"])
            self.assertEqual(duplicate["reason"], "already_saved")

    def test_character_limit(self):
        with tempfile.TemporaryDirectory() as temporary:
            storage = Path(temporary) / "jarvis_settings.json"
            functions = load_settings_functions(storage)
            with self.assertRaises(ValueError):
                functions["save_general_instructions"]("x" * 12001)


if __name__ == "__main__":
    unittest.main()
