import json
from pathlib import Path
import unittest

from zbrano.app.services import runtime_routing


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
INDEX = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
ROUTING = (ROOT / "zbrano/app/services/runtime_routing.py").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class ContextualMcpRoutingReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.248"', CONFIG)
        self.assertIn('version="0.13.248"', MAIN)
        self.assertIn("HUD 0.13.248", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.248")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.247")

    def test_unrelated_remote_mcp_is_removed_from_ordinary_chat(self):
        tools = [
            {"type": "function", "name": "local_tool"},
            {"type": "mcp", "server_description": "Workshop Memory", "server_url": "https://example.test/mcp"},
        ]
        selected = runtime_routing._contextual_default_tools(
            tools, "give me some winter soup recipes with beef"
        )
        self.assertEqual(selected, [{"type": "function", "name": "local_tool"}])

    def test_explicitly_named_connector_remains_available(self):
        connector = {
            "type": "mcp",
            "server_description": "Google Drive",
            "server_url": "https://drive.example.test/mcp",
        }
        selected = runtime_routing._contextual_default_tools(
            [connector], "Search Google Drive for the warranty PDF"
        )
        self.assertEqual(selected, [connector])

    def test_priority_routes_still_bypass_default_connectors(self):
        self.assertIn("Keep optional remote MCP dependencies", ROUTING)
        self.assertIn("_contextual_default_tools(_default_tools(), message)", ROUTING)


if __name__ == "__main__":
    unittest.main()
