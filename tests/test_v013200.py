import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
INDEX = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
CORE = (ROOT / "jarvis/app/static/js/core.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "jarvis/tests/browser_smoke.cjs").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "jarvis/tests/test_app_integration.py").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class StoppedResponsePreservationReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.212"', CONFIG)
        self.assertIn('version="0.13.212"', MAIN)
        self.assertIn("HUD 0.13.212", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.212")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.211")

    def test_stop_uses_raw_markdown_instead_of_compact_dom_text(self):
        self.assertIn("function finishInterruptedMessage", CORE)
        self.assertIn('String(item?.dataset?.rawText || "").trim()', CORE)
        self.assertNotIn("jarvisMessage.textContent.trim()", CORE)
        self.assertIn('finishInterruptedMessage(jarvisMessage, "[Response stopped]"', CORE)

    def test_partial_stream_is_persisted_when_cancelled(self):
        self.assertIn("except asyncio.CancelledError:", MAIN)
        self.assertIn('partial_reply + "\\n\\n[Response stopped]"', MAIN)
        self.assertIn("test_stopped_stream_persists_partial_markdown", INTEGRATION)

    def test_browser_covers_structured_markdown(self):
        self.assertIn("const stoppedMarkdown", BROWSER)
        self.assertIn("<h4>Beef soup", BROWSER)
        self.assertIn("<ol>", BROWSER)
        self.assertIn("<strong>Tip:", BROWSER)


if __name__ == "__main__":
    unittest.main()
