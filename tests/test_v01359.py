import json
from pathlib import Path
import tempfile
import unittest

from zbrano.app.domains import settings


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
ONBOARDING_JS = (ROOT / "zbrano/app/static/js/onboarding.js").read_text(encoding="utf-8")
BOUNDARY = (ROOT / "docs/REPOSITORY_BOUNDARIES.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class OnboardingFoundationReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.original_path = settings.SETTINGS_STORAGE_PATH
        settings.SETTINGS_STORAGE_PATH = Path(self.temporary.name) / "settings.json"

    def tearDown(self):
        settings.SETTINGS_STORAGE_PATH = self.original_path
        self.temporary.cleanup()

    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.232"', CONFIG)
        self.assertIn('version="0.13.232"', MAIN)
        self.assertIn("HUD 0.13.232", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.232")

    def test_new_installation_opens_setup_without_writing(self):
        state = settings.load_onboarding_state()
        self.assertTrue(state["show_on_startup"])
        self.assertFalse(settings.SETTINGS_STORAGE_PATH.exists())

    def test_existing_installation_is_preserved_and_not_interrupted(self):
        settings.save_settings_payload({"version": 3, "preferences": {"theme": "gray"}})
        state = settings.load_onboarding_state()
        self.assertTrue(state["legacy_installation"])
        self.assertTrue(state["completed"])
        self.assertFalse(state["show_on_startup"])
        settings.save_onboarding_state(completed=False, dismissed=True)
        payload = settings.load_settings_payload()
        self.assertEqual(payload["preferences"], {"theme": "gray"})
        self.assertTrue(payload["onboarding"]["dismissed"])

    def test_setup_ui_and_api_are_wired(self):
        self.assertIn('data-settings-target="setup"', HTML)
        self.assertIn('src="js/onboarding.js"', HTML)
        self.assertIn('@app.get("/api/onboarding")', MAIN)
        self.assertIn('@app.put("/api/onboarding")', MAIN)
        self.assertIn('load({openIfNeeded: true})', ONBOARDING_JS)

    def test_owner_only_grinder_is_excluded_from_onboarding(self):
        self.assertNotIn("grinder", ONBOARDING_JS.lower())
        self.assertIn("owner-specific private extension", BOUNDARY)

    def test_release_history_includes_v01358(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.231")


if __name__ == "__main__":
    unittest.main()
