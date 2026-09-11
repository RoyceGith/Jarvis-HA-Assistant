import ast
from pathlib import Path
import json
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
        self.assertIn('version: "0.13.215"', CONFIG)
        self.assertIn('version="0.13.215"', MAIN)
        self.assertIn("HUD 0.13.215", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.215")

    def test_both_modules_are_outside_composition_root(self):
        self.assertNotIn("async def create_openai_response(", MAIN)
        self.assertNotIn("def developer_mode_enabled(", MAIN)
        self.assertIn("async def create_openai_response(", OPENAI)
        self.assertIn("def developer_mode_enabled(", DEVELOPER)
        self.assertIn("configure_openai_responses(", MAIN)
        self.assertNotIn("DEVELOPER_STATE_PATH", MAIN)

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

    def test_developer_mode_is_permanently_disabled_in_customer_builds(self):
        self.assertFalse(developer_state.developer_mode_enabled())
        self.assertEqual(developer_state.developer_system_instructions("base"), "base")
        self.assertNotIn("def set_developer_mode", DEVELOPER)
        self.assertNotIn('@app.get("/api/developer/', MAIN)
        self.assertNotIn('@app.post("/api/developer/', MAIN)
        self.assertNotIn('@app.put("/api/developer/', MAIN)


if __name__ == "__main__":
    unittest.main()
