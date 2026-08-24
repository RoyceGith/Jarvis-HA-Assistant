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


class AdaptiveSpeechBufferTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.19"', CONFIG)
        self.assertIn('version="0.13.19"', MAIN)
        self.assertIn("HUD 0.13.19", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.19")

    def test_adjusted_speed_can_use_progressive_playback(self):
        playback = INDEX[INDEX.index("const canStreamMp3") : INDEX.index("if (!canStreamMp3)")]
        self.assertIn("response.body && window.MediaSource", playback)
        self.assertNotIn("speechPlaybackRate-1", playback)

    def test_start_requires_rate_aware_buffer_and_sustainable_delivery(self):
        self.assertIn("playbackBufferTarget=Math.max(1.25,1.35*speechPlaybackRate)", INDEX)
        self.assertIn("productionRate=bufferedSeconds/bufferingSeconds", INDEX)
        self.assertIn("bufferedSeconds>=playbackBufferTarget", INDEX)
        self.assertIn("productionRate>=speechPlaybackRate*1.5", INDEX)
        self.assertNotIn("bufferedSeconds >= 0.28", INDEX)

    def test_short_audio_still_starts_after_download_completes(self):
        self.assertIn("if (!playbackStarted && bufferedBytes > 0) startBufferedPlayback()", INDEX)

    def test_first_phrase_is_extracted_early_while_later_chunks_stay_longer(self):
        extraction = INDEX[INDEX.index("function extractSpeakableChunks") : INDEX.index("function cleanupMicrophone")]
        self.assertIn("fastStart = false", extraction)
        self.assertIn("fastStart ? 64 : 120", extraction)
        self.assertIn("fastStart ? 120 : 200", extraction)
        self.assertIn("fastStart&&remaining.length>110", extraction)
        self.assertIn("const fastSpeechStart=!speechQueueRunning&&!speechQueue.length&&!activeAudio", INDEX)
        self.assertIn("extractSpeakableChunks(speechBuffer,false,fastSpeechStart)", INDEX)
        self.assertIn("primeSpeechPrefetch(force)", INDEX)


if __name__ == "__main__":
    unittest.main()
