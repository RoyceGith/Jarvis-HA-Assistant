from pathlib import Path
import gc
import json
import tempfile
import unittest
import warnings

from jarvis.app.domains import fast_memory


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))
WORKSHOP_MEMORY = (ROOT / "jarvis/app/domains/workshop_memory.py").read_text(encoding="utf-8")


class MemoryDomainBoundaryTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.35"', CONFIG)
        self.assertIn('version="0.13.35"', MAIN)
        self.assertIn("HUD 0.13.35", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.35")

    def test_memory_engines_are_outside_composition_root(self):
        self.assertNotIn("def _fast_memory_connect(", MAIN)
        self.assertNotIn("async def _call_workshop_memory_endpoint(", MAIN)
        self.assertIn("configure_fast_memory_domain(", MAIN)
        self.assertIn("configure_workshop_memory_domain(", MAIN)

    def test_fast_memory_preserves_sqlite_contract(self):
        original_path = fast_memory.FAST_MEMORY_PATH
        with tempfile.TemporaryDirectory() as directory:
            fast_memory.FAST_MEMORY_PATH = Path(directory) / "zbrano_fast_memory.sqlite3"
            try:
                saved = fast_memory.upsert_fast_memory({
                    "kind": "preference",
                    "subject": "Royce",
                    "key": "test_preference",
                    "value": "Keep the existing storage contract",
                })
                found = fast_memory.fast_memory_search("storage contract")
                self.assertTrue(saved["saved"])
                self.assertEqual(found["count"], 1)
                self.assertEqual(found["memories"][0]["key"], "test_preference")
            finally:
                fast_memory.FAST_MEMORY_PATH = original_path
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", ResourceWarning)
                    gc.collect()

    def test_workshop_memory_owns_transport_and_bounded_runtime_state(self):
        self.assertIn("async def _call_workshop_memory_endpoint(", WORKSHOP_MEMORY)
        self.assertIn("async def select_workshop_memory_endpoint(", WORKSHOP_MEMORY)
        self.assertIn("def workshop_memory_runtime_status(", WORKSHOP_MEMORY)
        self.assertIn('"cache_entries": len(MCP_TOOL_CACHE)', WORKSHOP_MEMORY)
        self.assertIn('"http_pool_open": bool(MCP_CLIENT and not MCP_CLIENT.is_closed)', WORKSHOP_MEMORY)


if __name__ == "__main__":
    unittest.main()
