from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app import main
from app.domains import conversations, settings


class ApplicationIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        temporary_root = Path(self.temporary.name)
        self.original_settings_path = settings.SETTINGS_STORAGE_PATH
        self.original_chat_path = conversations.CHAT_STORAGE_PATH
        self.original_clear_chat_files = conversations.clear_chat_files
        settings.SETTINGS_STORAGE_PATH = temporary_root / "jarvis_settings.json"
        conversations.CHAT_STORAGE_PATH = temporary_root / "chat_sessions.json"
        conversations.clear_chat_files = lambda session_id=None: None
        conversations.CHAT_SESSIONS.clear()
        conversations.CHAT_SESSION_ORDER.clear()
        conversations.CHAT_SESSION_META.clear()
        conversations.LAST_ENTITY_BY_SESSION.clear()
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=main.app),
            base_url="http://zbrano.test",
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        settings.SETTINGS_STORAGE_PATH = self.original_settings_path
        conversations.CHAT_STORAGE_PATH = self.original_chat_path
        conversations.clear_chat_files = self.original_clear_chat_files
        conversations.CHAT_SESSIONS.clear()
        conversations.CHAT_SESSION_ORDER.clear()
        conversations.CHAT_SESSION_META.clear()
        conversations.LAST_ENTITY_BY_SESSION.clear()
        self.temporary.cleanup()

    async def test_application_import_health_and_frontend_smoke(self) -> None:
        self.assertGreaterEqual(len(main.app.router.on_startup), 2)
        self.assertGreaterEqual(len(main.app.router.on_shutdown), 2)
        approved = {
            "read_entities": ["sensor.workshop_temperature"],
            "control_entities": ["light.workshop"],
        }
        with patch.object(main, "approved_ha_entities", AsyncMock(return_value=approved)):
            response = await self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["version"], "0.13.43")
        self.assertEqual(response.json()["ha_read_entity_count"], 1)
        self.assertEqual(response.json()["ha_control_entity_count"], 1)

        frontend = await self.client.get("/")
        self.assertEqual(frontend.status_code, 200)
        self.assertIn("HUD 0.13.43", frontend.text)
        self.assertEqual(
            frontend.headers.get("cache-control"),
            "no-store, no-cache, must-revalidate, max-age=0",
        )

    async def test_settings_api_round_trip_uses_isolated_persistence(self) -> None:
        initial = await self.client.get("/api/settings")
        self.assertEqual(initial.status_code, 200)
        self.assertEqual(initial.json()["preferences"]["theme"], "dark")

        with patch.object(main, "cancel_release_sync"):
            saved = await self.client.put(
                "/api/settings",
                json={
                    "general_instructions": "Keep integration checks concise.",
                    "theme": "gray",
                    "auto_sync_releases_to_workshop_memory": False,
                },
            )
        self.assertEqual(saved.status_code, 200)
        self.assertTrue(saved.json()["saved"])
        self.assertEqual(saved.json()["preferences"]["theme"], "gray")

        stored = json.loads(settings.SETTINGS_STORAGE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(stored["general_instructions"], "Keep integration checks concise.")
        reread = await self.client.get("/api/settings")
        self.assertEqual(reread.json()["preferences"]["theme"], "gray")

    async def test_chat_api_create_rename_list_and_delete_round_trip(self) -> None:
        created = await self.client.post("/api/chats", json={"session_id": "integration-chat"})
        self.assertEqual(created.status_code, 200)
        self.assertTrue(conversations.CHAT_STORAGE_PATH.is_file())

        renamed = await self.client.put(
            "/api/chats/integration-chat/title",
            json={"title": "Integration smoke test"},
        )
        self.assertEqual(renamed.status_code, 200)
        self.assertEqual(renamed.json()["title"], "Integration smoke test")

        listed = await self.client.get("/api/chats")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["chats"][0]["session_id"], "integration-chat")

        deleted = await self.client.delete("/api/chat/history/integration-chat")
        self.assertEqual(deleted.status_code, 200)
        persisted = json.loads(conversations.CHAT_STORAGE_PATH.read_text(encoding="utf-8"))
        self.assertNotIn("integration-chat", persisted["sessions"])

    async def test_request_validation_rejects_invalid_payload_before_storage(self) -> None:
        response = await self.client.post("/api/chats", json={"session_id": ""})
        self.assertEqual(response.status_code, 422)
        self.assertFalse(conversations.CHAT_STORAGE_PATH.exists())


if __name__ == "__main__":
    unittest.main()
