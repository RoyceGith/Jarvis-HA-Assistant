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
PUBLIC_README = (ROOT / "distribution/public-repository/README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class InstallationConfigurationGuideReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.181"', CONFIG)
        self.assertIn('version="0.13.181"', MAIN)
        self.assertIn("HUD 0.13.181", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.181")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.180")

    def test_model_help_is_an_explicit_restart_and_verify_sequence(self):
        guide = ONBOARDING[ONBOARDING.index('configurationHelp.innerHTML'):ONBOARDING.index('summary.after(configurationHelp)')]
        for marker in (
            "Settings → Apps → ZBRANO → Configuration",
            "openai_api_key",
            "restart the ZBRANO app",
            "Verify key",
            "Optional fields can stay blank",
        ):
            self.assertIn(marker, guide)
        self.assertNotIn("<input", guide)
        self.assertIn("never displays it on this page", guide)

    def test_guide_actions_are_wired_and_responsive(self):
        for marker in (
            'target === "model"',
            "configurationHelp.hidden = false",
            'copyInstallationSummary("openai_api_key"',
            "configurationVerify.addEventListener",
            "configurationClose.addEventListener",
        ):
            self.assertIn(marker, ONBOARDING)
        self.assertIn(".onboarding-configuration-help", CSS)
        self.assertIn(".onboarding-configuration-actions", CSS)
        self.assertIn("#onboarding-configuration-help:not([hidden])", BROWSER)

    def test_public_installation_instructions_match_the_guide(self):
        self.assertIn("Settings → Apps → ZBRANO → Configuration", PUBLIC_README)
        self.assertIn("`openai_api_key`", PUBLIC_README)
        self.assertIn("save, and restart ZBRANO", PUBLIC_README)
        self.assertIn("may remain blank", PUBLIC_README)


if __name__ == "__main__":
    unittest.main()
