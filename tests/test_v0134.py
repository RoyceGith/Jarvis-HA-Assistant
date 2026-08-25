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


class StableSpeechSpeedTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.27"', CONFIG)
        self.assertIn('version="0.13.27"', MAIN)
        self.assertIn("HUD 0.13.27", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.27")

    def test_adjusted_speed_avoids_the_unsafe_early_start_threshold(self):
        self.assertNotIn("bufferedSeconds >= 0.28", INDEX)

    def test_rate_is_locked_when_metadata_loads(self):
        playback = INDEX[INDEX.index("function applySpeechPlaybackSettings(audio)") : INDEX.index("async function playSpeechText")]
        self.assertIn("audio.defaultPlaybackRate=rate", playback)
        self.assertIn("audio.playbackRate=rate", playback)
        self.assertIn('audio.addEventListener("loadedmetadata"', playback)

    def test_slider_does_not_change_active_segment(self):
        listener = INDEX[INDEX.index('voiceSpeed.addEventListener("input"') : INDEX.index("testVoice.addEventListener")]
        self.assertIn("saveVoiceSettings()", listener)
        self.assertNotIn("activeAudio", listener)


if __name__ == "__main__":
    unittest.main()
