import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class ArmBrowserBuildStabilityReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.135"', CONFIG)
        self.assertIn('version="0.13.135"', MAIN)
        self.assertIn("HUD 0.13.135", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.135")

    def test_browser_waits_for_async_automation_summary(self):
        self.assertIn('[aria-label="View 1 automation draft"]\').waitFor()', BROWSER)
        wait_index = BROWSER.index('[aria-label="View 1 automation draft"]\').waitFor()')
        assertion_index = BROWSER.index('getAttribute("aria-label"), "View 1 automation draft"')
        self.assertLess(wait_index, assertion_index)

    def test_release_history_includes_v01396(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.134")


if __name__ == "__main__":
    unittest.main()
