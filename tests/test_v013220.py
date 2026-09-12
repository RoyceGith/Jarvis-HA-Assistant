import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "zbrano" / "app" / "static" / "index.html").read_text(encoding="utf-8")
STYLE = (ROOT / "zbrano" / "app" / "static" / "css" / "notification-center.css").read_text(encoding="utf-8")
CONFIG = (ROOT / "zbrano" / "config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano" / "app" / "main.py").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano" / "release_manifest.json").read_text(encoding="utf-8"))


class NotificationWorkspaceLayoutTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.222"', CONFIG)
        self.assertIn('version="0.13.222"', MAIN)
        self.assertIn("HUD 0.13.222", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.222")

    def test_notifications_have_a_dedicated_scoped_workspace(self):
        self.assertIn('href="css/notification-center.css"', INDEX)
        self.assertIn('class="notification-workspace-head"', INDEX)
        self.assertIn('class="notification-workspace-panel" data-notification-panel="center"', INDEX)
        self.assertIn('[data-notification-workspace]', STYLE)
        self.assertIn("grid-template-columns: repeat(12, minmax(0, 1fr))", STYLE)

    def test_forms_actions_and_dynamic_lists_are_contained(self):
        self.assertIn('#settings-panel [data-notification-workspace] .notification-form-grid', STYLE)
        self.assertIn('.notification-form-grid > .check', STYLE)
        self.assertIn('.notification-log-toolbar', STYLE)
        self.assertIn('@media (max-width: 700px)', STYLE)
        self.assertIn("overflow-wrap: anywhere", STYLE)

    def test_refresh_control_is_unique_and_all_sections_remain_available(self):
        self.assertEqual(INDEX.count('id="notification-refresh"'), 1)
        for marker in (
            'id="notification-settings-form"',
            'id="notification-channels"',
            'id="notification-test-form"',
            'id="telegram-inbound-form"',
            'data-notification-panel="watchlist"',
            'data-notification-panel="logs"',
        ):
            self.assertIn(marker, INDEX)


if __name__ == "__main__":
    unittest.main()
