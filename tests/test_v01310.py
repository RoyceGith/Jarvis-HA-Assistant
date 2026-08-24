from pathlib import Path
import json
import unittest
from tests.frontend_source import load_frontend_source
from tests.backend_source import load_backend_source


ROOT = Path(__file__).resolve().parents[1]
INDEX = load_frontend_source()
MAIN = load_backend_source()
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class PassiveAutomationBrainTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.17"', CONFIG)
        self.assertIn('version="0.13.17"', MAIN)
        self.assertIn("HUD 0.13.17", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.17")

    def test_home_assistant_areas_and_device_inheritance_are_imported(self):
        self.assertIn('"type": "config/area_registry/list"', MAIN)
        self.assertIn('"type": "config/device_registry/list"', MAIN)
        self.assertIn('"type": "config/entity_registry/list"', MAIN)
        self.assertIn('"area_source": "entity" if direct_area else "device"', MAIN)

    def test_learning_state_is_persistent_and_bounded(self):
        for marker in ('"area_context"', '"observations"', '"patterns"', '"discoveries"'):
            self.assertIn(marker, MAIN)
        self.assertIn('data["observations"] = list(data.get("observations") or [])[:1500]', MAIN)
        self.assertIn('data["discoveries"] = list(data.get("discoveries") or [])[:100]', MAIN)
        self.assertIn('id="autonomy-passive-learning"', INDEX)

    def test_room_lighting_discovery_uses_context_and_sustained_presence(self):
        self.assertIn("AUTOMATION_ROOM_OCCUPANCY_SECONDS = 120", MAIN)
        self.assertIn("def _automation_dark_context", MAIN)
        self.assertIn('sun_state == "below_horizon"', MAIN)
        self.assertIn("async def _automation_discover_area", MAIN)
        self.assertIn('"source": "automation_brain"', MAIN)

    def test_discovered_actions_stay_explicitly_permission_gated(self):
        approval = MAIN[MAIN.index('async def approve_automation_suggestion') : MAIN.index('async def dismiss_automation_suggestion')]
        self.assertIn("ensure_control_allowed(entity_id)", approval)
        self.assertIn('suggestion.get("source") == "automation_brain"', approval)
        self.assertIn('"status": "approval_required"', MAIN)
        self.assertIn("domain not in {\"light\", \"switch\", \"fan\", \"input_boolean\"}", approval)

    def test_feedback_and_room_context_are_visible(self):
        self.assertIn('id="automation-brain-list"', INDEX)
        self.assertIn("function renderAutomationBrain()", INDEX)
        self.assertIn('data-discovery-feedback="never_suggest"', INDEX)
        self.assertIn('@app.post("/api/automations/discoveries/{discovery_id}/feedback")', MAIN)
        self.assertIn('areaCell.textContent = entity.area_name || "Unassigned"', INDEX)
        self.assertIn("def automation_brain_memory_context", MAIN)
        self.assertIn('"learned_patterns": patterns', MAIN)


if __name__ == "__main__":
    unittest.main()
