import json
from pathlib import Path
import tempfile
import unittest

from zbrano.app.services import assist_bridge


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "zbrano/config.yaml").read_text(encoding="utf-8")
MAIN = (ROOT / "zbrano/app/main.py").read_text(encoding="utf-8")
INDEX = (ROOT / "zbrano/app/static/index.html").read_text(encoding="utf-8")
SATELLITE = (ROOT / "zbrano/app/static/js/voice/satellite.js").read_text(encoding="utf-8")
COMPONENT = ROOT / "distribution/public-repository/custom_components/zbrano"
CONVERSATION = (COMPONENT / "conversation.py").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "zbrano/release_manifest.json").read_text(encoding="utf-8"))


class NativeAssistSatelliteReleaseTests(unittest.TestCase):
    def test_release_is_aligned(self):
        self.assertIn('version: "0.13.217"', CONFIG)
        self.assertIn('version="0.13.217"', MAIN)
        self.assertIn("HUD 0.13.217", INDEX)
        self.assertEqual(MANIFEST["version"], "0.13.217")
        self.assertEqual(MANIFEST["history_backfill"][-1]["version"], "0.13.216")

    def test_pairing_token_is_hashed_and_authenticated(self):
        original = assist_bridge.ASSIST_BRIDGE_PATH
        with tempfile.TemporaryDirectory() as temporary:
            try:
                path = Path(temporary) / "bridge.json"
                assist_bridge.configure_assist_bridge(path=path)
                paired = assist_bridge.create_pairing_token()
                stored = path.read_text(encoding="utf-8")
                self.assertNotIn(paired["pairing_token"], stored)
                self.assertTrue(assist_bridge.valid_pairing_token(f"Bearer {paired['pairing_token']}"))
                self.assertFalse(assist_bridge.valid_pairing_token("Bearer incorrect"))
            finally:
                assist_bridge.configure_assist_bridge(path=original)

    def test_duplicate_request_cache_and_spoken_output(self):
        assist_bridge.configure_assist_bridge(path=assist_bridge.ASSIST_BRIDGE_PATH)
        payload = {"reply": "Done", "conversation_id": "one"}
        assist_bridge.remember_response("request-one", "Turn it on", payload)
        self.assertEqual(assist_bridge.cached_response("request-one", "Turn it on"), payload)
        with self.assertRaises(ValueError):
            assist_bridge.cached_response("request-one", "Turn it off")
        spoken = assist_bridge.speech_reply("## Result\n\n- **Kitchen light** is `on`.")
        self.assertEqual(spoken, "Result\n\nKitchen light is on.")

    def test_public_component_registers_one_native_conversation_agent(self):
        required = {
            "manifest.json", "__init__.py", "api.py", "config_flow.py",
            "const.py", "conversation.py", "strings.json",
        }
        self.assertTrue(required.issubset({path.name for path in COMPONENT.iterdir()}))
        self.assertIn("ConversationEntity", CONVERSATION)
        self.assertIn("conversation.async_set_agent", CONVERSATION)
        self.assertNotIn("async_handle_intents", CONVERSATION)
        self.assertIn('"request_id": uuid.uuid4().hex', CONVERSATION)

    def test_voice_settings_explain_opt_in_pipeline_pairing(self):
        for marker in (
            'id="assist-bridge-pair"', 'id="assist-bridge-token"',
            "Existing Assist pipelines remain unchanged",
        ):
            self.assertIn(marker, INDEX)
        self.assertIn('fetch("api/assist/bridge/pair"', SATELLITE)
        self.assertIn('navigator.clipboard.writeText', SATELLITE)


if __name__ == "__main__":
    unittest.main()
