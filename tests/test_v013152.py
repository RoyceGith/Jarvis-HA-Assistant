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
        self.assertEqual(MANIFEST["version"], "0.13.200")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.199")

    def test_response_wording_is_attached_to_executable_paths(self):
        self.assertNotIn("How should ZBRANO respond?", HTML)
        for label in ("Ask before running", "Run automatically"):
            self.assertIn(label, WORKSPACE + BROWSER)
        self.assertNotIn("Suggest it to me", HTML)
        self.assertNotIn("Ask before doing it", HTML)

    def test_choices_adapt_to_device_type(self):
        self.assertIn("function normalizeExecutionPolicyForDevice()", WORKSPACE)
        self.assertIn('["approval_required","autonomous"]', WORKSPACE)
        self.assertIn('["suggest","observe"]', WORKSPACE)
        self.assertIn("if(!allowedPolicies.includes(option.value))option.remove()", WORKSPACE)

    def test_browser_verifies_independent_branch_choices(self):
        self.assertIn('data-branch-policy][data-branch-index="1"', BROWSER)
        self.assertIn('selectOption("autonomous")', BROWSER)
        self.assertIn('data-branch-policy][data-branch-index="0"', BROWSER)


if __name__ == "__main__":
    unittest.main()
