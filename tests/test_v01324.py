from pathlib import Path
import json
import tempfile
import unittest

from jarvis.app.domains import settings


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
SETTINGS = (APP / "domains/settings.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class SettingsDomainBoundaryTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version: "0.13.44"', CONFIG)
        self.assertIn('version="0.13.44"', MAIN)
        self.assertIn("HUD 0.13.44", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.44")

    def test_settings_store_is_outside_composition_root(self):
        self.assertNotIn("def load_settings_payload(", MAIN)
        self.assertNotIn("def load_preferences(", MAIN)
        self.assertIn("def load_settings_payload(", SETTINGS)
        self.assertIn("def load_preferences(", SETTINGS)
        self.assertIn('SETTINGS_STORAGE_PATH = Path("/data/jarvis_settings.json")', SETTINGS)

    def test_settings_json_round_trip_preserves_payload(self):
        original_path = settings.SETTINGS_STORAGE_PATH
        with tempfile.TemporaryDirectory() as directory:
            settings.SETTINGS_STORAGE_PATH = Path(directory) / "jarvis_settings.json"
            try:
                payload = {"version": 3, "general_instructions": "Keep behavior stable", "preferences": {"theme": "dark"}}
                settings.save_settings_payload(payload)
                self.assertEqual(settings.load_settings_payload(), payload)
            finally:
                settings.SETTINGS_STORAGE_PATH = original_path

    def test_defaults_and_pronunciation_contract_are_preserved(self):
        self.assertEqual(settings.ELEVENLABS_VOICE_DEFAULTS["speed"], 0.96)
        self.assertEqual(settings.GENERAL_INSTRUCTIONS_MAX_CHARS, 12000)
        original_loader = settings.load_preferences
        settings.load_preferences = lambda: {"pronunciation_dictionary": "ZBRANO=Zee brah no"}
        try:
            self.assertEqual(settings.apply_pronunciation_dictionary("Ask ZBRANO now"), "Ask Zee brah no now")
        finally:
            settings.load_preferences = original_loader


if __name__ == "__main__":
    unittest.main()
