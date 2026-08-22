from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class VoiceConversationRegressionTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.1"', CONFIG)
        self.assertIn('version="0.13.1"', MAIN)
        self.assertIn("HUD 0.13.1", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.1")

    def test_listening_animation_is_inline_above_composer(self):
        panel = INDEX.index('id="wake-listening-overlay"')
        composer = INDEX.index('<form id="chat-form">')
        self.assertLess(panel, composer)
        self.assertIn('class="wake-listening-panel"', INDEX)
        self.assertIn('role="status" aria-live="polite"', INDEX)
        self.assertNotIn('class="wake-listening-overlay"', INDEX)
        self.assertNotIn('position:fixed; inset:0; z-index:10000', INDEX)
        self.assertNotIn('aria-modal="true"', INDEX)

    def test_stop_phrase_tolerates_common_transcription_variants(self):
        self.assertIn('function conversationPhrase(value)', INDEX)
        self.assertIn('replace(/\\bokay\\b/g,"ok")', INDEX)
        self.assertIn('replace(/\\bthanks\\b/g,"thank you")', INDEX)
        self.assertIn('normalized===preferredStop||builtInStop', INDEX)
        self.assertIn('conversation(?: mode)?', INDEX)

    def test_command_capture_ends_on_real_post_speech_silence(self):
        self.assertIn('const continuingVoice=rms>threshold*.82&&peak>Math.max(.065,wakeNoiseFloor*3.4)', INDEX)
        self.assertIn('if(continuingVoice)wakeFallbackLastVoice=now', INDEX)
        self.assertIn('now-wakeFallbackLastVoice>=720', INDEX)
        self.assertIn('wakeFallbackCaptureTimer=setTimeout', INDEX)
        self.assertIn('},8500)', INDEX)


if __name__ == "__main__":
    unittest.main()
