import ast
import json
from pathlib import Path
import unittest
from typing import Any

from jarvis.app.services import plugin_presentation


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
PRESENTATION = (APP / "services/plugin_presentation.py").read_text(encoding="utf-8")
DISCOVERY = (APP / "services/plugin_discovery.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def load_mcp_response_decoder():
    tree = ast.parse(DISCOVERY)
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_mcp_response_json"
    )
    namespace = {"Any": Any, "json": json}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "<plugin_discovery>", "exec"), namespace)
    return namespace["_mcp_response_json"]


class PluginPresentationAndDiscoveryBoundaryTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.48"', CONFIG)
        self.assertIn('version="0.13.48"', MAIN)
        self.assertIn("HUD 0.13.48", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.48")

    def test_both_services_are_outside_composition_root_and_configured(self):
        self.assertNotIn("def plugin_public(", MAIN)
        self.assertNotIn("async def discover_plugin_tools(", MAIN)
        self.assertIn("def plugin_public(", PRESENTATION)
        self.assertIn("async def discover_plugin_tools(", DISCOVERY)
        self.assertIn("configure_plugin_presentation(", MAIN)
        self.assertIn("configure_plugin_discovery(", MAIN)

    def test_public_payload_preserves_oauth_and_permission_summary(self):
        plugin_presentation.configure_plugin_presentation(
            plugin_secrets_fn=lambda: {"github": "secret"},
            plugin_oauth_records_fn=lambda: {"github": {"scope": "repo read:user"}},
            oauth_scope_set_fn=lambda raw: set(str(raw).split()),
        )
        payload = plugin_presentation.plugin_public("github", {
            "name": "GitHub",
            "url": "https://api.githubcopilot.com/mcp/",
            "enabled": True,
            "healthy": True,
            "auth_mode": "oauth",
            "tools": [
                {"name": "read", "enabled": True, "permission": "read_only"},
                {"name": "write", "enabled": True, "permission": "write"},
                {"name": "blocked", "enabled": True, "permission": "blocked"},
            ],
        })
        self.assertTrue(payload["has_secret"])
        self.assertTrue(payload["oauth_connected"])
        self.assertEqual(payload["oauth_scopes"], ["read:user", "repo"])
        self.assertEqual(payload["enabled_tool_count"], 2)
        self.assertEqual(payload["approval_tool_count"], 1)
        self.assertTrue(payload["available_to_chat"])

    def test_mcp_json_and_sse_decoding_and_discovery_limits_are_preserved(self):
        decoder = load_mcp_response_decoder()

        class Response:
            def __init__(self, content_type, text="", payload=None):
                self.headers = {"content-type": content_type}
                self.text = text
                self.payload = payload

            def json(self):
                return self.payload

        self.assertEqual(decoder(Response("application/json", payload={"result": 1})), {"result": 1})
        self.assertEqual(
            decoder(Response("text/event-stream", 'data: {"result":{"tools":[]}}\n')),
            {"result": {"tools": []}},
        )
        self.assertIn("tools[:100]", DISCOVERY)
        self.assertIn("name[:128]", DISCOVERY)
        self.assertIn("[:1000]", DISCOVERY)
        self.assertIn("MCP redirects are blocked", DISCOVERY)
        self.assertIn('"protocolVersion": "2025-06-18"', DISCOVERY)


if __name__ == "__main__":
    unittest.main()
