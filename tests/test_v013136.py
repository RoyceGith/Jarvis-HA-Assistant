import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = (ROOT / "zbrano" / "app" / "static" / "css" / "base.css").read_text(encoding="utf-8")
CORE = (ROOT / "zbrano" / "app" / "static" / "js" / "core.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano" / "release_manifest.json").read_text(encoding="utf-8"))


class V013136NeutralNeuronCoreTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.233")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.232")

    def test_every_neuron_core_is_neutral_grayscale(self):
        cores = re.findall(r"--node-core:\s*(\d+),\s*(\d+),\s*(\d+);", BASE)
        self.assertEqual(len(cores), 3)
        self.assertTrue(all(red == green == blue for red, green, blue in cores))

    def test_blue_activity_effects_remain_separate(self):
        self.assertIn('const edgeRgb = cssRgb("--node-edge")', CORE)
        self.assertIn('const linkRgb = cssRgb("--node-link")', CORE)
        self.assertIn("rgba(${edgeRgb}, ${pulseAlpha})", CORE)


if __name__ == "__main__":
    unittest.main()
