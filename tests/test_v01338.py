import asyncio
import json
from pathlib import Path
import unittest

from jarvis.app.services import ha_history


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
SERVICE = (APP / "services/ha_history.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class HomeAssistantHistoryBoundaryTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.39"', CONFIG)
        self.assertIn('version="0.13.39"', MAIN)
        self.assertIn("HUD 0.13.39", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.39")

    def test_effective_history_implementation_is_outside_main(self):
        self.assertNotIn("def _ha_history_entities(", MAIN)
        self.assertNotIn("def _dispatch_ha_state_changed(", MAIN)
        self.assertNotIn("def get_home_assistant_history(", MAIN)
        self.assertIn("def _ha_history_entities(", SERVICE)
        self.assertIn("def dispatch_ha_state_changed(", SERVICE)
        self.assertIn("async def get_home_assistant_history(", SERVICE)
        self.assertIn("configure_ha_history_service(", MAIN)

    def test_normalization_summary_and_bounds_preserve_contract(self):
        points = ha_history._ha_history_normalize_series([
            {"state": "20", "last_changed": "2026-01-01T00:00:00+00:00"},
            {"state": "22", "last_changed": "2026-01-01T01:00:00+00:00"},
        ], "sensor.room")
        summary = ha_history._ha_history_summary("sensor.room", points, {
            "attributes": {"friendly_name": "Room", "unit_of_measurement": "°C"},
        })
        self.assertEqual(summary["friendly_name"], "Room")
        self.assertEqual(summary["trend"], "rising")
        self.assertEqual(summary["change"], 2.0)
        self.assertEqual(len(ha_history._ha_history_downsample(list(range(300)), 80)), 80)

    def test_approved_live_event_dispatches_both_automation_callbacks(self):
        calls = []

        async def record(kind, event):
            calls.append((kind, event["entity_id"]))

        async def exercise():
            ha_history.HA_LIVE_EVENTS.clear()
            ha_history.configure_ha_history_service(
                supervisor_token="token",
                ha_api_base="http://ha/api",
                ensure_read_allowed_fn=lambda entity_id: None,
                effective_entity_access_fn=lambda entity_id: "read",
                ha_get_state_fn=lambda entity_id: None,
                automation_evaluate_fn=lambda event: record("evaluate", event),
                automation_learn_fn=lambda event: record("learn", event),
            )
            ha_history.dispatch_ha_state_changed({
                "time_fired": "2026-01-01T00:00:00+00:00",
                "data": {
                    "entity_id": "sensor.room",
                    "old_state": {"state": "20", "attributes": {}},
                    "new_state": {"state": "21", "attributes": {"friendly_name": "Room"}},
                },
            })
            await asyncio.sleep(0)

        asyncio.run(exercise())
        self.assertEqual(calls, [("evaluate", "sensor.room"), ("learn", "sensor.room")])
        self.assertEqual(ha_history.HA_LIVE_EVENTS[0]["state"], "21")


if __name__ == "__main__":
    unittest.main()
