import asyncio
import json
from pathlib import Path
import unittest

from jarvis.app.services import google_oauth, plugin_oauth


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
PROTOCOL = (APP / "services/plugin_oauth.py").read_text(encoding="utf-8")
GOOGLE = (APP / "services/google_oauth.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class PluginOAuthBoundaryTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.52"', CONFIG)
        self.assertIn('version="0.13.52"', MAIN)
        self.assertIn("HUD 0.13.52", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.52")

    def test_protocol_and_google_policy_are_outside_main(self):
        for marker in (
            "def _oauth_validate_redirect_uri(",
            "async def _oauth_discover(",
            "async def _oauth_exchange_token(",
            "async def _validate_gmail_oauth_grant(",
            "async def enforce_stored_gmail_scope_policy(",
        ):
            self.assertNotIn(marker, MAIN)
        self.assertIn("def oauth_validate_redirect_uri(", PROTOCOL)
        self.assertIn("async def oauth_discover(", PROTOCOL)
        self.assertIn("async def validate_gmail_oauth_grant(", GOOGLE)
        self.assertIn("configure_plugin_oauth_service(", MAIN)
        self.assertIn("configure_google_oauth_service(", MAIN)

    def test_callback_pkce_and_scope_contracts(self):
        plugin_oauth.configure_plugin_oauth_service(
            plugin_load_fn=lambda path: {"connected": {"scope": "read write"}},
            validate_plugin_url_fn=lambda url: url if url.startswith("https://") else (_ for _ in ()).throw(ValueError("HTTPS required")),
            timeout=15,
            runtime_version="0.13.52",
        )
        self.assertEqual(
            plugin_oauth.oauth_validate_redirect_uri("https://example.com/api/plugin-oauth/callback"),
            "https://example.com/api/plugin-oauth/callback",
        )
        self.assertEqual(
            plugin_oauth.oauth_validate_redirect_uri("http://localhost:8099/api/plugin-oauth/callback"),
            "http://localhost:8099/api/plugin-oauth/callback",
        )
        with self.assertRaises(ValueError):
            plugin_oauth.oauth_validate_redirect_uri("http://example.com/api/plugin-oauth/callback")
        with self.assertRaises(ValueError):
            plugin_oauth.oauth_validate_redirect_uri("https://example.com/api/plugin-oauth/callback?code=x")
        verifier, challenge = plugin_oauth.oauth_pkce()
        self.assertGreater(len(verifier), 40)
        self.assertTrue(challenge)
        self.assertEqual(plugin_oauth.oauth_scope_set("read  write read"), {"read", "write"})
        self.assertEqual(plugin_oauth.plugin_oauth_records()["connected"]["scope"], "read write")

    def test_google_stored_scope_policy_preserves_or_quarantines(self):
        gmail_scopes = ("gmail.readonly", "gmail.compose")
        registry = {"gmail": {"enabled": False}}
        secrets = {"gmail": ""}
        records = {"gmail": {"scope": "gmail.readonly gmail.compose"}}
        saves = {}
        google_oauth.configure_google_oauth_service(
            timeout=15,
            gmail_scopes=gmail_scopes,
            calendar_scopes=("calendar.events",),
            gmail_plugin_id_fn=lambda: "gmail",
            oauth_records_fn=lambda: records,
            oauth_scope_set_fn=plugin_oauth.oauth_scope_set,
            oauth_safe_json_fn=plugin_oauth.oauth_safe_json,
            oauth_validate_url_fn=plugin_oauth.oauth_validate_https_url,
            plugin_registry_fn=lambda: registry,
            plugin_secrets_fn=lambda: secrets,
            plugin_save_fn=lambda path, data: saves.__setitem__(str(path), dict(data)),
            gmail_tool_records_fn=lambda: [{"name": "gmail_search"}],
            registry_path=Path("registry.json"),
            secrets_path=Path("secrets.json"),
            oauth_path=Path("oauth.json"),
        )
        asyncio.run(google_oauth.enforce_stored_gmail_scope_policy())
        self.assertTrue(registry["gmail"]["enabled"])
        self.assertEqual(registry["gmail"]["tools"], [{"name": "gmail_search"}])

        records["gmail"] = {"scope": "gmail.readonly"}
        asyncio.run(google_oauth.enforce_stored_gmail_scope_policy())
        self.assertNotIn("gmail", records)
        self.assertFalse(registry["gmail"]["enabled"])
        self.assertIn("reconnect required", registry["gmail"]["last_error"])


if __name__ == "__main__":
    unittest.main()
