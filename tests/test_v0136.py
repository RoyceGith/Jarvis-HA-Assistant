from pathlib import Path
import json
import unittest
from tests.frontend_source import load_frontend_source
from tests.backend_source import load_backend_source


ROOT = Path(__file__).resolve().parents[1]
INDEX = load_frontend_source()
MAIN = load_backend_source()
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class ConversationCaptureHealthTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.40"', CONFIG)
        self.assertIn('version="0.13.40"', MAIN)
        self.assertIn("HUD 0.13.40", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.40")

    def test_cancelled_microphone_start_cannot_install_stale_stream(self):
        fallback = INDEX[INDEX.index("async function startWakeFallback()") : INDEX.index("function recognitionLanguage()")]
        self.assertIn("const startToken=++wakeFallbackStartToken", fallback)
        self.assertGreaterEqual(fallback.count("startToken!==wakeFallbackStartToken"), 2)
        self.assertIn("wakeFallbackStartToken++", INDEX[INDEX.index("function stopWakeFallback()") : INDEX.index("function stopWake(")])
        self.assertIn("if(startToken===wakeFallbackStartToken)wakeFallbackStarting=false", fallback)

    def test_capture_health_requires_every_live_component(self):
        health = INDEX[INDEX.index("function wakeFallbackCaptureHealthy") : INDEX.index("function stopWakeFallback()")]
        self.assertIn('track.readyState==="live"&&track.enabled&&!track.muted', health)
        self.assertIn('wakeFallbackContext?.state==="running"', health)
        self.assertIn("wakeFallbackAnalyser", health)
        self.assertIn("wakeFallbackTimer", health)
        self.assertIn("samplesFresh", health)
        self.assertIn('wakeFallbackRecorder?.state==="recording"', health)

    def test_conversation_watchdog_reconnects_stalled_capture(self):
        followup = INDEX[INDEX.index("function startConversationFollowup()") : INDEX.index('window.addEventListener("zbrano-response-finished"')]
        self.assertIn("const verifyCapture=()", followup)
        self.assertIn("wakeFallbackCaptureHealthy(true)", followup)
        self.assertIn("Conversation microphone stopped responding - reconnecting", followup)
        self.assertIn("stopWake();wakeConversationWaitTimer=setTimeout(attempt,500)", followup)

    def test_failed_or_short_command_capture_rearms_recorder(self):
        finish = INDEX[INDEX.index("function finishWakeFallbackUtterance") : INDEX.index("function sampleWakeFallback")]
        self.assertGreaterEqual(finish.count('if(mode==="command")beginWakeFallbackRecorder()'), 2)
        self.assertIn('if(mode==="command"&&generation===wakeFallbackGeneration)beginWakeFallbackRecorder()', finish)
        self.assertIn("wakeFallbackFinalizing", finish)

    def test_cancel_clears_watchdog_and_discards_recorder(self):
        cancel = INDEX[INDEX.index('wakeOverlayCancel.addEventListener("click"') : INDEX.index("wakeTestPhrase.addEventListener")]
        self.assertIn("clearWakeConversationHealth()", cancel)
        self.assertIn("discardWakeFallbackRecorder()", cancel)


if __name__ == "__main__":
    unittest.main()
