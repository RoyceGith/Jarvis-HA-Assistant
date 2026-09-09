import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (ROOT / "jarvis" / "app" / "static" / "js" / "automations" / "workspace.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis" / "tests" / "browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis" / "release_manifest.json").read_text(encoding="utf-8"))


class V013146AutomationSaveFeedbackTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.196")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.195")

    def test_client_validation_matches_server_minimum_lengths(self):
        self.assertIn("name.length<2", WORKSPACE)
        self.assertIn("objective.length<3", WORKSPACE)
        self.assertIn("Use at least 2 characters for the automation name", WORKSPACE)
        self.assertIn("at least 2 characters", BROWSER)

    def test_structured_server_errors_are_readable(self):
        self.assertIn("function apiErrorMessage(detail,status)", WORKSPACE)
        self.assertIn('Array.isArray(detail)', WORKSPACE)
        self.assertIn('messages.join(" · ")', WORKSPACE)
        self.assertNotIn('new Error(data.detail||`HTTP ${response.status}`)', WORKSPACE)


if __name__ == "__main__":
    unittest.main()
