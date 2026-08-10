import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_voice_latency_and_activity_revisions_v01253.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01253_starts_first_speech_phrase_earlier_without_dropping_words():
    assert "remaining.length >= 56" in PATCH
    assert "phraseLimit = Math.min(88, remaining.length)" in PATCH
    assert "remaining.slice(0, splitAt).trim()" in PATCH
    assert "remaining = remaining.slice(splitAt)" in PATCH
    assert "{12,220}" in PATCH


def test_v01253_buffers_mp3_before_playback_to_protect_first_word():
    assert "bufferedBytes += value.byteLength" in PATCH
    assert "bufferedBytes >= 24576" in PATCH
    assert "bufferedSeconds >= 0.28" in PATCH
    assert "startBufferedPlayback" in PATCH
    assert "if (!playbackStarted && bufferedBytes > 0)" in PATCH


def test_v01253_uses_server_revisions_for_meaningful_tab_activity():
    assert '@app.get("/api/tab-activity")' in PATCH
    for name in ("chat", "files", "plugins", "automations", "notifications", "settings", "developer"):
        assert f'"{name}"' in PATCH
    assert "checkSemanticActivity" in PATCH
    assert 'nativeFetch("api/tab-activity"' in PATCH
    assert "setInterval(checkSemanticActivity, 10000)" in PATCH
    assert "checkNotificationActivity" in PATCH  # present only in removal guard
    assert "_tab_activity_value_revision" in PATCH
    assert '"last_observed_state", "last_triggered_at", "trigger_count", "updated_at", "status"' in PATCH


def test_v01253_new_chat_clears_tool_and_completion_activity():
    assert "resetToolTimeline();" in PATCH
    assert "responseTimerId = null;" in PATCH
    assert "responseStartedAt = null;" in PATCH
    assert "firstResponseSeconds = null;" in PATCH
    assert "aiActivity.hidden = true;" in PATCH
    assert 'aiActivityLabel.textContent = "";' in PATCH
    assert 'aiResponseTimer.textContent = "";' in PATCH


def test_v01253_speak_replies_is_stored_per_chat_with_settings_as_new_chat_default():
    assert 'const CHAT_AUTO_SPEAK_KEY = "zbrano_chat_auto_speak_v1"' in PATCH
    assert "chatAutoSpeakPreferences[sessionId] = jarvisPreferences.auto_speak !== false" in PATCH
    assert "await applyChatAutoSpeakPreference(sessionId, data.auto_speak);" in PATCH
    assert "setChatAutoSpeakPreference(jarvisChatSessionId, autoSpeak.checked)" in PATCH
    assert "deleteChatAutoSpeakPreference(sessionId);" in PATCH
    assert "autoSpeak: settingsAutoSpeak.checked" in PATCH
    assert "loadSettings().finally(() => openChat(jarvisChatSessionId))" in PATCH
    assert '@app.put("/api/chat/{session_id}/voice")' in PATCH
    assert '"auto_speak": CHAT_SESSION_META.get(session_id, {}).get("auto_speak")' in PATCH
    assert "persistChatAutoSpeakPreference(sessionId, enabled)" in PATCH


def test_v01253_runs_after_v01252_and_aligns_release():
    name = "apply_voice_latency_and_activity_revisions_v01253.py"
    assert f"COPY {name}" in DOCKER
    assert DOCKER.index("python3 ./apply_notification_watch_dedup_v01252.py") < DOCKER.index(f"python3 ./{name}")
    assert DOCKER.index(f"python3 ./{name}") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.53"' in CONFIG
    assert MANIFEST["version"] == "0.12.53"
    assert "ZBRANO v0.12.53" in README
    assert 'version="0.12.53"' in PATCH
    assert "HUD 0.12.53" in PATCH
