import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "zbrano/tests/test_app_integration.py").read_text(encoding="utf-8")
DOCKERFILE = (ROOT / "zbrano/Dockerfile").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class CompleteBackupRoundTripReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.228"', CONFIG)
        self.assertIn('version="0.13.228"', MAIN)
        self.assertIn("HUD 0.13.228", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.228")

    def test_image_build_gates_complete_backup_round_trip(self):
        self.assertIn('python3 -m unittest discover -s ./tests -p "test_*.py"', DOCKERFILE)
        for marker in (
            "test_complete_backup_round_trip_preserves_all_user_data_domains",
            "fast_memory.FAST_MEMORY_PATH = temporary_root",
            'self.client.get("/api/settings/backup")',
            'self.client.post("/api/settings/restore"',
            '"automations", "notifications", "calendar", "birthdays", "contacts", "fast_memory"',
            'CHAT_SESSION_META["backup-chat"]',
            'notification_store()["deliveries"]',
            'calendar_store()["appointments"]',
            'fast_memory_search("upgrades"',
        ):
            self.assertIn(marker, INTEGRATION)

    def test_release_history_includes_v01391(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.227")


if __name__ == "__main__":
    unittest.main()
