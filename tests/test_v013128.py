import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class ArmBrowserGateReleaseTests(unittest.TestCase):
    def test_branch_condition_delete_bypasses_card_interception(self):
        line = next(value for value in BROWSER.splitlines() if "const removableBranchCondition=" in value)
        self.assertIn('.automation-flow-card-delete").click({force:true})', line)

    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.134")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.133")


if __name__ == "__main__":
    unittest.main()
