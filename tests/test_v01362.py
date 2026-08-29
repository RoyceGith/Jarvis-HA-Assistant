import json
from pathlib import Path
import tempfile
import unittest

from jarvis.app.domains import settings


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
SCHEMAS = (ROOT / "jarvis/app/schemas.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
ONBOARDING_JS = (ROOT / "jarvis/app/static/js/onboarding.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class GuidedOnboardingReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.original_path = settings.SETTINGS_STORAGE_PATH
        settings.SETTINGS_STORAGE_PATH = Path(self.temporary.name) / "settings.json"

    def tearDown(self):
        settings.SETTINGS_STORAGE_PATH = self.original_path
        self.temporary.cleanup()

    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.86"', CONFIG)
        self.assertIn('version="0.13.86"', MAIN)
        self.assertIn("HUD 0.13.86", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.86")

    def test_progress_and_optional_skip_are_persisted_non_destructively(self):
        settings.save_settings_payload({"version": 3, "preferences": {"theme": "gray"}})
        settings.save_onboarding_progress("voice", skipped_step="entities")
        state = settings.load_onboarding_state()
        self.assertEqual(state["current_step"], "voice")
        self.assertEqual(state["skipped_steps"], ["entities"])
        self.assertTrue(state["completed"])
        self.assertEqual(settings.load_settings_payload()["preferences"], {"theme": "gray"})

    def test_successful_check_removes_a_previous_skip(self):
        settings.save_onboarding_progress("entities", skipped_step="entities")
        settings.save_onboarding_check("entities", ready=True, detail="ready")
        self.assertEqual(settings.load_onboarding_state()["skipped_steps"], [])

    def test_required_steps_cannot_be_skipped(self):
        with self.assertRaises(ValueError):
            settings.save_onboarding_progress("model", skipped_step="home_assistant")

    def test_guided_api_and_controls_are_wired(self):
        self.assertIn("class OnboardingProgressUpdate", SCHEMAS)
        self.assertIn('@app.put("/api/onboarding/progress")', MAIN)
        for control in ("onboarding-previous", "onboarding-skip", "onboarding-next", "onboarding-summary"):
            self.assertIn(f'id="{control}"', HTML)
        self.assertIn("async function saveProgress", ONBOARDING_JS)
        self.assertIn("async function moveGuide", ONBOARDING_JS)
        self.assertNotIn("grinder", ONBOARDING_JS.lower())

    def test_release_history_includes_v01361(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.85")


if __name__ == "__main__":
    unittest.main()
