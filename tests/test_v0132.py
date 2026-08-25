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


class FollowupCaptureRegressionTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.28"', CONFIG)
        self.assertIn('version="0.13.28"', MAIN)
        self.assertIn("HUD 0.13.28", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.28")

    def test_command_window_records_before_speech_detection(self):
        window = INDEX[INDEX.index("function startFallbackCommandWindow()"):INDEX.index("function fallbackRateAllowed")]
        self.assertIn("beginWakeFallbackRecorder()", window)
        self.assertIn("performance.now()+160", window)
        self.assertIn("discardWakeFallbackRecorder()", window)

    def test_empty_followup_rearms_and_timeout_cleans_up(self):
        self.assertIn('mode==="command"&&generation===wakeFallbackGeneration&&wakeFallbackMode==="command"&&!wakeFallbackRecorder', INDEX)
        self.assertIn('"No speech recognized - still listening..."', INDEX)
        self.assertIn("wakeConversationListening=false;discardWakeFallbackRecorder();wakeFallbackMode=\"wake\";hideWakeOverlay(250)", INDEX)

    def test_animation_is_small_centered_unframed_and_rms_responsive(self):
        self.assertIn("width:min(240px,calc(100% - 1rem)); min-height:34px; align-self:center", INDEX)
        self.assertNotIn(".wake-listening-panel { position:fixed", INDEX)
        panel_rule = INDEX[INDEX.index(".wake-listening-panel {"):INDEX.index(".wake-listening-panel[hidden]")]
        self.assertNotIn("border:", panel_rule)
        self.assertNotIn("background:", panel_rule)
        self.assertNotIn("box-shadow:", panel_rule)
        self.assertIn('<span class="wake-levels"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></span>', INDEX)
        self.assertNotIn("wake-microphone", INDEX)
        self.assertNotIn("wake-ring", INDEX)
        self.assertIn("function updateWakeListeningLevel(rms=0,peak=0)", INDEX)
        self.assertIn("updateWakeListeningLevel(rms,peak)", INDEX)
        self.assertIn("bar.style.height=", INDEX)
        self.assertIn("bar.style.opacity=", INDEX)


if __name__ == "__main__":
    unittest.main()
