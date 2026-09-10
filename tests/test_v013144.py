import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BROWSER = (ROOT / "jarvis" / "tests" / "browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis" / "release_manifest.json").read_text(encoding="utf-8"))


class V013144ArmBrowserGateTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.204")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.203")

    def test_undo_waits_for_persisted_debounced_history(self):
        self.assertIn('localStorage.getItem("zbrano.automation-studio.unsaved.v1")', BROWSER)
        self.assertIn('saved?.state?.controls?.["automation-trigger-value"]==="27"', BROWSER)
        history_wait = BROWSER.index('saved?.state?.controls?.["automation-trigger-value"]==="27"')
        undo_click = BROWSER.index('page.locator("#automation-studio-undo").click()', history_wait)
        self.assertLess(history_wait, undo_click)


if __name__ == "__main__":
    unittest.main()
