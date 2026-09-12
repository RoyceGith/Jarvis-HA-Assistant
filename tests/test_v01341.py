import asyncio
import json
from pathlib import Path
import time
import unittest

from zbrano.app.services import github_device_oauth


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "zbrano/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
SERVICE = (APP / "services/github_device_oauth.py").read_text(encoding="utf-8")
CATALOG_SERVICE = (APP / "services/plugin_catalog.py").read_text(encoding="utf-8")
PLUGIN_RUNTIME = (APP / "static/js/plugins/runtime.js").read_text(encoding="utf-8")
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class GitHubDeviceFlowBoundaryTests(unittest.TestCase):
    def setUp(self):
        async def catalog_entry(catalog_id):
            if catalog_id == "github-official":
                return {"id": catalog_id, "title": "GitHub", "url": github_device_oauth.GITHUB_MCP_URL}
            if catalog_id == "other":
                return {"id": catalog_id, "title": "Other", "url": "https://example.com/mcp"}
            return None

        async def install_plugin(name, url, token):
            return {"installed": True, "name": name, "url": url, "token": token}

        github_device_oauth.GITHUB_DEVICE_FLOWS.clear()
        github_device_oauth.configure_github_device_oauth(
            timeout=15,
            catalog_entry_fn=catalog_entry,
            install_plugin_fn=install_plugin,
        )

    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.245"', CONFIG)
        self.assertIn('version="0.13.245"', MAIN)
        self.assertIn("HUD 0.13.245", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.245")

    def test_device_flow_implementation_is_outside_main(self):
        self.assertNotIn("GITHUB_DEVICE_FLOWS = {}", MAIN)
        self.assertNotIn("def _github_oauth_client_id(", MAIN)
        self.assertNotIn('"https://github.com/login/device/code"', MAIN)
        self.assertIn("GITHUB_DEVICE_FLOWS:", SERVICE)
        self.assertIn("def github_oauth_client_id(", SERVICE)
        self.assertIn("async def start_github_device_flow(", SERVICE)
        self.assertIn("async def complete_github_device_flow(", SERVICE)
        self.assertIn("configure_github_device_oauth(", MAIN)

    def test_catalog_exposes_and_runs_github_account_connection(self):
        self.assertIn('item["auth_mode"] = "github-oauth"', CATALOG_SERVICE)
        self.assertIn('"Connect with GitHub"', CATALOG_SERVICE)
        self.assertIn('item["installable"] = bool(item["oauth_available"])', CATALOG_SERVICE)
        self.assertIn('data-github-connect=', PLUGIN_RUNTIME)
        self.assertIn('/github-device/start', PLUGIN_RUNTIME)
        self.assertIn('/github-device/${encodeURIComponent(started.flow_id)}/complete', PLUGIN_RUNTIME)
        self.assertLess(
            PLUGIN_RUNTIME.index('item.auth_mode==="github-oauth"'),
            PLUGIN_RUNTIME.index('item.auth_mode==="oauth"'),
        )

    def test_catalog_identity_and_missing_configuration_errors(self):
        with self.assertRaises(github_device_oauth.GitHubDeviceFlowError) as missing:
            asyncio.run(github_device_oauth.start_github_device_flow("missing"))
        self.assertEqual(missing.exception.status_code, 404)
        with self.assertRaises(github_device_oauth.GitHubDeviceFlowError) as wrong:
            asyncio.run(github_device_oauth.start_github_device_flow("other"))
        self.assertEqual(wrong.exception.status_code, 400)
        with self.assertRaises(github_device_oauth.GitHubDeviceFlowError) as unconfigured:
            asyncio.run(github_device_oauth.start_github_device_flow("github-official"))
        self.assertEqual(unconfigured.exception.status_code, 503)

    def test_missing_pending_and_expired_flow_contracts(self):
        with self.assertRaises(github_device_oauth.GitHubDeviceFlowError) as missing:
            asyncio.run(github_device_oauth.complete_github_device_flow("missing"))
        self.assertEqual(missing.exception.status_code, 404)

        github_device_oauth.GITHUB_DEVICE_FLOWS["pending"] = {
            "catalog_id": "github-official",
            "device_code": "device",
            "expires_at": time.time() + 60,
            "interval": 5,
            "next_poll": time.time() + 5,
        }
        pending = asyncio.run(github_device_oauth.complete_github_device_flow("pending"))
        self.assertTrue(pending["pending"])
        self.assertGreaterEqual(pending["interval"], 1)

        github_device_oauth.GITHUB_DEVICE_FLOWS["expired"] = {
            "catalog_id": "github-official",
            "device_code": "device",
            "expires_at": time.time() - 1,
            "interval": 5,
            "next_poll": 0,
        }
        with self.assertRaises(github_device_oauth.GitHubDeviceFlowError) as expired:
            asyncio.run(github_device_oauth.complete_github_device_flow("expired"))
        self.assertEqual(expired.exception.status_code, 410)
        self.assertNotIn("expired", github_device_oauth.GITHUB_DEVICE_FLOWS)


if __name__ == "__main__":
    unittest.main()
