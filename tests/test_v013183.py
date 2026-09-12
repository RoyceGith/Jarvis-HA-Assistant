import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
PUBLIC = (ROOT / "distribution/public-repository/README.md").read_text(encoding="utf-8")
APP_GUIDE = (ROOT / "distribution/public-repository/zbrano/README.md").read_text(encoding="utf-8")
CHANGELOG = (ROOT / "distribution/public-repository/zbrano/CHANGELOG.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class PublicProductGuideReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.241"', CONFIG)
        self.assertIn('version="0.13.241"', MAIN)
        self.assertIn("HUD 0.13.241", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.241")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.240")
        self.assertTrue(CHANGELOG.startswith("# Change log\n\n## 0.13.241"))

    def test_public_landing_page_is_a_concise_product_guide(self):
        self.assertLess(len(PUBLIC.splitlines()), 130)
        for marker in (
            "What ZBRANO brings together",
            "From installation to useful action",
            "Installation",
            "Permission model",
            "Data and connected services",
            "Updates and existing installations",
            "Support and troubleshooting",
        ):
            self.assertIn(f"## {marker}", PUBLIC)
        self.assertIn("Conversation and voice", PUBLIC)
        self.assertIn("Visual automations", PUBLIC)
        self.assertIn("Safety and ownership", PUBLIC)
        self.assertNotIn("Version 0.13.181 gives", PUBLIC)

    def test_app_guide_explains_setup_safety_and_privacy(self):
        self.assertLess(len(APP_GUIDE.splitlines()), 110)
        for marker in (
            "Before installation",
            "First setup",
            "Device access",
            "Automation safety",
            "Privacy and recovery",
            "Need help?",
        ):
            self.assertIn(f"## {marker}", APP_GUIDE)
        for choice in ("Sensor device", "Control device", "Do not allow"):
            self.assertIn(choice, APP_GUIDE)
        self.assertIn("Try it safely", APP_GUIDE)

    def test_store_description_represents_the_complete_product(self):
        description = next(line for line in CONFIG.splitlines() if line.startswith("description:"))
        self.assertIn("conversation", description.lower())
        self.assertIn("visual automation", description.lower())
        self.assertIn("explicit device permissions", description.lower())
        self.assertNotIn("Workshop Memory", description)


if __name__ == "__main__":
    unittest.main()
