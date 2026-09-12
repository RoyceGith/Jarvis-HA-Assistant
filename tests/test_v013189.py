import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
HA_CONTROL = (ROOT / "zbrano/app/services/ha_control.py").read_text(encoding="utf-8")
HTML = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
CHANGELOG = (ROOT / "distribution/public-repository/zbrano/CHANGELOG.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class FastHomeAssistantControlReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.235"', CONFIG)
        self.assertIn('version="0.13.235"', MAIN)
        self.assertIn("HUD 0.13.235", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.235")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.234")
        self.assertTrue(CHANGELOG.startswith("# Change log\n\n## 0.13.235"))

    def test_local_control_runs_before_workshop_tool_preparation(self):
        normal = MAIN[MAIN.index("async def run_zbrano("):MAIN.index("async def _run_zbrano_stream_events(")]
        stream = MAIN[MAIN.index("async def _run_zbrano_stream_events("):MAIN.index("async def run_zbrano_stream(")]
        for route in (normal, stream):
            self.assertLess(route.index("try_local_ha_route("), route.index("refresh_workshop_memory_tools()"))

    def test_control_intents_consider_only_control_devices(self):
        route = MAIN[MAIN.index("async def try_local_ha_route("):MAIN.index("async def run_zbrano(")]
        self.assertIn('candidate.get("control_approved") is True', route)
        self.assertIn("control_matches", route)
        self.assertIn("approved Control Device", route)
        self.assertIn("Which one?", route)

    def test_successful_websocket_action_is_verified_without_replay(self):
        self.assertIn("timeout=1.0", HA_CONTROL)
        self.assertIn("verified_raw = await ha_get_state_rest(entity_id)", HA_CONTROL)
        self.assertIn('transport = "websocket"', HA_CONTROL)
        self.assertIn('"transport": transport', HA_CONTROL)
        self.assertIn("Controlling Home Assistant", MAIN)


if __name__ == "__main__":
    unittest.main()
