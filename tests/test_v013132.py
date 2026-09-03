import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE = (ROOT / "jarvis" / "app" / "static" / "js" / "core.js").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis" / "release_manifest.json").read_text(encoding="utf-8"))


class V013132NeuralPauseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertEqual(MANIFEST["version"], "0.13.133")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.132")

    def test_active_chat_and_selection_pause_animation(self):
        self.assertIn('window.dispatchEvent(new CustomEvent("zbrano-neural-intensity-change"', CORE)
        self.assertIn('stage?.classList.contains("neuron-intense")', CORE)
        self.assertIn('selectionTouchesMessages()', CORE)
        self.assertIn('messages.addEventListener("pointerdown"', CORE)
        self.assertIn('document.addEventListener("selectionchange"', CORE)
        self.assertIn('canvas.dataset.animationState = "paused"', CORE)

    def test_hidden_chat_and_reduced_motion_do_not_animate(self):
        self.assertIn('!document.hidden', CORE)
        self.assertIn('!chatPanel?.classList.contains("hidden")', CORE)
        self.assertIn('!prefersReducedMotion()', CORE)
        self.assertIn('new MutationObserver(() => refreshAnimation(false))', CORE)


if __name__ == "__main__":
    unittest.main()
