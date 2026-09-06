import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
ONBOARDING = (ROOT / "jarvis/app/static/js/onboarding.js").read_text(encoding="utf-8")
CSS = (ROOT / "jarvis/app/static/css/onboarding.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class FocusedOnboardingReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.168"', CONFIG)
        self.assertIn('version="0.13.168"', MAIN)
        self.assertIn("HUD 0.13.168", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.168")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.167")

    def test_setup_is_one_focused_step_with_a_compact_rail(self):
        self.assertIn('rail.className = "onboarding-step-rail"', ONBOARDING)
        self.assertIn('.onboarding-step:not(.is-active) { display: none; }', CSS)
        self.assertIn('grid-template-columns: repeat(7, minmax(0, 1fr))', CSS)
        for step_id in ("home_assistant", "model", "entities", "voice", "memory", "plugins", "notifications"):
            self.assertIn(f"{step_id}:", ONBOARDING)

    def test_required_steps_gate_future_navigation_using_live_and_verified_state(self):
        gate = 'step.required && !(step.ready && step.last_check?.ready)'
        self.assertGreaterEqual(ONBOARDING.count(gate), 2)
        self.assertIn('railStep.disabled = blockedIndex >= 0 && index > blockedIndex', ONBOARDING)
        self.assertIn('Boolean(activeStep.ready) && Boolean(activeStep.last_check?.ready)', ONBOARDING)

    def test_browser_exercises_the_guided_setup(self):
        self.assertIn("onboardingFixture", BROWSER)
        self.assertIn("await page.locator('.onboarding-step.is-active').waitFor()", BROWSER)
        self.assertIn("await page.locator('.onboarding-step:visible').count()", BROWSER)
        self.assertIn('"Refresh status"', BROWSER)

    def test_owner_extension_is_absent_from_onboarding(self):
        self.assertNotIn("grinder", ONBOARDING.lower())


if __name__ == "__main__":
    unittest.main()
