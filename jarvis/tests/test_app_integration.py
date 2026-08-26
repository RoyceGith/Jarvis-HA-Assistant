from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app import main
from app.domains import automations, calendar, conversations, notifications, settings
from app.services import entity_policy


class FakeHomeAssistant:
    connected = True

    async def get_state(self, entity_id: str):
        return {
            "entity_id": entity_id,
            "state": "off",
            "attributes": {"friendly_name": "Workshop Door"},
        }


class ApplicationIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        temporary_root = Path(self.temporary.name)
        self.original_settings_path = settings.SETTINGS_STORAGE_PATH
        self.original_chat_path = conversations.CHAT_STORAGE_PATH
        self.original_automation_path = automations.AUTOMATION_STORAGE_PATH
        self.original_calendar_path = calendar.CALENDAR_STORAGE_PATH
        self.original_notification_path = notifications.NOTIFICATION_STORAGE_PATH
        self.original_main_chat_path = main.CHAT_STORAGE_PATH
        self.original_main_entity_policy_path = main.ENTITY_POLICY_PATH
        self.original_entity_data_dir = entity_policy.DATA_DIR
        self.original_entity_policy_path = entity_policy.ENTITY_POLICY_PATH
        self.original_v063_policy_path = entity_policy.V063_ENTITY_POLICY_PATH
        self.original_v063_marker = entity_policy.V063_MIGRATION_MARKER
        self.original_clear_chat_files = conversations.clear_chat_files
        settings.SETTINGS_STORAGE_PATH = temporary_root / "jarvis_settings.json"
        conversations.CHAT_STORAGE_PATH = temporary_root / "chat_sessions.json"
        automations.AUTOMATION_STORAGE_PATH = temporary_root / "autonomous_automations.json"
        calendar.CALENDAR_STORAGE_PATH = temporary_root / "zbrano_calendar.json"
        notifications.NOTIFICATION_STORAGE_PATH = temporary_root / "notification_center.json"
        main.CHAT_STORAGE_PATH = conversations.CHAT_STORAGE_PATH
        main.ENTITY_POLICY_PATH = temporary_root / "entity_policy.json"
        entity_policy.DATA_DIR = temporary_root
        entity_policy.ENTITY_POLICY_PATH = main.ENTITY_POLICY_PATH
        entity_policy.V063_ENTITY_POLICY_PATH = temporary_root / "legacy-share-policy.json"
        entity_policy.V063_MIGRATION_MARKER = temporary_root / ".entity_policy_v063_migrated"
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
        automations.AUTOMATION_STORAGE_PATH = self.original_automation_path
        calendar.CALENDAR_STORAGE_PATH = self.original_calendar_path
        notifications.NOTIFICATION_STORAGE_PATH = self.original_notification_path
        main.CHAT_STORAGE_PATH = self.original_main_chat_path
        main.ENTITY_POLICY_PATH = self.original_main_entity_policy_path
        entity_policy.DATA_DIR = self.original_entity_data_dir
        entity_policy.ENTITY_POLICY_PATH = self.original_entity_policy_path
        entity_policy.V063_ENTITY_POLICY_PATH = self.original_v063_policy_path
        entity_policy.V063_MIGRATION_MARKER = self.original_v063_marker
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
        self.assertEqual(response.json()["version"], "0.13.52")
        self.assertEqual(response.json()["ha_read_entity_count"], 1)
        self.assertEqual(response.json()["ha_control_entity_count"], 1)

        frontend = await self.client.get("/")
        self.assertEqual(frontend.status_code, 200)
        self.assertIn("HUD 0.13.52", frontend.text)
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

    async def test_legacy_minimal_backup_restores_without_newer_optional_sections(self) -> None:
        legacy_backup = {
            "format": "jarvis-backup-v1",
            "created_at": 1_700_000_000,
            "settings": {
                "version": 1,
                "general_instructions": "Preserve this legacy instruction.",
                "preferences": {"theme": "gray"},
            },
            "chats": {
                "version": 1,
                "sessions": {
                    "legacy-chat": {
                        "title": "Legacy chat",
                        "updated_at": 1_700_000_000,
                        "messages": [
                            {"role": "user", "content": "Remember the old setup."},
                            {"role": "assistant", "content": "Preserved."},
                        ],
                    }
                },
            },
            "entity_policy": {
                "version": 1,
                "entities": {
                    "sensor.legacy_temperature": {
                        "entity_id": "sensor.legacy_temperature",
                        "friendly_name": "Legacy temperature",
                        "enabled": True,
                        "access": "read_only",
                        "aliases": ["old temperature"],
                    }
                },
            },
        }

        response = await self.client.post(
            "/api/settings/restore",
            json={"backup": legacy_backup},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["restored"])
        self.assertEqual(response.json()["chat_count"], 1)
        self.assertEqual(settings.load_general_instructions(), "Preserve this legacy instruction.")
        self.assertEqual(conversations.CHAT_SESSION_META["legacy-chat"]["title"], "Legacy chat")
        self.assertEqual(
            entity_policy.load_entity_policy()["sensor.legacy_temperature"]["aliases"],
            ["old temperature"],
        )

    async def test_malformed_migration_backup_is_rejected_before_any_write(self) -> None:
        settings.save_settings_payload({"version": 3, "general_instructions": "Keep me."})
        original_settings = settings.SETTINGS_STORAGE_PATH.read_text(encoding="utf-8")
        malformed_backup = {
            "format": "jarvis-backup-v1",
            "settings": {"version": 1, "general_instructions": "Do not write me."},
            "chats": {"version": 1, "sessions": {}},
            "entity_policy": {"version": 1, "entities": {}},
            "automations": {"settings": {}, "automations": "not-a-list"},
        }

        response = await self.client.post(
            "/api/settings/restore",
            json={"backup": malformed_backup},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            settings.SETTINGS_STORAGE_PATH.read_text(encoding="utf-8"),
            original_settings,
        )

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

    async def test_automation_api_create_read_and_delete_round_trip(self) -> None:
        with patch.object(automations, "ensure_read_allowed"):
            created = await self.client.post(
                "/api/automations",
                json={
                    "name": "Workshop temperature suggestion",
                    "objective": "Suggest cooling when the workshop becomes too warm.",
                    "trigger_entity": "sensor.workshop_temperature",
                    "trigger_operator": "above",
                    "trigger_value": "27",
                    "proposal_template": "The workshop is warm. Would you like cooling?",
                },
            )
        self.assertEqual(created.status_code, 200)
        automation_id = created.json()["automation"]["id"]
        self.assertTrue(automations.AUTOMATION_STORAGE_PATH.is_file())

        with patch.object(main, "_automation_refresh_area_context", AsyncMock(return_value={})):
            listed = await self.client.get("/api/automations")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["automations"][0]["id"], automation_id)

        deleted = await self.client.delete(f"/api/automations/{automation_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(automations.automation_store()["automations"], [])

    async def test_calendar_api_create_list_and_cancel_round_trip(self) -> None:
        start_at = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        with patch.object(calendar, "google_calendar_sync_store", return_value={"enabled": False}):
            created = await self.client.post(
                "/api/calendar",
                json={
                    "title": "Integration appointment",
                    "start_at": start_at,
                    "duration_minutes": 30,
                },
            )
            self.assertEqual(created.status_code, 200)
            appointment_id = created.json()["appointment"]["id"]
            self.assertTrue(calendar.CALENDAR_STORAGE_PATH.is_file())

            listed = await self.client.get("/api/calendar")
            self.assertEqual(listed.status_code, 200)
            self.assertEqual(listed.json()["appointments"][0]["id"], appointment_id)

            cancelled = await self.client.delete(f"/api/calendar/{appointment_id}")
            self.assertEqual(cancelled.status_code, 200)
            self.assertEqual((await self.client.get("/api/calendar")).json()["count"], 0)

    async def test_notification_settings_and_watch_round_trip(self) -> None:
        saved = await self.client.put(
            "/api/notifications/settings",
            json={"quiet_hours_enabled": True, "quiet_hours_start": "23:00", "quiet_hours_end": "06:00"},
        )
        self.assertEqual(saved.status_code, 200)
        self.assertTrue(notifications.NOTIFICATION_STORAGE_PATH.is_file())

        channels = [{
            "entity_id": "notify.mobile_app_phone",
            "friendly_name": "Phone",
            "platform": "home_assistant",
            "integration": "mobile_app",
            "available": True,
            "state": "unknown",
            "icon": None,
        }]
        with (
            patch.object(notifications, "ha_ws", FakeHomeAssistant()),
            patch.object(notifications, "notification_channels", AsyncMock(return_value=channels)),
        ):
            created = await self.client.post(
                "/api/notifications/watches",
                json={
                    "name": "Workshop door",
                    "entity_id": "binary_sensor.workshop_door",
                    "trigger_state": "on",
                    "destination": "notify.mobile_app_phone",
                    "message": "The workshop door opened.",
                },
            )
        self.assertEqual(created.status_code, 200)
        watch_id = created.json()["watch"]["id"]

        paused = await self.client.put(
            f"/api/notifications/watches/{watch_id}/state",
            json={"enabled": False},
        )
        self.assertEqual(paused.status_code, 200)
        self.assertEqual(paused.json()["watch"]["status"], "paused")

        with patch.object(main, "notification_channels", AsyncMock(return_value=channels)):
            listed = await self.client.get("/api/notifications")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["watches"][0]["id"], watch_id)

        deleted = await self.client.delete(f"/api/notifications/watches/{watch_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(notifications.notification_watches(), [])


if __name__ == "__main__":
    unittest.main()
