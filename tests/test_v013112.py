import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "zbrano/tests/test_app_integration.py").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class BirthdayBackupBuildFixTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.220"', CONFIG)
        self.assertIn('version="0.13.220"', MAIN)
        self.assertIn("HUD 0.13.220", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.220")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.219")

    def test_container_integration_contract_includes_birthdays(self):
        self.assertIn('"automations", "notifications", "calendar", "birthdays", "contacts", "fast_memory"', INTEGRATION)
        self.assertIn('calendar._birthday_save({', INTEGRATION)
        self.assertIn('"id": "backup-birthday"', INTEGRATION)
        self.assertIn('calendar.birthday_store()["birthdays"][0]["id"]', INTEGRATION)


if __name__ == "__main__":
    unittest.main()
