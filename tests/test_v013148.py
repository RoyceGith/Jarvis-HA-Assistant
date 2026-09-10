import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BROWSER = (ROOT / "jarvis" / "tests" / "browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis" / "release_manifest.json").read_text(encoding="utf-8"))


class V013148ArmBrowserHistoryTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.208")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.207")

    def test_undo_uses_a_deliberately_committed_edit(self):
        self.assertIn('fill("28")', BROWSER)
        self.assertIn('["automation-trigger-value"]==="28"', BROWSER)
        self.assertIn('inputValue(), "27"', BROWSER)
        self.assertIn('inputValue(), "28"', BROWSER)

    def test_recovery_value_is_committed_without_a_fixed_cpu_delay(self):
        recovery = BROWSER.split('inputValue(), "28"', 1)[1].split('page.reload', 1)[0]
        self.assertIn('fill("27")', recovery)
        self.assertIn('["automation-trigger-value"]==="27"', recovery)
        self.assertNotIn("waitForTimeout(260)", recovery)


if __name__ == "__main__":
    unittest.main()
