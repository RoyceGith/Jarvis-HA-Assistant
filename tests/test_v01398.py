import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "jarvis/tests/test_app_integration.py").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class AutomationStudioLifecycleGateReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.103"', CONFIG)
        self.assertIn('version="0.13.103"', MAIN)
        self.assertIn("HUD 0.13.103", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.103")

    def test_build_gate_covers_complete_studio_workflow_lifecycle(self):
        self.assertIn("test_studio_workflow_persists_activates_and_evaluates_end_to_end", INTEGRATION)
        for marker in (
            'self.client.post("/api/automations", json=workflow)',
            'self.client.post("/api/automations/test-flow", json=workflow)',
            'self.client.post(f"/api/automations/{automation_id}/activate")',
            "await automations._automation_evaluate_state_change",
            'evaluated["suggestions"][0]["action_service"]',
        ):
            self.assertIn(marker, INTEGRATION)

    def test_release_history_includes_v01397(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.102")


if __name__ == "__main__":
    unittest.main()
