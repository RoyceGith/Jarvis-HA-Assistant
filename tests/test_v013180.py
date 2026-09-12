import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
ONBOARDING = (ROOT / "zbrano/app/static/js/onboarding.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "zbrano/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class HomeAssistantSetupRecoveryReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.242"', CONFIG)
        self.assertIn('version="0.13.242"', MAIN)
        self.assertIn("HUD 0.13.242", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.242")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.241")

    def test_home_assistant_step_opens_its_own_help(self):
        self.assertIn('"target": "home_assistant"', MAIN)
        self.assertIn('home_assistant: "Connection help"', ONBOARDING)
        self.assertIn('target === "home_assistant"', ONBOARDING)
        self.assertIn("showConfigurationGuide(target)", ONBOARDING)

    def test_connection_help_uses_plain_supervisor_guidance(self):
        for marker in (
            "connects to Home Assistant automatically",
            "do not need to enter an address or access token",
            "ZBRANO Log tab",
            "The Home Assistant Supervisor supplies this connection securely",
            "Check connection again",
        ):
            self.assertIn(marker, ONBOARDING)
        self.assertIn("ZBRANO is connected to Home Assistant", MAIN)
        self.assertNotIn('detail = "Home Assistant WebSocket connected"', MAIN)

    def test_browser_covers_connection_guide(self):
        self.assertIn("/connects to Home Assistant automatically/i", BROWSER)
        self.assertIn("/do not need to enter an address or access token/i", BROWSER)
        self.assertIn("/ZBRANO Log tab/i", BROWSER)
        self.assertIn('"Check connection again"', BROWSER)


if __name__ == "__main__":
    unittest.main()
