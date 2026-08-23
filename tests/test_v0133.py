from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class ConversationCaptureReadinessTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.7"', CONFIG)
        self.assertIn('version="0.13.7"', MAIN)
        self.assertIn("HUD 0.13.7", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.7")

    def test_existing_microphone_is_live_and_resumed_before_reuse(self):
        fallback = INDEX[INDEX.index("async function startWakeFallback()") : INDEX.index("function recognitionLanguage()")]
        self.assertIn('track.readyState==="live"&&track.enabled', fallback)
        self.assertIn('wakeFallbackContext.state==="suspended"', fallback)
        self.assertIn("await wakeFallbackContext.resume()", fallback)
        self.assertIn('wakeFallbackContext.state==="running"', fallback)
        self.assertIn("stopWakeFallback()", fallback)

    def test_command_window_requires_recorder_and_bounds_noise_floor(self):
        command = INDEX[INDEX.index("function startFallbackCommandWindow()") : INDEX.index("function fallbackRateAllowed")]
        self.assertIn("wakeNoiseFloor=Math.min(wakeNoiseFloor,.012)", command)
        self.assertIn("if(!beginWakeFallbackRecorder())", command)
        self.assertIn("return false", command)
        self.assertIn("return true", command)

    def test_followup_retries_before_showing_listening_ui(self):
        followup = INDEX[INDEX.index("function startConversationFollowup()") : INDEX.index('window.addEventListener("zbrano-response-finished"')]
        recorder = followup.index("startFallbackCommandWindow()")
        overlay = followup.index('showWakeOverlay("CONVERSATION MODE"')
        self.assertLess(recorder, overlay)
        self.assertIn("if(!microphoneReady||!wakeFallbackStream)", followup)
        self.assertIn("Conversation microphone capture did not arm - retrying", followup)
        self.assertGreaterEqual(followup.count("setTimeout(attempt,500)"), 2)

    def test_speech_speed_is_adjustable_and_applied_to_all_playback(self):
        self.assertIn('id="voice-speed" type="range" min="0.8" max="1.4" step="0.05"', INDEX)
        self.assertIn("speed: speechPlaybackRate", INDEX)
        self.assertIn("audio.playbackRate=rate", INDEX)
        self.assertEqual(INDEX.count("applySpeechPlaybackSettings(activeAudio)"), 3)
        self.assertNotIn("if(activeAudio)activeAudio.playbackRate=speechPlaybackRate", INDEX)


if __name__ == "__main__":
    unittest.main()
