import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE = (ROOT / "jarvis" / "app" / "static" / "js" / "core.js").read_text(encoding="utf-8")
BASE = (ROOT / "jarvis" / "app" / "static" / "css" / "base.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis" / "release_manifest.json").read_text(encoding="utf-8"))


class V013134VisibleNeuralSignalTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.149")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.148")

    def test_signals_render_over_nodes_with_visible_bounded_energy(self):
        node_render = CORE.index("for (const [pointIndex, point] of depthSorted.entries())")
        signal_render = CORE.index("for (const signal of neuralSignals)", node_render)
        self.assertLess(node_render, signal_render)
        self.assertIn('context.globalCompositeOperation = "screen"', CORE)
        self.assertIn("* .68", CORE)
        self.assertIn("context.arc(signalX, signalY, 1.05", CORE)
        self.assertIn(".slice(0, 12)", CORE)
        self.assertIn("cycle: 4100 + index * 310", CORE)

    def test_node_centers_are_less_blue(self):
        self.assertIn("--node-core: 9, 9, 9;", BASE)
        self.assertIn("--node-core: 20, 20, 20;", BASE)


if __name__ == "__main__":
    unittest.main()
