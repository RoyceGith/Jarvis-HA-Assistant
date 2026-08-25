import ast
from pathlib import Path
import json
import tempfile
import unittest
from typing import Any

from jarvis.app.domains import developer_state


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
OPENAI = (APP / "services/openai_responses.py").read_text(encoding="utf-8")
DEVELOPER = (APP / "domains/developer_state.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def load_openai_functions(*names: str) -> dict[str, Any]:
    tree = ast.parse(OPENAI)
    selected = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    namespace = {"Any": Any, "json": json}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "<openai>", "exec"), namespace)
    return namespace


class OpenAIAndDeveloperStateBoundaryTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.40"', CONFIG)
        self.assertIn('version="0.13.40"', MAIN)
        self.assertIn("HUD 0.13.40", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.40")

    def test_both_modules_are_outside_composition_root(self):
        self.assertNotIn("async def create_openai_response(", MAIN)
        self.assertNotIn("def developer_mode_enabled(", MAIN)
        self.assertIn("async def create_openai_response(", OPENAI)
        self.assertIn("def developer_mode_enabled(", DEVELOPER)
        self.assertIn("configure_openai_responses(", MAIN)
        self.assertIn("DEVELOPER_STATE_PATH", MAIN)

    def test_openai_text_function_call_and_error_contracts(self):
        functions = load_openai_functions("response_text", "function_calls", "openai_error_message")
        response = {
            "output": [
                {"type": "message", "content": [
                    {"type": "output_text", "text": "First"},
                    {"type": "output_text", "text": "Second"},
                ]},
                {"type": "function_call", "name": "tool", "arguments": "{}"},
            ],
        }
        self.assertEqual(functions["response_text"](response), "First\nSecond")
        self.assertEqual(functions["function_calls"](response)[0]["name"], "tool")

        class InvalidJsonResponse:
            status_code = 502
            text = "upstream unavailable"

            @staticmethod
            def json():
                raise json.JSONDecodeError("invalid", "", 0)

        self.assertEqual(
            functions["openai_error_message"](InvalidJsonResponse()),
            "OpenAI HTTP 502: upstream unavailable",
        )

    def test_developer_mode_round_trip_preserves_payload_and_safety_instructions(self):
        original_path = developer_state.DEVELOPER_STATE_PATH
        with tempfile.TemporaryDirectory() as directory:
            developer_state.DEVELOPER_STATE_PATH = Path(directory) / "zbrano_developer_mode.json"
            try:
                developer_state.set_developer_mode(True)
                payload = json.loads(developer_state.DEVELOPER_STATE_PATH.read_text(encoding="utf-8"))
                self.assertTrue(payload["enabled"])
                self.assertGreater(payload["updated_at"], 0)
                self.assertTrue(developer_state.developer_mode_enabled())
                instructions = developer_state.developer_system_instructions("base")
                self.assertIn("RoyceGith/Jarvis-HA-Assistant", instructions)
                self.assertIn("approval-gated", instructions)
                self.assertIn("investigate_zbrano_feature exactly once", instructions)
            finally:
                developer_state.DEVELOPER_STATE_PATH = original_path


if __name__ == "__main__":
    unittest.main()
