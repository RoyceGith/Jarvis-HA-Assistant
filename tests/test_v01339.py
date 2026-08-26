import asyncio
import json
from pathlib import Path
import unittest

from jarvis.app.services import plugin_catalog


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
SERVICE = (APP / "services/plugin_catalog.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class PluginCatalogBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.saved = {}
        self.registry = {
            "gmail-id": {"name": "Gmail Direct", "url": "https://gmail.googleapis.com/gmail/v1", "enabled": True},
        }
        plugin_catalog.configure_plugin_catalog_service(
            plugin_load_fn=lambda path: self.saved.get(str(path), {}),
            plugin_save_fn=lambda path, data: self.saved.__setitem__(str(path), data),
            validate_plugin_url_fn=lambda url: url,
            plugin_icon_url_fn=lambda name, url: "icon.svg",
            plugin_registry_fn=lambda: self.registry,
            plugin_url_key_fn=lambda url: str(url or "").rstrip("/").lower(),
            gmail_plugin_id_fn=lambda: "gmail-id",
            google_calendar_plugin_id_fn=lambda: "calendar-id",
            github_oauth_client_id_fn=lambda: "github-client",
        )

    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.50"', CONFIG)
        self.assertIn('version="0.13.50"', MAIN)
        self.assertIn("HUD 0.13.50", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.50")

    def test_catalog_implementation_is_outside_main(self):
        self.assertNotIn("FEATURED_REMOTE_PLUGINS = [", MAIN)
        self.assertNotIn("def _catalog_remote_entry(", MAIN)
        self.assertNotIn("async def _fetch_plugin_catalog(", MAIN)
        self.assertIn("FEATURED_REMOTE_PLUGINS = [", SERVICE)
        self.assertIn("def catalog_remote_entry(", SERVICE)
        self.assertIn("async def fetch_plugin_catalog(", SERVICE)
        self.assertIn("configure_plugin_catalog_service(", MAIN)

    def test_package_only_and_remote_registry_entries_preserve_contract(self):
        package_only = plugin_catalog.catalog_remote_entry({
            "name": "example/package",
            "packages": [{"registryType": "npm", "identifier": "@example/mcp"}],
        })
        self.assertEqual(package_only["package_ref"], "npm:@example/mcp")
        self.assertFalse(package_only["installable"])
        remote = plugin_catalog.catalog_remote_entry({
            "name": "example/remote",
            "title": "Example Search",
            "remotes": [{"url": "https://example.com/mcp", "authentication": {"type": "oauth"}}],
        })
        self.assertTrue(remote["installable"])
        self.assertTrue(remote["auth_required"])
        self.assertEqual(remote["category"], "data")

    def test_featured_deduplication_and_installed_oauth_presentation(self):
        merged = plugin_catalog.catalog_with_featured([
            dict(plugin_catalog.FEATURED_REMOTE_PLUGINS[0]),
            {"id": "extra", "url": "https://example.com/mcp"},
        ])
        self.assertEqual(sum(item["id"] == "github-official" for item in merged), 1)

        original_fetch = plugin_catalog.fetch_plugin_catalog

        async def fake_fetch(force=False):
            return [dict(item) for item in plugin_catalog.FEATURED_REMOTE_PLUGINS], False, None

        plugin_catalog.fetch_plugin_catalog = fake_fetch
        try:
            payload = asyncio.run(plugin_catalog.plugin_catalog_payload())
        finally:
            plugin_catalog.fetch_plugin_catalog = original_fetch
        gmail = next(item for item in payload["plugins"] if item["id"] == "gmail-official")
        github = next(item for item in payload["plugins"] if item["id"] == "github-official")
        self.assertTrue(gmail["installed"])
        self.assertTrue(gmail["installed_enabled"])
        self.assertTrue(github["oauth_available"])

    def test_result_contract_rejects_malformed_fetches(self):
        with self.assertRaises(RuntimeError):
            plugin_catalog.verify_catalog_result_contract(([], "false", None))


if __name__ == "__main__":
    unittest.main()
