import asyncio
import time
import unittest
from unittest.mock import patch

import httpx
from zbrano.app.services import plugin_catalog as catalog
from zbrano.app.services.plugin_policy import validate_plugin_url


class CatalogLoadingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.cache = {}
        self.state = patch.multiple(
            catalog, _catalog_refresh_task=None, _catalog_retry_at=0.0, _catalog_error=None,
            _plugin_load=lambda path: self.cache,
            _plugin_save=lambda path, value: self.cache.update(value),
            _plugin_registry=lambda: {},
            _validate_plugin_url=lambda url: validate_plugin_url(url, resolve_dns=False),
        )
        self.state.start()
        self.addCleanup(self.state.stop)

    async def asyncTearDown(self):
        await catalog.stop_plugin_catalog_refresh()

    async def test_cold_catalog_returns_featured_without_waiting_and_shares_refresh(self):
        release = asyncio.Event()
        entered = asyncio.Event()
        calls = []
        async def refresh(force=False):
            calls.append(force)
            entered.set()
            await release.wait()
            self.cache.update(saved_at=time.time(), plugins=[{"id": "new", "title": "New", "url": "https://example.com/mcp"}])
            return self.cache["plugins"], False, None
        with patch.object(catalog, "_refresh_plugin_catalog", refresh):
            first = await asyncio.wait_for(catalog.plugin_catalog_payload(), .2)
            await entered.wait()
            second = await asyncio.wait_for(catalog.plugin_catalog_payload(refresh=True), .2)
            self.assertTrue(first["refreshing"])
            self.assertTrue(second["refreshing"])
            self.assertTrue(any(p["id"] == "github-official" for p in first["plugins"]))
            self.assertEqual(calls, [True])
            release.set()
            await catalog._catalog_refresh_task
            final = await catalog.plugin_catalog_payload()
            self.assertFalse(final["refreshing"])
            self.assertTrue(any(p["id"] == "new" for p in final["plugins"]))

    async def test_timeout_preserves_stale_cache_and_backs_off(self):
        self.cache.update(saved_at=1, plugins=[{"id": "saved", "title": "Saved", "url": "https://example.com/mcp"}])
        before = dict(self.cache)
        async def slow_registry(request):
            await asyncio.sleep(1)
            return httpx.Response(200, json={"servers": []})
        client = httpx.AsyncClient(transport=httpx.MockTransport(slow_registry))
        with patch("httpx.AsyncClient", return_value=client), patch.object(catalog, "PLUGIN_CATALOG_REFRESH_TIMEOUT", .01):
            initial = await catalog.plugin_catalog_payload()
            self.assertTrue(any(p["id"] == "saved" for p in initial["plugins"]))
            task = catalog._catalog_refresh_task
            await asyncio.wait_for(task, .3)
            after = await catalog.plugin_catalog_payload()
            self.assertIs(catalog._catalog_refresh_task, task)
            self.assertFalse(after["refreshing"])
            self.assertTrue(after["registry_error"])
            self.assertEqual(self.cache, before)

    async def test_catalog_normalization_does_not_resolve_hosts(self):
        with patch("socket.getaddrinfo", side_effect=AssertionError("Display must not resolve DNS")):
            for index in range(1000):
                entry = catalog.catalog_remote_entry({"name": f"plugin-{index}", "remotes": [{"url": f"https://host{index}.example/mcp"}]})
                self.assertTrue(entry["installable"])
        with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 443))]) as dns:
            with self.assertRaises(ValueError):
                validate_plugin_url("https://example.com/mcp")
            dns.assert_called_once()
        for url in ["http://example.com", "https://localhost/mcp", "https://127.0.0.1/mcp", "https://user:secret@example.com", "https://example.com:bad"]:
            with self.assertRaises(ValueError):
                validate_plugin_url(url, resolve_dns=False)

    async def test_fresh_cache_does_not_start_refresh_and_shutdown_cancels_pending(self):
        self.cache.update(saved_at=time.time(), plugins=[])
        await catalog.plugin_catalog_payload()
        self.assertIsNone(catalog._catalog_refresh_task)
        async def wait_forever(force=False):
            await asyncio.Event().wait()
        with patch.object(catalog, "_refresh_plugin_catalog", wait_forever):
            await catalog.plugin_catalog_payload(refresh=True)
            task = catalog._catalog_refresh_task
            await asyncio.sleep(0)
            await catalog.stop_plugin_catalog_refresh()
            self.assertTrue(task.cancelled())
            self.assertIsNone(catalog._catalog_refresh_task)
