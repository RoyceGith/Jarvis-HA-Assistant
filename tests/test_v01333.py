import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jarvis.app.services import plugin_policy, plugin_storage


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
STORAGE = (APP / "services/plugin_storage.py").read_text(encoding="utf-8")
POLICY = (APP / "services/plugin_policy.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class PluginStorageAndPolicyBoundaryTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.46"', CONFIG)
        self.assertIn('version="0.13.46"', MAIN)
        self.assertIn("HUD 0.13.46", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.46")

    def test_both_services_are_outside_composition_root(self):
        self.assertNotIn("def _plugin_load(", MAIN)
        self.assertNotIn("def validate_plugin_url(", MAIN)
        self.assertIn("def _plugin_load(", STORAGE)
        self.assertIn("def validate_plugin_url(", POLICY)
        self.assertIn("from .services.plugin_storage import (", MAIN)
        self.assertIn("from .services.plugin_policy import (", MAIN)

    def test_plugin_storage_round_trip_preserves_json_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plugins/registry.json"
            expected = {"plugin": {"enabled": True, "tools": []}}
            plugin_storage._plugin_save(path, expected)
            self.assertEqual(plugin_storage._plugin_load(path), expected)
            if os.name != "nt":
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertIn("temporary.chmod(0o600)", STORAGE)
            self.assertIn("path.chmod(0o600)", STORAGE)

    def test_endpoint_icon_and_github_permission_policy_are_preserved(self):
        with self.assertRaisesRegex(ValueError, "Local MCP endpoints are blocked"):
            plugin_policy.validate_plugin_url("https://localhost/tools")
        with patch.object(
            plugin_policy.socket,
            "getaddrinfo",
            return_value=[(None, None, None, None, ("8.8.8.8", 443))],
        ):
            self.assertEqual(
                plugin_policy.validate_plugin_url("https://example.com/mcp"),
                "https://example.com/mcp",
            )
        self.assertEqual(plugin_policy.plugin_icon_url("GitHub", ""), "plugin-icons/github.svg")

        registry = {"github": {
            "name": "GitHub",
            "url": "https://api.githubcopilot.com/mcp/",
            "enabled": False,
            "tools": [
                {"name": "read", "permission": "read_only", "enabled": False},
                {"name": "write", "permission": "blocked", "enabled": False},
            ],
        }}
        self.assertTrue(plugin_policy._apply_github_tool_policy(registry))
        self.assertTrue(registry["github"]["enabled"])
        self.assertEqual(registry["github"]["tools"][0]["permission"], "read_only")
        self.assertEqual(registry["github"]["tools"][1]["permission"], "write")
        self.assertTrue(all(tool["enabled"] for tool in registry["github"]["tools"]))


if __name__ == "__main__":
    unittest.main()
