import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
CORE = (ROOT / "jarvis/app/static/js/core.js").read_text(encoding="utf-8")
STYLES = (ROOT / "jarvis/app/static/css/base.css").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class ResponsiveComposerReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.135"', CONFIG)
        self.assertIn('version="0.13.135"', MAIN)
        self.assertIn("HUD 0.13.135", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.135")

    def test_modern_browsers_use_native_content_sizing(self):
        self.assertIn('CSS?.supports?.("field-sizing", "content")', CORE)
        self.assertIn("field-sizing: content", STYLES)
        self.assertIn('if (nativeComposerSizing)', CORE)

    def test_legacy_fallback_is_frame_batched(self):
        self.assertIn("let composerResizeFrame = 0", CORE)
        self.assertIn("requestAnimationFrame(() =>", CORE)
        self.assertIn("if (composerResizeFrame) return", CORE)
        self.assertIn('input.addEventListener("input", resizeComposer, {passive: true})', CORE)

    def test_synchronous_per_character_resize_was_removed(self):
        old_handler = 'input.addEventListener("input", resizeComposer);'
        old_body = 'input.style.height = "auto";\n  input.style.height = `${Math.min(input.scrollHeight, 192)}px`;'
        self.assertNotIn(old_handler, CORE)
        self.assertNotIn(old_body, CORE)

    def test_browser_checks_native_multiline_growth(self):
        self.assertIn("composerStartHeight", BROWSER)
        self.assertIn("getComputedStyle(element).fieldSizing", BROWSER)
        self.assertIn("with a second visual line", BROWSER)

    def test_release_history_includes_v013109(self):
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.134")


if __name__ == "__main__":
    unittest.main()
