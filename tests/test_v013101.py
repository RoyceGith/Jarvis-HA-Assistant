import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
SCHEMAS = (ROOT / "zbrano/app/schemas.py").read_text(encoding="utf-8")
AUTOMATIONS = (ROOT / "zbrano/app/domains/automations.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "zbrano/app/static/js/automations/workspace.js").read_text(encoding="utf-8")
FLOW = (ROOT / "zbrano/app/static/js/automations/flow.js").read_text(encoding="utf-8")
CSS = (ROOT / "zbrano/app/static/css/automation-studio.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "zbrano/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class AutomationTaskPaletteReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.244"', CONFIG)
        self.assertIn('version="0.13.244"', MAIN)
        self.assertIn("HUD 0.13.244", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.244")

    def test_action_palette_exposes_executable_presets(self):
        for marker in ('["turn_on","Power on"', '["turn_off","Power off"',
                       '["toggle","Toggle"', '["notification","Notification"',
                       '["delay","Delay"', '["wait","Wait until"',
                       '["service","Custom service"'):
            self.assertIn(marker, WORKSPACE)
        self.assertIn("automation-task-palette-grid", CSS)
        self.assertIn("workflowDraft.actions.push(newActionTask", WORKSPACE)

    def test_notification_is_a_first_class_automation_action(self):
        self.assertIn("service|notification|delay|wait_state", SCHEMAS)
        self.assertIn('if kind == "notification":', AUTOMATIONS)
        self.assertIn("await test_notification_channel(NotificationTestRequest(", AUTOMATIONS)
        self.assertIn('kind==="notification"', FLOW)
        self.assertIn('notification_message', WORKSPACE)
        self.assertIn('legacyPrimary=actions[0]&&(actions[0].kind||"service")==="service"', WORKSPACE)
        self.assertIn('== "notification" for step in actions', AUTOMATIONS)

    def test_browser_covers_device_and_notification_presets(self):
        self.assertIn('data-action-template="turn_on"', BROWSER)
        self.assertIn('data-action-template="notification"', BROWSER)
        self.assertIn('notify.browser_phone', BROWSER)
        self.assertIn('Automation finished', BROWSER)

    def test_release_history_includes_v013100(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.243")


if __name__ == "__main__":
    unittest.main()
