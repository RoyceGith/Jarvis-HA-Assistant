import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.53 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.53 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        '''                "updated_at": CHAT_SESSION_META.get(session_id, {}).get("updated_at", 0),
                "messages": list(messages),''',
        '''                "updated_at": CHAT_SESSION_META.get(session_id, {}).get("updated_at", 0),
                "auto_speak": CHAT_SESSION_META.get(session_id, {}).get("auto_speak"),
                "messages": list(messages),''',
        "chat voice persistence",
    )
    backend = replace_once(
        backend,
        '''            "title": str(record.get("title") or chat_title(CHAT_SESSIONS[session_id])),
            "updated_at": float(record.get("updated_at", 0)),
        }''',
        '''            "title": str(record.get("title") or chat_title(CHAT_SESSIONS[session_id])),
            "updated_at": float(record.get("updated_at", 0)),
            "auto_speak": record.get("auto_speak") if isinstance(record.get("auto_speak"), bool) else None,
        }''',
        "chat voice restore",
    )
    backend = replace_once(
        backend,
        '''    CHAT_SESSION_META[session_id] = {
        "title": chat_title(history),
        "updated_at": time.time(),
    }
    persist_chat_sessions()''',
        '''    CHAT_SESSION_META[session_id] = {
        "title": chat_title(history),
        "updated_at": time.time(),
        "auto_speak": CHAT_SESSION_META.get(session_id, {}).get("auto_speak"),
    }
    persist_chat_sessions()''',
        "chat voice preservation after messages",
    )
    backend = replace_once(
        backend,
        '''        "title": CHAT_SESSION_META.get(session_id, {}).get("title") or chat_title(history),
        "messages": [public_chat_message(message) for message in history],''',
        '''        "title": CHAT_SESSION_META.get(session_id, {}).get("title") or chat_title(history),
        "auto_speak": CHAT_SESSION_META.get(session_id, {}).get("auto_speak"),
        "messages": [public_chat_message(message) for message in history],''',
        "chat history voice response",
    )

    activity_api = '''@app.put("/api/chat/{session_id}/voice")
async def update_chat_voice_preference(session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    enabled = payload.get("auto_speak")
    if not isinstance(enabled, bool):
        raise HTTPException(status_code=400, detail="auto_speak must be a boolean")
    get_chat_history(session_id)
    CHAT_SESSION_META[session_id]["auto_speak"] = enabled
    persist_chat_sessions()
    return {"session_id": session_id, "auto_speak": enabled}


def _tab_activity_revision(path: Path) -> str:
    try:
        stat = path.stat()
        return f"{stat.st_mtime_ns}:{stat.st_size}"
    except OSError:
        return "missing"


def _tab_activity_value_revision(value: Any) -> str:
    import hashlib

    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@app.get("/api/tab-activity")
async def read_tab_activity() -> dict[str, Any]:
    automation_data = automation_store()
    volatile_watch_fields = {
        "last_observed_state", "last_triggered_at", "trigger_count", "updated_at", "status",
    }
    semantic_automations = [
        {key: value for key, value in item.items() if key not in volatile_watch_fields}
        for item in automation_data.get("automations", [])
    ]
    return {
        "revisions": {
            "chat": _tab_activity_revision(CHAT_STORAGE_PATH),
            "files": _tab_activity_revision(SHARED_FILE_ROOT),
            "plugins": ":".join((
                _tab_activity_revision(PLUGIN_REGISTRY_PATH),
                _tab_activity_revision(PLUGIN_OAUTH_PATH),
            )),
            "automations": _tab_activity_value_revision({
                "settings": automation_data.get("settings", {}),
                "automations": semantic_automations,
                "suggestions": automation_data.get("suggestions", []),
                "timeline": automation_data.get("timeline", []),
            }),
            "notifications": _tab_activity_revision(NOTIFICATION_STORAGE_PATH),
            "settings": _tab_activity_revision(SETTINGS_STORAGE_PATH),
            "developer": _tab_activity_revision(DEVELOPER_STATE_PATH),
        }
    }


'''
    backend = replace_once(
        backend,
        '@app.get("/api/notifications/activity")\n',
        activity_api + '@app.get("/api/notifications/activity")\n',
        "semantic tab activity endpoint",
    )

    old_reader = '''    const reader = response.body.getReader();
    let playbackStarted = false;
    let playbackEnded = null;
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      if (!value?.byteLength) continue;
      await new Promise((resolve, reject) => {
        sourceBuffer.addEventListener("updateend", resolve, {once: true});
        sourceBuffer.addEventListener("error", () => reject(new Error("Audio buffer failed")), {once: true});
        sourceBuffer.appendBuffer(value);
      });
      if (!playbackStarted) {
        playbackStarted = true;
        playbackEnded = waitForAudioEnd(activeAudio);
        setVoiceState("SPEAKING");
        activeAudio.play().catch(error => {
          if (error.name !== "AbortError") setVoiceState("VOICE ERROR", error.message || String(error));
        });
      }
    }
'''
    new_reader = '''    const reader = response.body.getReader();
    let playbackStarted = false;
    let playbackEnded = null;
    let bufferedBytes = 0;
    const startBufferedPlayback = () => {
      if (playbackStarted) return;
      playbackStarted = true;
      playbackEnded = waitForAudioEnd(activeAudio);
      setVoiceState("SPEAKING");
      activeAudio.play().catch(error => {
        if (error.name !== "AbortError") setVoiceState("VOICE ERROR", error.message || String(error));
      });
    };
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      if (!value?.byteLength) continue;
      bufferedBytes += value.byteLength;
      await new Promise((resolve, reject) => {
        sourceBuffer.addEventListener("updateend", resolve, {once: true});
        sourceBuffer.addEventListener("error", () => reject(new Error("Audio buffer failed")), {once: true});
        sourceBuffer.appendBuffer(value);
      });
      const bufferedSeconds = sourceBuffer.buffered.length
        ? sourceBuffer.buffered.end(sourceBuffer.buffered.length - 1)
        : 0;
      if (!playbackStarted && (bufferedBytes >= 24576 || bufferedSeconds >= 0.28)) startBufferedPlayback();
    }
    if (!playbackStarted && bufferedBytes > 0) startBufferedPlayback();
'''
    frontend = replace_once(frontend, old_reader, new_reader, "MP3 startup buffer")

    old_chunker = '''function extractSpeakableChunks(buffer, final = false) {
  const chunks = [];
  let remaining = buffer;
  const sentencePattern = /^([\\s\\S]{24,240}?[.!?](?:\\s+|$))/;
  while (true) {
    const match = remaining.match(sentencePattern);
    if (!match) break;
    chunks.push(match[1].trim());
    remaining = remaining.slice(match[1].length);
  }
  if (final && remaining.trim()) {
    chunks.push(remaining.trim());
    remaining = "";
  } else if (remaining.length > 240) {
    const splitAt = Math.max(
      remaining.lastIndexOf(", ", 180),
      remaining.lastIndexOf("; ", 180),
      remaining.lastIndexOf(" ", 180)
    );
    if (splitAt > 80) {
      chunks.push(remaining.slice(0, splitAt + 1).trim());
      remaining = remaining.slice(splitAt + 1);
    }
  }
  return {chunks, remaining};
}
'''
    new_chunker = '''function extractSpeakableChunks(buffer, final = false) {
  const chunks = [];
  let remaining = buffer;
  const sentencePattern = /^([\\s\\S]{12,220}?[.!?](?:\\s+|$))/;
  while (true) {
    const match = remaining.match(sentencePattern);
    if (!match) break;
    chunks.push(match[1].trim());
    remaining = remaining.slice(match[1].length);
  }
  if (final && remaining.trim()) {
    chunks.push(remaining.trim());
    remaining = "";
  } else if (!chunks.length && remaining.length >= 56) {
    const phraseLimit = Math.min(88, remaining.length);
    const splitAt = Math.max(
      remaining.lastIndexOf(", ", phraseLimit),
      remaining.lastIndexOf("; ", phraseLimit),
      remaining.lastIndexOf(": ", phraseLimit),
      remaining.lastIndexOf(" ", phraseLimit)
    );
    if (splitAt >= 32) {
      chunks.push(remaining.slice(0, splitAt).trim());
      remaining = remaining.slice(splitAt);
    }
  } else if (remaining.length > 220) {
    const splitAt = Math.max(
      remaining.lastIndexOf(", ", 170),
      remaining.lastIndexOf("; ", 170),
      remaining.lastIndexOf(" ", 170)
    );
    if (splitAt > 80) {
      chunks.push(remaining.slice(0, splitAt).trim());
      remaining = remaining.slice(splitAt);
    }
  }
  return {chunks, remaining};
}
'''
    frontend = replace_once(frontend, old_chunker, new_chunker, "low-latency speech chunking")

    frontend = replace_once(
        frontend,
        'const VOICE_SETTINGS_KEY = "jarvis_voice_settings_v1";\n',
        '''const VOICE_SETTINGS_KEY = "jarvis_voice_settings_v1";
const CHAT_AUTO_SPEAK_KEY = "zbrano_chat_auto_speak_v1";
let chatAutoSpeakPreferences = {};
try {
  const storedChatVoice = JSON.parse(localStorage.getItem(CHAT_AUTO_SPEAK_KEY) || "{}");
  if (storedChatVoice && typeof storedChatVoice === "object" && !Array.isArray(storedChatVoice)) {
    chatAutoSpeakPreferences = storedChatVoice;
  }
} catch {}

function saveChatAutoSpeakPreferences() {
  localStorage.setItem(CHAT_AUTO_SPEAK_KEY, JSON.stringify(chatAutoSpeakPreferences));
}

async function persistChatAutoSpeakPreference(sessionId, enabled) {
  try {
    await fetch(`api/chat/${encodeURIComponent(sessionId)}/voice`, {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({auto_speak: Boolean(enabled)}),
    });
  } catch (_) {}
}

async function applyChatAutoSpeakPreference(sessionId, serverPreference) {
  if (typeof serverPreference === "boolean") {
    chatAutoSpeakPreferences[sessionId] = serverPreference;
  } else if (!Object.prototype.hasOwnProperty.call(chatAutoSpeakPreferences, sessionId)) {
    chatAutoSpeakPreferences[sessionId] = jarvisPreferences.auto_speak !== false;
  }
  saveChatAutoSpeakPreferences();
  autoSpeak.checked = chatAutoSpeakPreferences[sessionId] === true;
  if (typeof serverPreference !== "boolean") {
    await persistChatAutoSpeakPreference(sessionId, autoSpeak.checked);
  }
}

function setChatAutoSpeakPreference(sessionId, enabled) {
  chatAutoSpeakPreferences[sessionId] = Boolean(enabled);
  saveChatAutoSpeakPreferences();
  persistChatAutoSpeakPreference(sessionId, enabled);
}

function deleteChatAutoSpeakPreference(sessionId) {
  if (!Object.prototype.hasOwnProperty.call(chatAutoSpeakPreferences, sessionId)) return;
  delete chatAutoSpeakPreferences[sessionId];
  saveChatAutoSpeakPreferences();
}
''',
        "per-chat voice preference storage",
    )
    frontend = replace_once(
        frontend,
        '  if (typeof voiceSettings.autoSpeak === "boolean") autoSpeak.checked = voiceSettings.autoSpeak;\n',
        '',
        "obsolete global chat checkbox restore",
    )
    frontend = replace_once(
        frontend,
        '''  localStorage.setItem(VOICE_SETTINGS_KEY, JSON.stringify({
    autoSpeak: autoSpeak.checked,
    provider: speechProvider.value,
    voice: voiceSelect.value,
  }));''',
        '''  localStorage.setItem(VOICE_SETTINGS_KEY, JSON.stringify({
    autoSpeak: settingsAutoSpeak.checked,
    provider: speechProvider.value,
    voice: voiceSelect.value,
  }));''',
        "voice default persistence",
    )
    frontend = replace_once(
        frontend,
        'autoSpeak.addEventListener("change", saveVoiceSettings);',
        '''autoSpeak.addEventListener("change", () => {
  setChatAutoSpeakPreference(jarvisChatSessionId, autoSpeak.checked);
});''',
        "per-chat checkbox handler",
    )
    frontend = replace_once(
        frontend,
        '''settingsAutoSpeak.addEventListener("change", () => { autoSpeak.checked = settingsAutoSpeak.checked; });
autoSpeak.addEventListener("change", () => { settingsAutoSpeak.checked = autoSpeak.checked; });''',
        '''settingsAutoSpeak.addEventListener("change", saveVoiceSettings);''',
        "global and chat voice decoupling",
    )
    frontend = replace_once(
        frontend,
        '''    autoSpeak.checked = jarvisPreferences.auto_speak !== false;
    settingsAutoSpeak.checked = autoSpeak.checked;''',
        '''    settingsAutoSpeak.checked = jarvisPreferences.auto_speak !== false;''',
        "settings default loading",
    )
    frontend = replace_once(
        frontend,
        '''    jarvisPreferences = data.preferences || jarvisPreferences;
    autoSpeak.checked = jarvisPreferences.auto_speak !== false;
    applyInterfacePreferences(jarvisPreferences);''',
        '''    jarvisPreferences = data.preferences || jarvisPreferences;
    settingsAutoSpeak.checked = jarvisPreferences.auto_speak !== false;
    applyInterfacePreferences(jarvisPreferences);''',
        "settings default save response",
    )
    frontend = replace_once(
        frontend,
        '''    jarvisChatSessionId = sessionId;
    updateSessionDisplay();
    messages.innerHTML = "";''',
        '''    jarvisChatSessionId = sessionId;
    updateSessionDisplay();
    await applyChatAutoSpeakPreference(sessionId, data.auto_speak);
    messages.innerHTML = "";''',
        "chat voice restoration",
    )
    frontend = replace_once(
        frontend,
        '''  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);

  if (sessionId !== jarvisChatSessionId) {''',
        '''  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  deleteChatAutoSpeakPreference(sessionId);

  if (sessionId !== jarvisChatSessionId) {''',
        "deleted chat voice cleanup",
    )
    frontend = replace_once(
        frontend,
        '''checkHealth();
loadSettings();
openChat(jarvisChatSessionId);''',
        '''checkHealth();
loadSettings().finally(() => openChat(jarvisChatSessionId));''',
        "settings-before-chat initialization",
    )

    activity_start = frontend.find("  let notificationSignature = null;", frontend.find('<script id="zbrano-v01251-semantic-tab-activity">'))
    activity_end_marker = "  setInterval(checkNotificationActivity, 15000);"
    activity_end = frontend.find(activity_end_marker, activity_start)
    if activity_start < 0 or activity_end < 0:
        raise RuntimeError("ZBRANO v0.12.53 could not locate notification-only activity polling")
    activity_end += len(activity_end_marker)
    revision_polling = '''  let activityRevisions = null;
  const activityTargets = {
    chat: ["#chat-tab"],
    files: ["#files-tab"],
    plugins: ["#plugins-tab"],
    automations: ["#automations-tab", '[data-auto-view="library"]'],
    notifications: ["#automations-tab", '[data-auto-view="notifications"]', '[data-notification-view="logs"]'],
    settings: ["#settings-tab"],
    developer: ["#developer-tab"],
  };

  async function checkSemanticActivity() {
    try {
      const response = await nativeFetch("api/tab-activity", {cache:"no-store"});
      if (!response.ok) return;
      const payload = await response.json();
      const revisions = payload.revisions || {};
      if (activityRevisions !== null) {
        for (const [name, revision] of Object.entries(revisions)) {
          if (activityRevisions[name] === revision) continue;
          for (const selector of activityTargets[name] || []) markIfUnseen(document.querySelector(selector));
        }
      }
      activityRevisions = revisions;
    } catch (_) {}
  }

  checkSemanticActivity();
  setInterval(checkSemanticActivity, 10000);'''
    frontend = frontend[:activity_start] + revision_polling + frontend[activity_end:]

    new_chat_start = frontend.find("async function createNewChat() {")
    new_chat_end = frontend.find("\nasync function deleteChat(", new_chat_start)
    if new_chat_start < 0 or new_chat_end < 0:
        raise RuntimeError("ZBRANO v0.12.53 could not locate New Chat lifecycle")
    new_chat_block = frontend[new_chat_start:new_chat_end]
    reset_marker = '''  stopButton.disabled = true;
  showPanel("chat");'''
    reset_replacement = '''  stopButton.disabled = true;
  resetToolTimeline();
  if (responseTimerId) window.clearInterval(responseTimerId);
  responseTimerId = null;
  responseStartedAt = null;
  firstResponseSeconds = null;
  aiActivity.hidden = true;
  aiActivityLabel.textContent = "";
  aiResponseTimer.textContent = "";
  showPanel("chat");'''
    if new_chat_block.count(reset_marker) != 1:
        raise RuntimeError("ZBRANO v0.12.53 could not locate New Chat activity reset point")
    new_chat_block = new_chat_block.replace(reset_marker, reset_replacement, 1)
    frontend = frontend[:new_chat_start] + new_chat_block + frontend[new_chat_end:]

    backend = backend.replace('version="0.12.52"', 'version="0.12.53"')
    backend = backend.replace('"version": "0.12.52"', '"version": "0.12.53"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.52"', '"X-ZBRANO-Frontend-Version": "0.12.53"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.52"', '"name": "ZBRANO Developer Mode", "version": "0.12.53"')
    frontend = frontend.replace("HUD 0.12.52", "HUD 0.12.53")

    for marker in (
        'version="0.12.53"',
        '@app.put("/api/chat/{session_id}/voice")',
        '"auto_speak": CHAT_SESSION_META.get(session_id, {}).get("auto_speak")',
        '@app.get("/api/tab-activity")',
        '"automations": _tab_activity_value_revision({',
        '"last_observed_state", "last_triggered_at", "trigger_count", "updated_at", "status"',
        'service_domain = "telegram_bot" if channel["platform"] == "telegram" else "notify"',
    ):
        require(backend, marker, marker)
    for marker in (
        "HUD 0.12.53",
        "startBufferedPlayback",
        "bufferedBytes >= 24576",
        "remaining.length >= 56",
        "checkSemanticActivity",
        'nativeFetch("api/tab-activity"',
        "setInterval(checkSemanticActivity, 10000)",
        "resetToolTimeline();",
        "aiActivity.hidden = true;",
        "CHAT_AUTO_SPEAK_KEY",
        "await applyChatAutoSpeakPreference(sessionId, data.auto_speak)",
        "setChatAutoSpeakPreference(jarvisChatSessionId, autoSpeak.checked)",
        "loadSettings().finally(() => openChat(jarvisChatSessionId))",
    ):
        require(frontend, marker, marker)
    if "checkNotificationActivity" in frontend or "let notificationSignature" in frontend:
        raise RuntimeError("ZBRANO v0.12.53 retained obsolete notification-only polling")
    final_new_chat = frontend.split("async function createNewChat() {", 1)[1].split("\nasync function deleteChat(", 1)[0]
    for marker in ("resetToolTimeline();", "responseTimerId = null;", "aiActivity.hidden = true;", 'aiActivityLabel.textContent = "";'):
        if marker not in final_new_chat:
            raise RuntimeError(f"ZBRANO v0.12.53 New Chat reset missing: {marker}")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
