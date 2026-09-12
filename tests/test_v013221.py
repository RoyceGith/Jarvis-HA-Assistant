import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "zbrano" / "app"
INDEX = (APP / "static" / "index.html").read_text(encoding="utf-8")
NOTIFICATIONS = (APP / "domains" / "notifications.py").read_text(encoding="utf-8")
TELEGRAM = (APP / "static" / "js" / "integrations" / "telegram.js").read_text(encoding="utf-8")
STYLE = (APP / "static" / "css" / "notification-center.css").read_text(encoding="utf-8")
CATALOG = (APP / "static" / "js" / "i18n" / "catalog-advanced.js").read_text(encoding="utf-8")
CONFIG = (ROOT / "zbrano" / "config.yaml").read_text(encoding="utf-8")
MAIN = (APP / "main.py").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano" / "release_manifest.json").read_text(encoding="utf-8"))


class NotificationReadinessAndTelegramSetupTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.238"', CONFIG)
        self.assertIn('version="0.13.238"', MAIN)
        self.assertIn("HUD 0.13.238", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.238")

    def test_unknown_notify_state_is_not_treated_as_unavailable(self):
        self.assertIn('explicitly_unavailable = str(state or "").strip().lower() == "unavailable"', NOTIFICATIONS)
        self.assertIn('"available": not explicitly_unavailable', NOTIFICATIONS)
        self.assertIn('"Ready · status not reported"', NOTIFICATIONS)
        self.assertIn('row.dataset.availability = channel.available === false ? "unavailable" : "ready"', (APP / "static" / "js" / "notifications" / "center.js").read_text(encoding="utf-8"))

    def test_telegram_setup_is_guided_without_collecting_the_token(self):
        setup_source = INDEX + TELEGRAM
        for marker in (
            'id="telegram-setup-guide"',
            'href="https://t.me/BotFather"',
            'domain=telegram_bot',
            'href="https://t.me/id_bot"',
            'data-telegram-refresh',
            "ZBRANO never asks for it or stores it.",
        ):
            self.assertIn(marker, setup_source)
        self.assertNotIn('type="password"', TELEGRAM)
        self.assertIn("telegramChannels.length", TELEGRAM)
        self.assertIn(".telegram-setup-steps", STYLE)

    def test_new_setup_copy_is_available_in_every_interface_language(self):
        for phrase in (
            "Set up a Telegram bot",
            "Create your bot",
            "Connect it to Home Assistant",
            "Allow your Telegram chat",
            "Pair it with ZBRANO",
            "Ready · status not reported",
        ):
            self.assertIn(f'"{phrase}":', CATALOG)


if __name__ == "__main__":
    unittest.main()
