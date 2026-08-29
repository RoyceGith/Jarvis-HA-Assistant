import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "jarvis/tests/test_app_integration.py").read_text(encoding="utf-8")
DOCKERFILE = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class AutomationUpgradeCompatibilityReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.96"', CONFIG)
        self.assertIn('version="0.13.96"', MAIN)
        self.assertIn("HUD 0.13.96", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.96")

    def test_image_build_gates_pre_studio_automation_upgrade(self):
        self.assertIn('python3 -m unittest discover -s ./tests -p "test_*.py"', DOCKERFILE)
        for marker in (
            "test_pre_studio_automation_restores_and_upgrades_without_behavior_loss",
            '"id": "legacy-temperature-rule"',
            '"trigger_operator": "above"',
            '"trigger_value": "25"',
            'current["created_at"]',
            'current["triggers"][0]["entity_id"]',
            'current["conditions"], []',
            'current["actions"], []',
            'current["branches"], []',
        ):
            self.assertIn(marker, INTEGRATION)

    def test_release_history_includes_v01390(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.95")


if __name__ == "__main__":
    unittest.main()
