import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "jarvis/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class AdaptiveAutomationResponseReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.161")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.160")

    def test_plain_response_wording_replaces_overlapping_labels(self):
        self.assertIn("How should ZBRANO respond?", HTML)
        for label in ("Monitor silently", "Notify me", "Ask me first", "Do it automatically"):
            self.assertIn(label, HTML)
        self.assertNotIn("Suggest it to me", HTML)
        self.assertNotIn("Ask before doing it", HTML)

    def test_choices_adapt_to_device_type(self):
        self.assertIn("function normalizeExecutionPolicyForDevice()", WORKSPACE)
        self.assertIn('["approval_required","autonomous"]', WORKSPACE)
        self.assertIn('["suggest","observe"]', WORKSPACE)
        self.assertIn("if(!allowedPolicies.includes(option.value))option.remove()", WORKSPACE)

    def test_browser_verifies_both_two_choice_menus(self):
        self.assertIn('["Monitor silently", "Notify me"]', BROWSER)
        self.assertIn('["Ask me first", "Do it automatically"]', BROWSER)
        self.assertIn('#studio-automation-risk").selectOption("informational")', BROWSER)


if __name__ == "__main__":
    unittest.main()
