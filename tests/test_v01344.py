import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "jarvis/tests/test_app_integration.py").read_text(encoding="utf-8")
TESTING = (ROOT / "docs/TESTING.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class DomainIntegrationExpansionTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.52"', CONFIG)
        self.assertIn('version="0.13.52"', MAIN)
        self.assertIn("HUD 0.13.52", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.52")

    def test_three_domain_lifecycles_use_real_asgi_routes(self):
        for marker in (
            '"/api/automations",',
            'self.client.get("/api/automations")',
            'self.client.delete(f"/api/automations/{automation_id}")',
            '"/api/calendar",',
            'self.client.get("/api/calendar")',
            'self.client.delete(f"/api/calendar/{appointment_id}")',
            '"/api/notifications/settings",',
            '"/api/notifications/watches",',
            'self.client.get("/api/notifications")',
            'self.client.delete(f"/api/notifications/watches/{watch_id}")',
        ):
            self.assertIn(marker, INTEGRATION)

    def test_persistence_and_home_assistant_boundaries_are_isolated(self):
        for marker in (
            "automations.AUTOMATION_STORAGE_PATH = temporary_root",
            "calendar.CALENDAR_STORAGE_PATH = temporary_root",
            "notifications.NOTIFICATION_STORAGE_PATH = temporary_root",
            'patch.object(notifications, "ha_ws", FakeHomeAssistant())',
            'patch.object(notifications, "notification_channels", AsyncMock',
            'patch.object(main, "_automation_refresh_area_context", AsyncMock',
        ):
            self.assertIn(marker, INTEGRATION)
        self.assertIn("Automation Brain draft creation", TESTING)
        self.assertIn("Calendar appointment creation", TESTING)
        self.assertIn("Notification settings and watch lifecycle", TESTING)


if __name__ == "__main__":
    unittest.main()
