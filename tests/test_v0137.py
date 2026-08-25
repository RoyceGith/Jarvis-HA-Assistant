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


class VoiceBargeInTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.41"', CONFIG)
        self.assertIn('version="0.13.41"', MAIN)
        self.assertIn("HUD 0.13.41", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.41")

    def test_talk_remains_enabled_while_response_streams(self):
        submit = INDEX[INDEX.index('form.addEventListener("submit"') : INDEX.index("const jarvisMessage")]
        self.assertIn("micButton.disabled = false", submit)
        self.assertNotIn("micButton.disabled = true", submit)

    def test_talk_interrupts_generation_then_starts_recording(self):
        handler = INDEX[INDEX.index('micButton.addEventListener("click"') : INDEX.index("const PROMPT_HISTORY_KEY")]
        self.assertIn("if(activeRequest)interruptActiveResponseForVoice()", handler)
        self.assertIn("startRecording()", handler)
        interrupt = INDEX[INDEX.index("function interruptActiveResponseForVoice") : INDEX.index('micButton.addEventListener("click"')]
        self.assertIn("request.stopped=true", interrupt)
        self.assertIn('socket.send(JSON.stringify({type:"stop"}))', interrupt)
        self.assertIn("activeRequest=null", interrupt)
        self.assertIn("[Interrupted for voice]", interrupt)

    def test_stale_interrupted_close_cannot_reset_replacement_request(self):
        close = INDEX[INDEX.index('socket.addEventListener("close"') : INDEX.index("function startBrainNetwork")]
        stale_guard = "if(activeRequest!==requestState){if(requestState.stopped)refreshChatList();return}"
        self.assertIn(stale_guard, close)
        self.assertLess(close.index(stale_guard), close.index("input.disabled = false"))

    def test_playback_keeps_only_opted_in_local_wake_monitoring(self):
        monitor = INDEX[INDEX.index("async function maintainPlaybackWake") : INDEX.index("const voiceObserver")]
        self.assertIn("wakeShadowEnabled.checked", monitor)
        self.assertIn("wakeLocalActivate.checked", monitor)
        self.assertIn("stopWake(true)", monitor)
        self.assertIn("await startWakeFallback()", monitor)
        sample = INDEX[INDEX.index("function sampleWakeFallback") : INDEX.index("async function startWakeFallback")]
        self.assertIn('wakeShadowEnabled.checked&&wakeFallbackMode==="wake"', sample)

    def test_playback_wake_uses_stronger_confirmation(self):
        scoring = INDEX[INDEX.index("function handleWakeShadowScore") : INDEX.index("function startWakeShadow(context")]
        self.assertIn("Math.max(.68,threshold+.12)", scoring)
        self.assertIn("requiredFrames=playbackActive?3:2", scoring)
        self.assertIn("playbackContainsWake=wakeCandidates().some", scoring)
        self.assertIn("canBargeIn=activationReady&&playbackActive&&!playbackContainsWake", scoring)
        self.assertIn("startPlaybackWakeBargeIn(score)", scoring)

    def test_confirmed_wake_stops_playback_then_arms_after_echo_clear(self):
        barge = INDEX[INDEX.index("function startPlaybackWakeBargeIn") : INDEX.index("function fallbackRateAllowed")]
        self.assertIn("interruptActiveResponseForVoice()", barge)
        self.assertIn("setTimeout", barge)
        self.assertIn("240", barge)
        self.assertLess(barge.index("startFallbackCommandWindow()"), barge.index('showWakeOverlay("WAKE PHRASE HEARD"'))


if __name__ == "__main__":
    unittest.main()
