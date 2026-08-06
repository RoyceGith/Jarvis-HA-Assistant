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
        "load_settings_payload",
        "save_settings_payload",
        "load_general_instructions",
        "save_general_instructions",
        "load_elevenlabs_voice_settings",
        "save_elevenlabs_voice_settings",
        "append_general_instruction",
        "load_preferences",
        "save_preferences",
        "apply_pronunciation_dictionary",
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
        "ELEVENLABS_VOICE_DEFAULTS": {
            "stability": 0.55,
            "similarity": 0.75,
            "style": 0.15,
            "speed": 0.96,
        },
        "JARVIS_PREFERENCE_DEFAULTS": {
            "elevenlabs_model": "eleven_flash_v2_5",
            "elevenlabs_speaker_boost": True,
            "auto_speak": True,
            "response_length": "balanced",
            "confirmation_strictness": "standard",
            "context_messages": 20,
            "retention_days": 90,
            "preferred_language": "auto",
            "pronunciation_dictionary": "",
            "theme": "dark",
            "reduced_motion": False,
            "text_size": "medium",
            "interface_density": "comfortable",
            "quiet_hours_enabled": False,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "07:00",
            "voice_volume": 0.9,
        },
        "re": __import__("re"),
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

    def test_voice_settings_round_trip_preserves_instructions(self):
        with tempfile.TemporaryDirectory() as temporary:
            storage = Path(temporary) / "jarvis_settings.json"
            functions = load_settings_functions(storage)
            functions["save_general_instructions"]("- Keep answers concise.")
            expected = {
                "stability": 0.42,
                "similarity": 0.88,
                "style": 0.23,
                "speed": 1.05,
            }
            functions["save_elevenlabs_voice_settings"](expected)
            self.assertEqual(functions["load_elevenlabs_voice_settings"](), expected)
            self.assertEqual(
                functions["load_general_instructions"](), "- Keep answers concise."
            )

    def test_invalid_stored_voice_values_fall_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as temporary:
            storage = Path(temporary) / "jarvis_settings.json"
            storage.write_text(
                json.dumps(
                    {
                        "elevenlabs_voice_settings": {
                            "stability": 4,
                            "similarity": "invalid",
                            "style": 0.2,
                            "speed": 0.2,
                        }
                    }
                ),
                encoding="utf-8",
            )
            functions = load_settings_functions(storage)
            self.assertEqual(
                functions["load_elevenlabs_voice_settings"](),
                {"stability": 0.55, "similarity": 0.75, "style": 0.2, "speed": 0.96},
            )

    def test_preferences_and_pronunciation_round_trip(self):
        with tempfile.TemporaryDirectory() as temporary:
            storage = Path(temporary) / "jarvis_settings.json"
            functions = load_settings_functions(storage)
            preferences = dict(functions["JARVIS_PREFERENCE_DEFAULTS"])
            preferences.update({"theme": "gray", "pronunciation_dictionary": "HA = H A"})
            functions["save_preferences"](preferences)
            self.assertEqual(functions["load_preferences"]()["theme"], "gray")
            self.assertEqual(functions["apply_pronunciation_dictionary"]("Ask HA now"), "Ask H A now")


if __name__ == "__main__":
    unittest.main()
