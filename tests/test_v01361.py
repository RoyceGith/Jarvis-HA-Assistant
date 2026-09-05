import json
from pathlib import Path
import tempfile
import unittest

from jarvis.app.domains import settings


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
ONBOARDING_JS = (ROOT / "jarvis/app/static/js/onboarding.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class VerifiedOnboardingReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.original_path = settings.SETTINGS_STORAGE_PATH
        settings.SETTINGS_STORAGE_PATH = Path(self.temporary.name) / "settings.json"

    def tearDown(self):
        settings.SETTINGS_STORAGE_PATH = self.original_path
        self.temporary.cleanup()

    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.155"', CONFIG)
        self.assertIn('version="0.13.155"', MAIN)
        self.assertIn("HUD 0.13.155", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.155")

    def test_check_results_are_bounded_and_persisted(self):
        settings.save_onboarding_check(
            "home_assistant", ready=True, detail="connected" * 100, checked_at=123.0
        )
        state = settings.load_onboarding_state()
        check = state["checks"]["home_assistant"]
        self.assertTrue(check["ready"])
        self.assertEqual(check["checked_at"], 123.0)
        self.assertLessEqual(len(check["detail"]), settings.ONBOARDING_CHECK_DETAIL_MAX_CHARS)

    def test_legacy_install_remains_complete_when_a_check_is_saved(self):
        settings.save_settings_payload({"version": 3, "preferences": {"theme": "gray"}})
        settings.save_onboarding_check("model", ready=False, detail="not ready")
        state = settings.load_onboarding_state()
        payload = settings.load_settings_payload()
        self.assertTrue(state["completed"])
        self.assertFalse(state["show_on_startup"])
        self.assertEqual(payload["preferences"], {"theme": "gray"})

    def test_unknown_check_is_rejected(self):
        with self.assertRaises(ValueError):
            settings.save_onboarding_check("grinder", ready=True, detail="excluded")

    def test_required_verification_gate_and_ui_are_wired(self):
        self.assertIn('"required_verified": required_verified', MAIN)
        self.assertIn('status["required_verified"]', MAIN)
        self.assertIn('id="onboarding-check-required"', HTML)
        self.assertIn("async function runRequiredChecks", ONBOARDING_JS)
        self.assertIn("step.last_check", ONBOARDING_JS)
        self.assertNotIn("grinder", ONBOARDING_JS.lower())

    def test_release_history_includes_v01360(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.154")


if __name__ == "__main__":
    unittest.main()
