import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "jarvis/tests/test_app_integration.py").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class BirthdayBackupBuildFixTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.156"', CONFIG)
        self.assertIn('version="0.13.156"', MAIN)
        self.assertIn("HUD 0.13.156", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.156")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.155")

    def test_container_integration_contract_includes_birthdays(self):
        self.assertIn('"automations", "notifications", "calendar", "birthdays", "contacts", "fast_memory"', INTEGRATION)
        self.assertIn('calendar._birthday_save({', INTEGRATION)
        self.assertIn('"id": "backup-birthday"', INTEGRATION)
        self.assertIn('calendar.birthday_store()["birthdays"][0]["id"]', INTEGRATION)


if __name__ == "__main__":
    unittest.main()
