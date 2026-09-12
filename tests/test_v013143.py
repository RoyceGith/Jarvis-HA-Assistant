import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "zbrano" / "app" / "static" / "index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "zbrano" / "app" / "static" / "js" / "automations" / "workspace.js").read_text(encoding="utf-8")
FLOW = (ROOT / "zbrano" / "app" / "static" / "js" / "automations" / "flow.js").read_text(encoding="utf-8")
CSS = (ROOT / "zbrano" / "app" / "static" / "css" / "automation-studio.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano" / "release_manifest.json").read_text(encoding="utf-8"))


class V013143AutomationStudioTaskFirstTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.224")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.223")

    def test_new_then_step_hides_blank_legacy_action_fields(self):
        self.assertIn('selectedStudioNode==="action"', WORKSPACE)
        self.assertIn('!["automation-action-entity","automation-action-service","automation-action-data"].includes(id)', WORKSPACE)
        self.assertIn("Choose a task above. Nothing will be controlled unless you add one.", WORKSPACE)

    def test_common_actions_are_primary_and_custom_action_is_advanced(self):
        for phrase in ("What should happen?", "Choose a task. You can add more than one.", "Advanced: custom Home Assistant action"):
            self.assertIn(phrase, WORKSPACE)
        self.assertIn("automation-task-custom", CSS)
        self.assertIn('data-action-template="service"', WORKSPACE)

    def test_raw_commands_are_translated_on_common_surfaces(self):
        for phrase in ("Set heating or cooling mode", "Activate scene", "Start cleaning", "Change power"):
            self.assertIn(phrase, WORKSPACE)
            self.assertIn(phrase, FLOW)
        self.assertIn("actionLabel(item.action_service)", WORKSPACE)
        self.assertNotIn("Service: climate.set_temperature", WORKSPACE)

    def test_full_advanced_fields_remain_available(self):
        for label in ("Advanced action device", "Advanced action command", "Advanced action details (JSON)"):
            self.assertIn(label, HTML)


if __name__ == "__main__":
    unittest.main()
