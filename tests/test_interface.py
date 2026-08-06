from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "jarvis/app/static/index.html").read_text(encoding="utf-8")
MAIN = (ROOT / "jarvis/app/main.py").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


class InterfaceTests(unittest.TestCase):
    def test_prompt_history_is_persistent_and_arrow_driven(self):
        self.assertIn('localStorage.setItem(PROMPT_HISTORY_KEY', INDEX)
        self.assertIn('event.key === "ArrowUp"', INDEX)
        self.assertIn('event.key !== "ArrowDown"', INDEX)

    def test_stop_control_cancels_server_stream(self):
        self.assertIn('id="stop-button"', INDEX)
        self.assertIn('socket.send(JSON.stringify({type: "stop"}))', INDEX)
        self.assertIn('if control.get("type") == "stop"', MAIN)
        self.assertIn("stream_task.cancel()", MAIN)

    def test_hud_graph_and_versions(self):
        self.assertIn('id="brain-network"', INDEX)
        self.assertIn("prefers-reduced-motion: reduce", INDEX)
        self.assertIn('version: "0.7.3"', CONFIG)
        self.assertIn('"version": "0.7.3"', MAIN)

    def test_settings_tab_and_persistent_general_instructions(self):
        self.assertIn('id="settings-tab"', INDEX)
        self.assertIn('id="general-instructions"', INDEX)
        self.assertIn('fetch("api/settings"', INDEX)
        self.assertIn('@app.get("/api/settings")', MAIN)
        self.assertIn('@app.put("/api/settings")', MAIN)
        self.assertIn('SETTINGS_STORAGE_PATH = Path("/data/jarvis_settings.json")', MAIN)
        self.assertIn('"name": "save_general_instruction"', MAIN)
        self.assertIn('effective_system_instructions()', MAIN)

    def test_entity_aliases_flush_and_survive_page_exit(self):
        self.assertIn('aliasesInput.addEventListener("blur"', INDEX)
        self.assertIn('event.key !== "Enter"', INDEX)
        self.assertIn('window.addEventListener("pagehide", flushPendingPoliciesOnExit)', INDEX)
        self.assertIn('keepalive,', INDEX)
        self.assertNotIn('if (review.selected) queuePolicySave(entity, review, 600);', INDEX)

    def test_entity_aliases_use_addon_storage_and_restore_for_disabled_entities(self):
        self.assertIn('ENTITY_POLICY_PATH = DATA_DIR / "entity_policy.json"', MAIN)
        self.assertIn('V063_ENTITY_POLICY_PATH = Path("/share/jarvis/entity_policy.json")', MAIN)
        self.assertIn('V063_MIGRATION_MARKER = DATA_DIR / ".entity_policy_v063_migrated"', MAIN)
        self.assertIn('"policy": policy,', MAIN)
        self.assertNotIn('"policy": enabled,', MAIN)

    def test_fullscreen_layout_and_interrupted_alias_recovery(self):
        self.assertIn('html, body { width: 100%; height: 100%; overflow: hidden; }', INDEX)
        self.assertIn('height: 100dvh;', INDEX)
        self.assertIn('const ENTITY_ALIAS_BACKUP_KEY = "jarvis_entity_aliases_v1";', INDEX)
        self.assertIn('backupEntityAliases(entity.entity_id, review.aliases);', INDEX)
        self.assertIn('entityReview.clear();', INDEX)
        self.assertIn('interruptedSaves.push(entity);', INDEX)
        self.assertIn('policySaveRevisions.set(entity.entity_id, revision);', INDEX)
        self.assertIn('policySaveChains.set(entity.entity_id, currentSave);', INDEX)

    def test_socket_and_hvac_auto_approval(self):
        self.assertIn("def should_auto_approve_entity", MAIN)
        self.assertIn('domain == "climate"', MAIN)
        self.assertIn('{"socket", "outlet", "plug"}', MAIN)
        self.assertIn('"auto_approved": True', MAIN)
        self.assertIn("await list_ha_entities()", MAIN)
        self.assertIn('SAFE_CONTROL_DOMAINS = {"light", "switch", "fan", "input_boolean", "climate"}', MAIN)

    def test_cyan_user_response_and_hud_panels(self):
        self.assertIn("color: var(--cyan);", INDEX)
        self.assertIn('class="hud-rail left-rail"', INDEX)
        self.assertIn('class="hud-rail right-rail"', INDEX)

    def test_persistent_chat_sidebar_and_restore(self):
        self.assertIn('id="chat-list"', INDEX)
        self.assertIn('id="new-chat-button"', INDEX)
        self.assertIn('fetch("api/chats")', INDEX)
        self.assertIn('openChat(jarvisChatSessionId)', INDEX)
        self.assertIn('CHAT_STORAGE_PATH = Path("/data/chat_sessions.json")', MAIN)
        self.assertIn('CHAT_HISTORY_MAX_MESSAGES = 200', MAIN)
        self.assertIn('CHAT_CONTEXT_MAX_MESSAGES = 20', MAIN)
        self.assertIn('@app.get("/api/chats")', MAIN)
        self.assertIn('@app.get("/api/chat/history/{session_id}")', MAIN)
        self.assertIn('load_chat_sessions()', MAIN)

    def test_device_local_push_to_talk_and_spoken_replies(self):
        self.assertIn('id="mic-button"', INDEX)
        self.assertIn('navigator.mediaDevices.getUserMedia', INDEX)
        self.assertIn('new MediaRecorder(', INDEX)
        self.assertIn('fetch("api/voice/transcribe"', INDEX)
        self.assertIn('form.requestSubmit()', INDEX)
        self.assertIn('fetch("api/voice/speech"', INDEX)
        self.assertIn('new Audio(activeAudioUrl)', INDEX)
        self.assertIn('stopAudioPlayback("VOICE STOPPED")', INDEX)
        self.assertIn('@app.post("/api/voice/transcribe")', MAIN)
        self.assertIn('@app.post("/api/voice/speech")', MAIN)
        self.assertIn('OPENAI_TRANSCRIPTION_MODEL', MAIN)
        self.assertIn('OPENAI_TTS_MODEL', MAIN)

    def test_elevenlabs_speech_provider_is_server_side_and_selectable(self):
        self.assertIn('id="speech-provider"', INDEX)
        self.assertIn('provider: speechProvider.value', INDEX)
        self.assertIn('ELEVENLABS_SPEECH_URL', MAIN)
        self.assertIn('"xi-api-key": ELEVENLABS_API_KEY', MAIN)
        self.assertIn('"output_format": "mp3_44100_128"', MAIN)
        self.assertIn('"X-Jarvis-Speech-Provider": "elevenlabs"', MAIN)
        self.assertIn('speech_provider: "list(openai|elevenlabs)"', CONFIG)
        self.assertIn('elevenlabs_api_key: "password"', CONFIG)
        self.assertIn('elevenlabs_model_id: "eleven_flash_v2_5"', CONFIG)
        self.assertIn('MediaSource.isTypeSupported("audio/mpeg")', INDEX)
        self.assertIn('response.body.getReader()', INDEX)
        self.assertIn('/{ELEVENLABS_VOICE_ID}/stream', MAIN)
        self.assertNotIn('ELEVENLABS_API_KEY', INDEX)

    def test_voice_security_and_limits(self):
        self.assertIn('VOICE_UPLOAD_MAX_BYTES = 12 * 1024 * 1024', MAIN)
        self.assertIn('if not OPENAI_API_KEY:', MAIN)
        self.assertIn('if voice not in TTS_VOICES:', MAIN)
        self.assertIn('"Cache-Control": "no-store"', MAIN)
        self.assertNotIn('OPENAI_API_KEY', INDEX)


if __name__ == "__main__":
    unittest.main()
