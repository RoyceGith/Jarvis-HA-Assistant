import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class ArmBrowserGateReleaseTests(unittest.TestCase):
    def test_existing_linear_task_is_connected_when_branching_starts(self):
        self.assertIn('data-flow-kind="action"]\').count(), 0', BROWSER)
        self.assertIn('data-flow-branch-drop="0"', BROWSER)
        self.assertIn("Wait 2 sec", BROWSER)

    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.205")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.204")


if __name__ == "__main__":
    unittest.main()
