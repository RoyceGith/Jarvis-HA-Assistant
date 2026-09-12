import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
SCHEMAS = (ROOT / "zbrano/app/schemas.py").read_text(encoding="utf-8")
AUTOMATIONS = (ROOT / "zbrano/app/domains/automations.py").read_text(encoding="utf-8")
NOTIFICATIONS = (ROOT / "zbrano/app/domains/notifications.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
INBOX = (ROOT / "zbrano/app/static/js/notifications/inbox.js").read_text(encoding="utf-8")
CENTER = (ROOT / "zbrano/app/static/js/notifications/center.js").read_text(encoding="utf-8")
STYLES = (ROOT / "zbrano/app/static/css/entity-columns.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "zbrano/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class NotificationInboxDeleteReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.235"', CONFIG)
        self.assertIn('version="0.13.235"', MAIN)
        self.assertIn("HUD 0.13.235", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.235")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.234")

    def test_each_inbox_item_has_a_persistent_delete_control(self):
        self.assertIn('remove.className = "notification-inbox-delete"', INBOX)
        self.assertIn('api("api/notifications/deliveries"', INBOX)
        self.assertIn('method:"DELETE"', INBOX)
        self.assertIn('body:JSON.stringify({ids:[item.id]})', INBOX)
        self.assertIn('notifications = notifications.filter', INBOX)

    def test_hover_behavior_and_cross_view_refresh_are_covered(self):
        self.assertIn('.notification-inbox-item:hover .notification-inbox-delete', STYLES)
        self.assertIn('@media (hover:none)', STYLES)
        self.assertIn('window.addEventListener("zbrano-notification-center-refresh", load)', CENTER)
        self.assertIn('notificationRow.locator(".notification-inbox-delete").click()', BROWSER)
        self.assertIn('/No notifications yet/i', BROWSER)

    def test_automation_suggestion_controls_use_existing_decision_apis(self):
        self.assertIn('suggestion_id: str = Field(default="", max_length=64', SCHEMAS)
        self.assertIn('delivery["suggestion_id"]', NOTIFICATIONS)
        self.assertIn('suggestion_id=suggestion["id"]', AUTOMATIONS)
        self.assertIn('notification["automation_suggestion"]', MAIN)
        self.assertIn('approve.textContent = "Approve action"', INBOX)
        self.assertIn('dismiss.textContent = "Not now"', INBOX)
        self.assertIn('never.textContent = "Never suggest"', INBOX)
        self.assertIn('api(`api/automations/suggestions/${encodeURIComponent(item.id)}/${verb}`', INBOX)
        self.assertIn('getByRole("button", {name:"Not now"}).click()', BROWSER)


if __name__ == "__main__":
    unittest.main()
