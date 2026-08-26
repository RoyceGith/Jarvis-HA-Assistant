import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "jarvis/tests/test_app_integration.py").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class IntegrationBuildRepairTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.51"', CONFIG)
        self.assertIn('version="0.13.51"', MAIN)
        self.assertIn("HUD 0.13.51", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.51")

    def test_synthetic_automation_entity_is_policy_isolated(self):
        self.assertIn(
            'with patch.object(automations, "ensure_read_allowed"):',
            INTEGRATION,
        )
        self.assertIn('"trigger_entity": "sensor.workshop_temperature"', INTEGRATION)

    def test_runtime_permission_boundary_is_unchanged(self):
        policy = (APP / "services/entity_policy.py").read_text(encoding="utf-8")
        self.assertIn("raise PermissionError", policy)
        self.assertIn("Entity is not approved for ZBRANO access", policy)


if __name__ == "__main__":
    unittest.main()
