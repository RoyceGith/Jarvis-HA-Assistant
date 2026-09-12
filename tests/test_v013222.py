from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
CENTER = (ROOT / "zbrano/app/static/js/notifications/center.js").read_text(encoding="utf-8")
INBOX = (ROOT / "zbrano/app/static/js/notifications/inbox.js").read_text(encoding="utf-8")
CALENDAR = (ROOT / "zbrano/app/static/js/calendar/center.js").read_text(encoding="utf-8")
STYLE = (ROOT / "zbrano/app/static/css/workspace-modern.css").read_text(encoding="utf-8")


class HierarchicalWorkspaceNavigationTests(unittest.TestCase):
    def test_notifications_are_settings_subcategories(self):
        self.assertIn('id="notification-settings-host"', INDEX)
        self.assertEqual(INDEX.count('data-settings-target="notifications"'), 3)
        for view in ("center", "watchlist", "logs"):
            self.assertIn(f'data-notification-view="{view}"', INDEX)
        self.assertNotIn('data-auto-view="notifications"', INDEX)
        self.assertNotIn('class="notification-subtabs"', INDEX)
        self.assertIn("host.appendChild(panel)", CENTER)
        self.assertIn('document.getElementById("settings-tab")?.click()', INBOX)

    def test_other_nested_workspaces_use_side_navigation(self):
        self.assertEqual(INDEX.count("workspace-side-navigation"), 3)
        self.assertIn('class="workspace-nav-sub active"', INDEX)
        self.assertNotIn('class="birthday-toolbar"', INDEX)
        self.assertIn('showView("birthdays")', CALENDAR)
        self.assertIn(".workspace-side-navigation", STYLE)
        self.assertIn("grid-template-columns: minmax(190px, 225px)", STYLE)


if __name__ == "__main__":
    unittest.main()
