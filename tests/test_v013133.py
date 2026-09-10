import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE = (ROOT / "jarvis" / "app" / "static" / "js" / "core.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis" / "release_manifest.json").read_text(encoding="utf-8"))


class V013133NeuralSignalTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.206")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.205")

    def test_neural_signals_are_sparse_and_bounded(self):
        self.assertIn("let neuralSignals = [];", CORE)
        self.assertIn("Math.floor(links.length / 12)", CORE)
        self.assertIn(".slice(0, 12)", CORE)
        self.assertIn("cycle: 4100 + index * 310", CORE)
        self.assertIn("activeShare: .2 + (index % 3) * .015", CORE)

    def test_signal_and_arrival_flash_render_only_while_active(self):
        self.assertIn("if (shouldAnimate()) {", CORE)
        self.assertIn("for (const signal of neuralSignals)", CORE)
        self.assertIn("const signalX = from.x + (to.x - from.x) * progress", CORE)
        self.assertIn("if (progress > .68)", CORE)
        self.assertIn("const arrival = Math.pow(Math.sin", CORE)
        self.assertIn("if (redraw || animate || wasRunning) draw", CORE)


if __name__ == "__main__":
    unittest.main()
