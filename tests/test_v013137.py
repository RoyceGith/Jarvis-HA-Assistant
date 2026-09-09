import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE = (ROOT / "jarvis" / "app" / "static" / "js" / "core.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis" / "release_manifest.json").read_text(encoding="utf-8"))


class V013137NonCircularNeuralFlashTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.197")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.196")

    def test_arrival_uses_crossed_spark_lines_without_a_ring(self):
        arrival = CORE[CORE.index("if (progress > .68)"):CORE.index("context.shadowBlur = 0", CORE.index("if (progress > .68)"))]
        self.assertIn("context.moveTo(to.x - sparkExtent, to.y)", arrival)
        self.assertIn("context.lineTo(to.x, to.y + sparkExtent)", arrival)
        self.assertIn("const diagonalExtent = sparkExtent * .55", arrival)
        self.assertNotIn("context.arc", arrival)


if __name__ == "__main__":
    unittest.main()
