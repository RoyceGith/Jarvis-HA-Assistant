import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE = (ROOT / "zbrano" / "app" / "static" / "js" / "core.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano" / "release_manifest.json").read_text(encoding="utf-8"))


class V013135NeuralArrivalFlashTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.228")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.227")

    def test_arrival_has_a_distinct_non_circular_spark(self):
        self.assertIn("if (progress > .68)", CORE)
        self.assertIn("const sparkExtent = Math.max(1.5, to.perspective * 2.4)", CORE)
        self.assertIn("rgba(255, 255, 245, ${arrival * .95})", CORE)
        self.assertIn("context.shadowBlur = 8", CORE)
        self.assertIn("const diagonalExtent = sparkExtent * .55", CORE)
        self.assertIn("context.stroke()", CORE)


if __name__ == "__main__":
    unittest.main()
