from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app import main
from app.domains import automations, calendar, contacts, conversations, fast_memory, notifications, settings
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
        self.original_contacts_path = contacts.CONTACTS_STORAGE_PATH
        self.original_notification_path = notifications.NOTIFICATION_STORAGE_PATH
        self.original_fast_memory_path = fast_memory.FAST_MEMORY_PATH
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
        contacts.CONTACTS_STORAGE_PATH = temporary_root / "zbrano_contacts.json"
        notifications.NOTIFICATION_STORAGE_PATH = temporary_root / "notification_center.json"
        fast_memory.FAST_MEMORY_PATH = temporary_root / "zbrano_fast_memory.sqlite3"
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
        contacts.CONTACTS_STORAGE_PATH = self.original_contacts_path
        notifications.NOTIFICATION_STORAGE_PATH = self.original_notification_path
        fast_memory.FAST_MEMORY_PATH = self.original_fast_memory_path
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
        self.assertEqual(response.json()["version"], "0.13.133")
        self.assertEqual(response.json()["ha_read_entity_count"], 1)
        self.assertEqual(response.json()["ha_control_entity_count"], 1)

        frontend = await self.client.get("/")
        self.assertEqual(frontend.status_code, 200)
        self.assertIn("HUD 0.13.133", frontend.text)
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

    async def test_pre_studio_automation_restores_and_upgrades_without_behavior_loss(self) -> None:
        legacy_automation = {
            "id": "legacy-temperature-rule",
            "name": "Legacy temperature suggestion",
            "objective": "Suggest cooling when the room becomes warm.",
            "trigger_entity": "sensor.legacy_temperature",
            "trigger_operator": "above",
            "trigger_value": "25",
            "trigger_for_seconds": 60,
            "proposal_template": "Would you like me to turn on cooling?",
            "cooldown_minutes": 30,
            "confidence_threshold": 0.75,
            "risk_level": "controlled",
            "enabled": False,
            "status": "draft",
            "created_at": 1_700_000_000,
            "updated_at": 1_700_000_100,
        }
        backup = {
            "format": "jarvis-backup-v1",
            "settings": {"version": 1, "preferences": {"theme": "dark"}},
            "chats": {"version": 1, "sessions": {}},
            "entity_policy": {"version": 1, "entities": {}},
            "automations": {
                "settings": {"operating_mode": "suggest_only"},
                "automations": [legacy_automation],
            },
        }

        restored = await self.client.post("/api/settings/restore", json={"backup": backup})
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json()["automation_count"], 1)

        with patch.object(main, "_automation_refresh_area_context", AsyncMock(return_value={})):
            listed = await self.client.get("/api/automations")
        self.assertEqual(listed.status_code, 200)
        loaded = listed.json()["automations"][0]
        for field in ("id", "trigger_entity", "trigger_operator", "trigger_value", "proposal_template"):
            self.assertEqual(loaded[field], legacy_automation[field])

        with patch.object(automations, "ensure_read_allowed"):
            upgraded = await self.client.put(
                "/api/automations/legacy-temperature-rule",
                json={
                    "name": loaded["name"],
                    "objective": loaded["objective"],
                    "trigger_entity": loaded["trigger_entity"],
                    "trigger_operator": loaded["trigger_operator"],
                    "trigger_value": loaded["trigger_value"],
                    "trigger_for_seconds": loaded["trigger_for_seconds"],
                    "proposal_template": loaded["proposal_template"],
                    "cooldown_minutes": loaded["cooldown_minutes"],
                    "confidence_threshold": loaded["confidence_threshold"],
                    "risk_level": loaded["risk_level"],
                    "enabled": False,
                },
            )
        self.assertEqual(upgraded.status_code, 200)
        current = upgraded.json()["automation"]
        self.assertEqual(current["id"], legacy_automation["id"])
        self.assertEqual(current["created_at"], legacy_automation["created_at"])
        self.assertEqual(current["trigger_entity"], legacy_automation["trigger_entity"])
        self.assertEqual(current["trigger_operator"], legacy_automation["trigger_operator"])
        self.assertEqual(current["trigger_value"], legacy_automation["trigger_value"])
        self.assertEqual(current["proposal_template"], legacy_automation["proposal_template"])
        self.assertEqual(current["triggers"][0]["entity_id"], legacy_automation["trigger_entity"])
        self.assertEqual(current["conditions"], [])
        self.assertEqual(current["actions"], [])
        self.assertEqual(current["branches"], [])

        persisted = json.loads(automations.AUTOMATION_STORAGE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(persisted["automations"][0]["id"], "legacy-temperature-rule")
        self.assertEqual(persisted["automations"][0]["trigger_value"], "25")

    async def test_complete_backup_round_trip_preserves_all_user_data_domains(self) -> None:
        settings.save_settings_payload({
            "version": 3,
            "general_instructions": "Preserve the complete integration backup.",
            "preferences": {"theme": "gray"},
        })
        await self.client.post("/api/chats", json={"session_id": "backup-chat"})
        await self.client.put("/api/chats/backup-chat/title", json={"title": "Backup chat"})
        entity_policy.save_entity_policy({
            "sensor.backup_temperature": {
                "entity_id": "sensor.backup_temperature",
                "friendly_name": "Backup temperature",
                "enabled": True,
                "access": "read_only",
                "aliases": ["backup sensor"],
            },
        })
        automations._automation_save({
            **automations._automation_empty_store(),
            "automations": [{
                "id": "backup-automation",
                "name": "Backup automation",
                "objective": "Preserve this automation.",
                "trigger_entity": "sensor.backup_temperature",
                "trigger_operator": "above",
                "trigger_value": "28",
                "enabled": False,
                "status": "draft",
            }],
        })
        notifications._notification_save({
            "settings": {**notifications.NOTIFICATION_DEFAULT_SETTINGS, "quiet_hours_enabled": True},
            "deliveries": [{
                "id": "backup-delivery",
                "target": "notify.mobile_app_phone",
                "severity": "information",
                "title": "Backup delivery",
                "status": "sent",
                "detail": "Preserve this notification record.",
                "created_at": 1_700_000_200,
            }],
        })
        calendar._calendar_save({
            "appointments": [{
                "id": "backup-appointment",
                "title": "Backup appointment",
                "start_at": "2030-01-01T10:00:00+00:00",
                "start_timestamp": 1_893_492_000,
                "end_timestamp": 1_893_495_600,
                "status": "scheduled",
            }],
        })
        calendar._birthday_save({
            "birthdays": [{
                "id": "backup-birthday",
                "name": "Backup Person",
                "birthday": "09-02",
                "birth_year": 1990,
                "relationship": "Friend",
                "reminder_days_before": [7, 1, 0],
                "destination": "notify.mobile_app_phone",
                "notes": "Preserve this birthday.",
                "gift_ideas": "Books",
                "deliveries": {},
            }],
        })
        contacts._contacts_save({"contacts": [{
            "id": "backup-contact", "kind": "person", "display_name": "Backup Person",
            "phone_numbers": ["+357 99000000"], "emails": ["backup@example.com"],
            "birthday": "09-02", "birth_year": 1990, "bank_accounts": [],
        }]})
        fast_memory.upsert_fast_memory({
            "kind": "preference",
            "subject": "Backup preference",
            "key": "backup_round_trip",
            "value": "Preserve Fast Memory during upgrades.",
            "importance": 4,
            "confidence": 1.0,
        })

        exported = await self.client.get("/api/settings/backup")
        self.assertEqual(exported.status_code, 200)
        backup = exported.json()
        self.assertEqual(set(backup), {
            "format", "created_at", "settings", "chats", "entity_policy",
            "automations", "notifications", "calendar", "birthdays", "contacts", "fast_memory",
        })

        settings.save_settings_payload({"version": 3, "general_instructions": "Replace me."})
        conversations.CHAT_SESSIONS.clear()
        conversations.CHAT_SESSION_ORDER.clear()
        conversations.CHAT_SESSION_META.clear()
        conversations.persist_chat_sessions()
        entity_policy.save_entity_policy({})
        automations._automation_save(automations._automation_empty_store())
        notifications._notification_save({"settings": {}, "deliveries": []})
        calendar._calendar_save({"appointments": []})
        calendar._birthday_save({"birthdays": []})
        contacts._contacts_save({"contacts": []})
        fast_memory.restore_fast_memory({"version": 1, "memories": []})

        restored = await self.client.post("/api/settings/restore", json={"backup": backup})
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(settings.load_general_instructions(), "Preserve the complete integration backup.")
        self.assertEqual(conversations.CHAT_SESSION_META["backup-chat"]["title"], "Backup chat")
        self.assertEqual(
            entity_policy.load_entity_policy()["sensor.backup_temperature"]["aliases"],
            ["backup sensor"],
        )
        self.assertEqual(automations.automation_store()["automations"][0]["id"], "backup-automation")
        self.assertEqual(notifications.notification_store()["deliveries"][0]["id"], "backup-delivery")
        self.assertEqual(calendar.calendar_store()["appointments"][0]["id"], "backup-appointment")
        self.assertEqual(calendar.birthday_store()["birthdays"][0]["id"], "backup-birthday")
        self.assertEqual(contacts.contacts_store()["contacts"][0]["id"], "backup-contact")
        memories = fast_memory.fast_memory_search("upgrades", limit=10)["memories"]
        self.assertEqual(memories[0]["key"], "backup_round_trip")

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

    async def test_studio_workflow_persists_activates_and_evaluates_end_to_end(self) -> None:
        class FlowHomeAssistant:
            connected = True
            state_cache = {
                "sensor.workshop_temperature": {"state": "28", "attributes": {}},
                "binary_sensor.workshop_occupied": {"state": "on", "attributes": {}},
                "climate.workshop": {"state": "cool", "attributes": {"hvac_action": "cooling", "temperature": 25}},
                "light.workshop": {"state": "off", "attributes": {}},
            }

        store = automations._automation_empty_store()
        store["settings"]["require_presence"] = False
        automations._automation_save(store)
        workflow = {
            "name": "Studio lifecycle flow",
            "objective": "Suggest workshop lighting when the configured context matches.",
            "proposal_template": "Would you like me to switch on the workshop light?",
            "execution_policy": "suggest",
            "delivery_voice": False,
            "delivery_notification_center": False,
            "delivery_ha_push": False,
            "enabled": False,
            "triggers": [{
                "kind": "entity", "entity_id": "sensor.workshop_temperature",
                "operator": "above", "value": "27", "for_seconds": 0,
            }, {
                "kind": "entity", "entity_id": "binary_sensor.workshop_occupied",
                "operator": "changes_to", "value": "on", "for_seconds": 0,
            }],
            "trigger_mode": "all",
            "conditions": [{
                "kind": "entity", "entity_id": "binary_sensor.workshop_occupied",
                "operator": "equals", "value": "on",
            }, {
                "kind": "entity", "entity_id": "climate.workshop", "attribute": "hvac_action",
                "operator": "equals", "value": "cooling", "for_seconds": 0,
            }],
            "condition_mode": "all",
            "actions": [{
                "kind": "service", "entity_id": "light.workshop",
                "service": "light.turn_on", "service_data": {},
            }],
        }
        with (
            patch.object(automations, "ensure_read_allowed"),
            patch.object(automations, "effective_entity_access", return_value="control"),
            patch.object(automations, "ha_ws", FlowHomeAssistant()),
        ):
            created = await self.client.post("/api/automations", json=workflow)
            self.assertEqual(created.status_code, 200)
            automation_id = created.json()["automation"]["id"]
            self.assertEqual(created.json()["automation"]["status"], "draft")

            persisted = json.loads(automations.AUTOMATION_STORAGE_PATH.read_text(encoding="utf-8"))
            self.assertEqual(persisted["automations"][0]["triggers"][0]["entity_id"], "sensor.workshop_temperature")
            self.assertEqual(persisted["automations"][0]["triggers"][0]["value"], "27")
            self.assertEqual(persisted["automations"][0]["triggers"][1]["entity_id"], "binary_sensor.workshop_occupied")
            self.assertEqual(persisted["automations"][0]["trigger_mode"], "all")
            self.assertEqual(persisted["automations"][0]["conditions"][0]["entity_id"], "binary_sensor.workshop_occupied")
            self.assertEqual(persisted["automations"][0]["conditions"][1]["attribute"], "hvac_action")
            self.assertEqual(persisted["automations"][0]["actions"][0]["service"], "light.turn_on")

            tested = await self.client.post("/api/automations/test-flow", json=workflow)
            self.assertEqual(tested.status_code, 200)
            self.assertEqual(len(tested.json()["trace"]), 4)
            self.assertEqual(tested.json()["actions_executed"], 0)
            self.assertIn("ALL logic", tested.json()["trace"][0]["detail"])

            activated = await self.client.post(f"/api/automations/{automation_id}/activate")
            self.assertEqual(activated.status_code, 200)
            self.assertTrue(activated.json()["automation"]["enabled"])
            self.assertEqual(activated.json()["automation"]["status"], "armed")

            reloaded = automations.automation_store()["automations"][0]
            self.assertEqual(reloaded["id"], automation_id)
            self.assertEqual(reloaded["triggers"][0]["value"], "27")
            self.assertEqual(reloaded["trigger_mode"], "all")
            await automations._automation_evaluate_state_change({
                "entity_id": "sensor.workshop_temperature", "old_state": "26", "state": "28",
            })

        evaluated = automations.automation_store()
        self.assertEqual(evaluated["automations"][0]["status"], "pending")
        self.assertEqual(len(evaluated["suggestions"]), 1)
        self.assertEqual(evaluated["suggestions"][0]["action_entity"], "light.workshop")
        self.assertEqual(evaluated["suggestions"][0]["action_service"], "light.turn_on")

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
