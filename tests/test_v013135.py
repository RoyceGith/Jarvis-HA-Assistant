import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE = (ROOT / "jarvis" / "app" / "static" / "js" / "core.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis" / "release_manifest.json").read_text(encoding="utf-8"))


class V013135NeuralArrivalFlashTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.136")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.135")

    def test_arrival_has_a_distinct_core_and_halo(self):
        self.assertIn("if (progress > .68)", CORE)
        self.assertIn("const flashRadius = Math.max(1.8, to.perspective * 2.8)", CORE)
        self.assertIn("rgba(255, 255, 245, ${arrival * .92})", CORE)
        self.assertIn("context.shadowBlur = 10", CORE)
        self.assertIn("flashRadius + arrivalPhase * 2.2", CORE)
        self.assertIn("context.stroke()", CORE)


if __name__ == "__main__":
    unittest.main()
