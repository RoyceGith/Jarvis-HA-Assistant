from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
GRINDER = (APP / "domains/grinder.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class GrinderDomainBoundaryTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.28"', CONFIG)
        self.assertIn('version="0.13.28"', MAIN)
        self.assertIn("HUD 0.13.28", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.28")

    def test_grinder_engine_is_outside_composition_root(self):
        self.assertNotIn("async def grinder_monitor_worker(", MAIN)
        self.assertNotIn("def _ingest_grinder_message(", MAIN)
        self.assertIn("async def grinder_monitor_worker(", GRINDER)
        self.assertIn("def _ingest_grinder_message(", GRINDER)
        self.assertIn('GRINDER_INCIDENTS_PATH = DATA_DIR / "grinder_incidents.json"', GRINDER)

    def test_grinder_lifecycle_is_explicitly_delegated(self):
        import_block = MAIN.split("from .domains.grinder import (", 1)[1].split(")", 1)[0]
        self.assertIn("start_grinder_monitor,", import_block)
        self.assertIn("stop_grinder_monitor,", import_block)
        self.assertIn("start_grinder_monitor()", MAIN)
        self.assertIn("await stop_grinder_monitor()", MAIN)
        self.assertNotIn("global GRINDER_MONITOR_TASK", MAIN)

    def test_monitor_remains_read_only(self):
        self.assertIn('"read_only": True', GRINDER)
        self.assertIn("await client.subscribe(", GRINDER)
        self.assertNotIn("client.publish(", GRINDER)


if __name__ == "__main__":
    unittest.main()
