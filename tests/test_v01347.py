import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
GUARD = (ROOT / "jarvis/app/services/workshop_cost_guard.py").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class WorkshopCostSafetyReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.49"', CONFIG)
        self.assertIn('version="0.13.49"', MAIN)
        self.assertIn("HUD 0.13.49", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.49")

    def test_runtime_enforces_workshop_cost_controls(self):
        for marker in (
            "parallel_tool_calls",
            "MAX_MODEL_RESPONSES = 6",
            "MAX_TOOL_CALLS = 8",
            "MAX_CALLS_PER_RESPONSE = 3",
            "MAX_SINGLE_TOOL_OUTPUT_CHARS = 32_000",
            "MAX_TOTAL_TOOL_OUTPUT_CHARS = 64_000",
            "MAX_INPUT_TOKENS = 80_000",
            "MAX_CACHE_WRITE_TOKENS = 40_000",
        ):
            self.assertIn(marker, GUARD)
        self.assertIn("workshop_memory_cost_guard", MAIN)
        self.assertIn("request_message=request_message", MAIN)
        self.assertIn("cost_budget=workshop_budget", MAIN)

    def test_release_history_includes_previous_release(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.48")


if __name__ == "__main__":
    unittest.main()
