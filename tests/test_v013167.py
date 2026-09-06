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


class OnboardingCompletionReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.177"', CONFIG)
        self.assertIn('version="0.13.177"', MAIN)
        self.assertIn("HUD 0.13.177", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.177")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.176")

    def test_completed_setup_has_a_clear_handoff(self):
        self.assertIn("function renderCompletion(data, steps)", ONBOARDING)
        self.assertIn('title.textContent = "ZBRANO is ready"', ONBOARDING)
        self.assertIn('start.textContent = "Start chatting"', ONBOARDING)
        self.assertIn('review.textContent = "Review connections"', ONBOARDING)
        self.assertIn('document.getElementById("chat-tab")?.click()', ONBOARDING)

    def test_completion_distinguishes_ready_and_later_capabilities(self):
        self.assertIn('const ready = steps.filter(step => step.ready)', ONBOARDING)
        self.assertIn('const later = steps.filter(step => !step.ready)', ONBOARDING)
        self.assertIn('${step.title} ready', ONBOARDING)
        self.assertIn('${step.title} available later', ONBOARDING)
        self.assertIn(".onboarding-capability-list span.is-ready", CSS)

    def test_browser_exercises_completion_and_review(self):
        self.assertIn("await page.locator('.onboarding-complete-card').waitFor()", BROWSER)
        self.assertIn("getByRole('button', {name:'Review connections'})", BROWSER)

    def test_owner_extension_is_absent_from_onboarding(self):
        self.assertNotIn("grinder", ONBOARDING.lower())


if __name__ == "__main__":
    unittest.main()
