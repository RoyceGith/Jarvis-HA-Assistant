const zbranoInspectionSession =
  new URLSearchParams(window.location.search).get("zbrano_inspection") === "1";
let jarvisChatSessionId = zbranoInspectionSession
  ? "zbrano-playwright-inspection"
  : localStorage.getItem("jarvis_chat_session_id") ||
    (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`);
if (!zbranoInspectionSession) {
  localStorage.setItem("jarvis_chat_session_id", jarvisChatSessionId);
}

const messages = document.getElementById("messages");
const form = document.getElementById("chat-form");
const input = document.getElementById("message");
const health = document.getElementById("health");
const stopButton = document.getElementById("stop-button");
const aiActivity = document.getElementById("ai-activity");
const aiActivityLabel = document.getElementById("ai-activity-label");
const aiResponseTimer = document.getElementById("ai-response-timer");
const toolTimeline = document.getElementById("tool-timeline");
const toolActivities = new Map();
const sendButton = document.getElementById("send-button");
const micButton = document.getElementById("mic-button");
const micLabel = document.getElementById("mic-label");
const voiceState = document.getElementById("voice-state");
const voiceRailState = document.getElementById("voice-rail-state");
const autoSpeak = document.getElementById("auto-speak");
const speechProvider = document.getElementById("speech-provider");
const voiceSelect = document.getElementById("voice-select");
const agentModel = document.getElementById("agent-model");
const reasoningEffort = document.getElementById("reasoning-effort");
const chatList = document.getElementById("chat-list");
const newChatButton = document.getElementById("new-chat-button");

const VOICE_SETTINGS_KEY = "jarvis_voice_settings_v1";
const CHAT_AUTO_SPEAK_KEY = "zbrano_chat_auto_speak_v1";
let speechPlaybackRate=1;
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
let mediaRecorder = null;
let microphoneStream = null;
let recordingChunks = [];
let recordingTimer = null;
let activeAudio = null;
let activeAudioUrl = null;
let speechAbortController = null;
let speechQueue = [];
let speechQueueRunning = false;
let speechPrefetch = null;
let speechPrefetchAbortController = null;
let activeSpeechText = "";
let hasSavedSpeechProvider = false;
let agentControlsLoaded = false;

function addAgentModelOption(modelId) {
  const cleanId = String(modelId || "").trim();
  if (!cleanId || [...agentModel.options].some(option => option.value === cleanId)) return;
  const option = document.createElement("option");
  option.value = cleanId;
  option.textContent = cleanId;
  agentModel.appendChild(option);
}

async function loadAgentControls(preferences = null) {
  try {
    const response = await fetch("api/models");
    const data = await response.json();
    const selectedModel = preferences?.agent_model || data.selected_model || "gpt-5-mini";
    for (const modelId of data.models || []) addAgentModelOption(modelId);
    addAgentModelOption(selectedModel);
    agentModel.value = selectedModel;
    reasoningEffort.value = preferences?.reasoning_effort || data.reasoning_effort || "medium";
    agentControlsLoaded = true;
  } catch {
    const selectedModel = preferences?.agent_model || "gpt-5-mini";
    addAgentModelOption(selectedModel);
    agentModel.value = selectedModel;
    reasoningEffort.value = preferences?.reasoning_effort || "medium";
  }
}

async function saveAgentControls() {
  if (!agentControlsLoaded) return;
  const response = await fetch("api/agent/settings", {
    method: "PUT",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({agent_model: agentModel.value, reasoning_effort: reasoningEffort.value}),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    setVoiceState("AGENT SETTINGS ERROR", data.detail || `HTTP ${response.status}`);
    return;
  }
  jarvisPreferences = {...jarvisPreferences, ...(data.preferences || {})};
  setVoiceState("AGENT READY");
}

agentModel.addEventListener("change", saveAgentControls);
reasoningEffort.addEventListener("change", saveAgentControls);

try {
  const voiceSettings = JSON.parse(localStorage.getItem(VOICE_SETTINGS_KEY) || "{}");
  if ([...speechProvider.options].some(option => option.value === voiceSettings.provider)) {
    speechProvider.value = voiceSettings.provider;
    hasSavedSpeechProvider = true;
  }
  if ([...voiceSelect.options].some(option => option.value === voiceSettings.voice)) {
    voiceSelect.value = voiceSettings.voice;
  }
  const savedSpeed=Number(voiceSettings.speed);if(Number.isFinite(savedSpeed))speechPlaybackRate=Math.min(1.4,Math.max(.8,savedSpeed));
} catch {}

function saveVoiceSettings() {
  localStorage.setItem(VOICE_SETTINGS_KEY, JSON.stringify({
    autoSpeak: settingsAutoSpeak.checked,
    provider: speechProvider.value,
    voice: voiceSelect.value,
    speed: speechPlaybackRate,
  }));
}

autoSpeak.addEventListener("change", () => {
  setChatAutoSpeakPreference(jarvisChatSessionId, autoSpeak.checked);
});
speechProvider.addEventListener("change", () => {
  updateVoiceProviderControls();
  saveVoiceSettings();
});
voiceSelect.addEventListener("change", saveVoiceSettings);

function updateVoiceProviderControls(elevenLabsVoiceName = "ZBRANO") {
  const elevenLabs = speechProvider.value === "elevenlabs";
  let configuredOption = voiceSelect.querySelector('option[value="__elevenlabs__"]');
  if (!configuredOption) {
    configuredOption = document.createElement("option");
    configuredOption.value = "__elevenlabs__";
    voiceSelect.append(configuredOption);
  }
  configuredOption.textContent = `${elevenLabsVoiceName} (ElevenLabs)`;
  configuredOption.hidden = !elevenLabs;
  if (elevenLabs) voiceSelect.value = "__elevenlabs__";
  else if (voiceSelect.value === "__elevenlabs__") voiceSelect.value = "cedar";
  voiceSelect.disabled = elevenLabs;
}

function setVoiceState(state, detail = "") {
  const text = detail ? `${state} · ${detail}` : state;
  voiceState.textContent = text;
  if (voiceRailState) voiceRailState.textContent = state;
}

function cleanupActiveAudio(nextState = "VOICE READY") {
  activeAudio = null;
  activeSpeechText = "";
  if (activeAudioUrl) URL.revokeObjectURL(activeAudioUrl);
  activeAudioUrl = null;
  if (!activeRequest && !mediaRecorder) stopButton.disabled = true;
  setVoiceState(nextState);
}

function stopAudioPlayback(nextState = "VOICE READY") {
  if (speechAbortController) speechAbortController.abort();
  speechAbortController = null;
  if (speechPrefetchAbortController) speechPrefetchAbortController.abort();
  speechPrefetchAbortController = null;
  speechPrefetch = null;
  speechQueue = [];
  speechQueueRunning = false;
  if (activeAudio) {
    activeAudio.pause();
    activeAudio.currentTime = 0;
  }
  cleanupActiveAudio(nextState);
}

function isQuietHours() {
  if (!jarvisPreferences.quiet_hours_enabled) return false;
  const now = new Date();
  const current = now.getHours() * 60 + now.getMinutes();
  const [startHour, startMinute] = String(jarvisPreferences.quiet_hours_start || "22:00").split(":").map(Number);
  const [endHour, endMinute] = String(jarvisPreferences.quiet_hours_end || "07:00").split(":").map(Number);
  const start = startHour * 60 + startMinute;
  const end = endHour * 60 + endMinute;
  return start <= end ? current >= start && current < end : current >= start || current < end;
}

function canSpeakNow(force = false) {
  return force || (autoSpeak.checked && !isQuietHours());
}

function waitForAudioEnd(audio) {
  return new Promise(resolve => {
    const finish = () => resolve();
    audio.addEventListener("ended", finish, {once: true});
    audio.addEventListener("error", finish, {once: true});
    audio.addEventListener("pause", () => {
      if (audio.currentTime === 0) finish();
    }, {once: true});
  });
}

function applySpeechPlaybackSettings(audio){
  const rate=speechPlaybackRate;audio.volume=Number(jarvisPreferences.voice_volume??.9);audio.defaultPlaybackRate=rate;audio.playbackRate=rate;audio.preservesPitch=true;
  audio.addEventListener("loadedmetadata",()=>{audio.defaultPlaybackRate=rate;audio.playbackRate=rate},{once:true});
}

async function playSpeechText(text, force = false, prefetchedBlob = null) {
  if ((!force && (!autoSpeak.checked || isQuietHours())) || !text.trim()) {
    if (!force && isQuietHours()) setVoiceState("QUIET HOURS");
    return;
  }
  const speechController = new AbortController();
  activeSpeechText=String(text||"");
  speechAbortController = speechController;
  stopButton.disabled = false;
  try {
    if (prefetchedBlob) {
      const blob = await prefetchedBlob;
      if (speechController.signal.aborted || !blob) return;
      activeAudioUrl = URL.createObjectURL(blob);
      activeAudio = new Audio(activeAudioUrl);
      applySpeechPlaybackSettings(activeAudio);
      activeAudio.addEventListener("ended", () => cleanupActiveAudio(speechQueue.length ? "SPEECH BUFFERING" : "VOICE READY"));
      activeAudio.addEventListener("error", () => stopAudioPlayback("VOICE PLAYBACK FAILED"));
      setVoiceState("SPEAKING");
      await activeAudio.play();
      await waitForAudioEnd(activeAudio);
      return;
    }

    const response = await fetch("api/voice/speech", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      signal: speechController.signal,
      body: JSON.stringify({
        text: text.slice(0, 4000),
        provider: speechProvider.value,
        voice: voiceSelect.value,
      }),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || `HTTP ${response.status}`);
    }
    const canStreamMp3 = response.body && window.MediaSource &&
      MediaSource.isTypeSupported("audio/mpeg");
    if (!canStreamMp3) {
      const blob = await response.blob();
      activeAudioUrl = URL.createObjectURL(blob);
      activeAudio = new Audio(activeAudioUrl);
      applySpeechPlaybackSettings(activeAudio);
      activeAudio.addEventListener("ended", () => cleanupActiveAudio(speechQueue.length ? "SPEECH BUFFERING" : "VOICE READY"));
      activeAudio.addEventListener("error", () => stopAudioPlayback("VOICE PLAYBACK FAILED"));
      setVoiceState("SPEAKING");
      await activeAudio.play();
      await waitForAudioEnd(activeAudio);
      return;
    }

    const mediaSource = new MediaSource();
    activeAudioUrl = URL.createObjectURL(mediaSource);
    activeAudio = new Audio(activeAudioUrl);
    applySpeechPlaybackSettings(activeAudio);
    activeAudio.addEventListener("ended", () => cleanupActiveAudio(speechQueue.length ? "SPEECH BUFFERING" : "VOICE READY"));
    activeAudio.addEventListener("error", () => stopAudioPlayback("VOICE PLAYBACK FAILED"));
    await new Promise((resolve, reject) => {
      mediaSource.addEventListener("sourceopen", resolve, {once: true});
      mediaSource.addEventListener("error", () => reject(new Error("Audio stream failed")), {once: true});
      activeAudio.load();
    });
    const sourceBuffer = mediaSource.addSourceBuffer("audio/mpeg");
    sourceBuffer.mode = "sequence";
    const reader = response.body.getReader();
    let playbackStarted = false;
    let playbackEnded = null;
    let bufferedBytes = 0;
    const bufferingStarted=performance.now(),playbackBufferTarget=Math.max(1.25,1.35*speechPlaybackRate);
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
      const bufferingSeconds=Math.max(.1,(performance.now()-bufferingStarted)/1000),productionRate=bufferedSeconds/bufferingSeconds;
      if(!playbackStarted&&bufferedSeconds>=playbackBufferTarget&&productionRate>=speechPlaybackRate*1.5)startBufferedPlayback();
    }
    if (!playbackStarted && bufferedBytes > 0) startBufferedPlayback();
    if (mediaSource.readyState === "open" && !sourceBuffer.updating) mediaSource.endOfStream();
    if (playbackEnded) await playbackEnded;
  } catch (error) {
    if (error.name !== "AbortError") setVoiceState("VOICE ERROR", error.message || String(error));
    if (!activeRequest) stopButton.disabled = true;
  } finally {
    if (speechAbortController === speechController) speechAbortController = null;
  }
}

async function speakText(text, force = false) {
  stopAudioPlayback("SPEECH BUFFERING");
  await playSpeechText(text, force);
}

async function fetchSpeechBlob(text, force = false) {
  if ((!force && (!autoSpeak.checked || isQuietHours())) || !text.trim()) return null;
  const controller = new AbortController();
  speechPrefetchAbortController = controller;
  try {
    const response = await fetch("api/voice/speech", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      signal: controller.signal,
      body: JSON.stringify({
        text: text.slice(0, 4000),
        provider: speechProvider.value,
        voice: voiceSelect.value,
      }),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || `HTTP ${response.status}`);
    }
    return await response.blob();
  } catch (error) {
    if (error.name !== "AbortError") setVoiceState("VOICE ERROR", error.message || String(error));
    return null;
  } finally {
    if (speechPrefetchAbortController === controller) speechPrefetchAbortController = null;
  }
}

function primeSpeechPrefetch(force = false) {
  if (speechPrefetch || !speechQueueRunning || !speechQueue.length) return;
  const text = speechQueue[0];
  speechPrefetch = {text, blob: fetchSpeechBlob(text, force)};
}

async function runSpeechQueue(force = false) {
  if (speechQueueRunning) return;
  speechQueueRunning = true;
  try {
    while (speechQueue.length) {
      const nextText = speechQueue.shift();
      const prepared = speechPrefetch?.text === nextText ? speechPrefetch.blob : null;
      speechPrefetch = null;
      primeSpeechPrefetch(force);
      await playSpeechText(nextText, force, prepared);
    }
  } finally {
    speechQueueRunning = false;
    speechPrefetch = null;
  }
}

function speechTextForPlayback(text) {
  return String(text || "")
    .replace(/^#{1,3}\s+/gm, "")
    .replace(/^\s*[-*]\s+/gm, "")
    .replace(/^\s*\d+[.)]\s+/gm, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\s*\n+\s*/g, " ")
    .replace(/[ \t]{2,}/g, " ")
    .trim();
}

function queueSpeech(text, force = false) {
  const spoken = speechTextForPlayback(text);
  if (!spoken || !canSpeakNow(force)) return;
  speechQueue.push(spoken);
  runSpeechQueue(force);
  primeSpeechPrefetch(force);
}

function extractSpeakableChunks(buffer, final = false, fastStart = false) {
  const chunks = [];
  let remaining = buffer;
  // TTS treats every request boundary like punctuation. Keep requests on real
  // sentence or clause boundaries so streamed speech does not invent pauses.
  const sentencePattern = fastStart
    ? /^([\s\S]{18,240}?[.!?](?:["')\]]?)(?:\s+|$))/
    : /^([\s\S]{36,320}?[.!?](?:["')\]]?)(?:\s+|$))/;
  while (true) {
    const match = remaining.match(sentencePattern);
    if (!match) break;
    chunks.push(match[1].trim());
    remaining = remaining.slice(match[0].length);
  }
  if (final && remaining.trim()) {
    chunks.push(remaining.trim());
    remaining = "";
  } else if (!chunks.length && remaining.length >= (fastStart ? 64 : 120)) {
    const clauseLimit = Math.min(fastStart ? 120 : 200, remaining.length);
    const splitAt = Math.max(
      remaining.lastIndexOf(", ", clauseLimit),
      remaining.lastIndexOf("; ", clauseLimit),
      remaining.lastIndexOf(": ", clauseLimit),
      remaining.lastIndexOf(" — ", clauseLimit),
      remaining.lastIndexOf(" – ", clauseLimit)
    );
    if (splitAt >= (fastStart ? 32 : 72)) {
      const delimiterLength = remaining.startsWith(" — ", splitAt) || remaining.startsWith(" – ", splitAt) ? 2 : 1;
      chunks.push(remaining.slice(0, splitAt + delimiterLength).trim());
      remaining = remaining.slice(splitAt + delimiterLength).trimStart();
    }
  }
  if(!chunks.length&&!final&&fastStart&&remaining.length>110){
    const splitAt=remaining.lastIndexOf(" ",88);if(splitAt>=64){chunks.push(remaining.slice(0,splitAt).trim());remaining=remaining.slice(splitAt).trimStart()}
  }
  // Preserve live playback for a rare, very long sentence with no natural
  // boundary. This is intentionally much later than the old 56-character cut.
  if (!chunks.length && !final && remaining.length > 360) {
    const splitAt = remaining.lastIndexOf(" ", 300);
    if (splitAt >= 220) {
      chunks.push(remaining.slice(0, splitAt).trim());
      remaining = remaining.slice(splitAt).trimStart();
    }
  }
  return {chunks, remaining};
}

function cleanupMicrophone() {
  if (recordingTimer) window.clearTimeout(recordingTimer);
  recordingTimer = null;
  if (microphoneStream) microphoneStream.getTracks().forEach(track => track.stop());
  microphoneStream = null;
  mediaRecorder = null;
  micButton.classList.remove("listening");
  micLabel.textContent = "Talk";
  micButton.setAttribute("aria-label", "Start microphone");
}

function recordingMimeType() {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
  return candidates.find(type => window.MediaRecorder?.isTypeSupported(type)) || "";
}

async function transcribeRecording(blob) {
  setVoiceState("TRANSCRIBING");
  micButton.disabled = true;
  try {
    const extension = blob.type.includes("mp4") ? "m4a" : "webm";
    const formData = new FormData();
    formData.append("audio", blob, `zbrano-recording.${extension}`);
    const response = await fetch("api/voice/transcribe", {method: "POST", body: formData});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    input.value = data.text || "";
    setVoiceState("PROCESSING");
    if (input.value.trim()) form.requestSubmit();
  } catch (error) {
    setVoiceState("VOICE ERROR", error.message || String(error));
  } finally {
    micButton.disabled = false;
  }
}

async function startRecording() {
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    setVoiceState("MIC UNAVAILABLE", "use HTTPS and a supported browser");
    return;
  }
  stopAudioPlayback("MIC REQUEST");
  try {
    microphoneStream = await navigator.mediaDevices.getUserMedia({
      audio: {echoCancellation: true, noiseSuppression: true, autoGainControl: true},
    });
    recordingChunks = [];
    const mimeType = recordingMimeType();
    mediaRecorder = new MediaRecorder(microphoneStream, mimeType ? {mimeType} : undefined);
    mediaRecorder.addEventListener("dataavailable", event => {
      if (event.data.size) recordingChunks.push(event.data);
    });
    mediaRecorder.addEventListener("stop", () => {
      const blob = new Blob(recordingChunks, {type: mediaRecorder?.mimeType || mimeType || "audio/webm"});
      cleanupMicrophone();
      if (blob.size) transcribeRecording(blob);
      else setVoiceState("VOICE ERROR", "empty recording");
    }, {once: true});
    mediaRecorder.start(250);
    micButton.classList.add("listening");
    micLabel.textContent = "Done";
    micButton.setAttribute("aria-label", "Stop microphone and send");
    setVoiceState("LISTENING", "tap Done to send");
    recordingTimer = window.setTimeout(stopRecording, 60000);
  } catch (error) {
    cleanupMicrophone();
    const permissionMessage = error.name === "NotAllowedError"
      ? "microphone permission denied"
      : (error.message || String(error));
    setVoiceState("MIC ERROR", permissionMessage);
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
}

function interruptActiveResponseForVoice(){
  const request=activeRequest;
  if(request){
    request.stopped=true;const {socket,jarvisMessage}=request;
    if(socket.readyState===WebSocket.OPEN)socket.send(JSON.stringify({type:"stop"}));else socket.close();
    const existing=jarvisMessage.textContent.trim();renderMessageContent(jarvisMessage,existing&&existing!=="Connectingâ€¦"?`${existing}\n\n[Interrupted for voice]`:"Interrupted for voice.");
    activeRequest=null;finishOpenToolActivities("failed");finishResponseActivity("Stopped");input.disabled=false;sendButton.disabled=false;stopButton.disabled=true;
  }
  stopAudioPlayback("VOICE INTERRUPTED");
}

micButton.addEventListener("click", () => {
  if (mediaRecorder && mediaRecorder.state !== "inactive") stopRecording();
  else{if(activeRequest)interruptActiveResponseForVoice();startRecording()}
});

const PROMPT_HISTORY_KEY = "jarvis_prompt_history_v1";
const PROMPT_HISTORY_LIMIT = 100;
let promptHistory = [];
try {
  const storedHistory = JSON.parse(localStorage.getItem(PROMPT_HISTORY_KEY) || "[]");
  if (Array.isArray(storedHistory)) {
    promptHistory = storedHistory.filter(item => typeof item === "string" && item.trim()).slice(-PROMPT_HISTORY_LIMIT);
  }
} catch {
  promptHistory = [];
}
let promptHistoryIndex = promptHistory.length;
let promptDraft = "";
let activeRequest = null;
let responseTimerId = null;
let responseStartedAt = 0;
let firstResponseSeconds = null;
let responseActivityBaseLabel = "Working";
let responseActivityUpdatedAt = 0;

function formatResponseTime(seconds) {
  const safe = Math.max(0, Number(seconds) || 0);
  const minutes = Math.floor(safe / 60);
  return `${String(minutes).padStart(2, "0")}:${(safe % 60).toFixed(1).padStart(4, "0")}`;
}

function updateResponseTimer() {
  if (!responseStartedAt) return;
  const elapsed = (performance.now() - responseStartedAt) / 1000;
  aiResponseTimer.textContent = firstResponseSeconds === null
    ? formatResponseTime(elapsed)
    : `first ${firstResponseSeconds.toFixed(1)}s · total ${formatResponseTime(elapsed)}`;
  const quietSeconds = responseActivityUpdatedAt
    ? (performance.now() - responseActivityUpdatedAt) / 1000
    : 0;
  if (firstResponseSeconds === null && quietSeconds >= 20) {
    const suffix = quietSeconds >= 60
      ? "taking longer than expected; you can stop safely"
      : "still working";
    aiActivityLabel.textContent = `${responseActivityBaseLabel} · ${suffix}`;
  }
}

function startResponseActivity(label = "Thinking") {
  if (responseTimerId) window.clearInterval(responseTimerId);
  responseStartedAt = performance.now();
  firstResponseSeconds = null;
  responseActivityBaseLabel = label || "Thinking";
  responseActivityUpdatedAt = performance.now();
  aiActivity.hidden = false;
  aiActivityLabel.textContent = responseActivityBaseLabel;
  updateResponseTimer();
  responseTimerId = window.setInterval(() => { updateResponseTimer(); updateToolTimelineClock(); }, 100);
}

function setResponseActivity(label) {
  if (!label) return;
  responseActivityBaseLabel = label;
  responseActivityUpdatedAt = performance.now();
  aiActivityLabel.textContent = label;
}

function markFirstResponse() {
  if (firstResponseSeconds !== null || !responseStartedAt) return;
  firstResponseSeconds = (performance.now() - responseStartedAt) / 1000;
  updateResponseTimer();
}

function finishResponseActivity(label = "Completed") {
  if (responseTimerId) window.clearInterval(responseTimerId);
  responseTimerId = null;
  updateResponseTimer();
  setResponseActivity(label);
  if (label === "Completed") window.dispatchEvent(new CustomEvent("zbrano-response-finished"));
}


function formatToolElapsed(milliseconds) {
  const seconds = Math.max(0, milliseconds) / 1000;
  return seconds < 10 ? `${seconds.toFixed(1)}s` : `${Math.round(seconds)}s`;
}

function setPluginToolActive(pluginId, active) {
  if (!pluginId) return;
  const button = [...document.querySelectorAll("[data-composer-plugin]")]
    .find(item => item.dataset.composerPlugin === pluginId);
  button?.classList.toggle("tool-active", active);
}

function resetToolTimeline() {
  for (const activity of toolActivities.values()) setPluginToolActive(activity.pluginId, false);
  toolActivities.clear();
  toolTimeline.replaceChildren();
  toolTimeline.hidden = true;
}

function updateToolTimelineClock() {
  const now = performance.now();
  for (const activity of toolActivities.values()) {
    const elapsed = (activity.finishedAt || now) - activity.startedAt;
    activity.time.textContent = formatToolElapsed(elapsed);
  }
}

function applyToolActivity(eventData) {
  const id = String(
    eventData.provider === "home_assistant"
      ? "local-home-assistant"
      : eventData.id || `${eventData.provider || "tool"}-${eventData.label || "activity"}`
  );
  const state = String(eventData.state || "started");
  let activity = toolActivities.get(id);
  if (!activity) {
    const item = document.createElement("span");
    item.className = "tool-activity";
    const dot = document.createElement("span");
    dot.className = "tool-activity-dot";
    dot.setAttribute("aria-hidden", "true");
    const label = document.createElement("span");
    label.className = "tool-activity-label";
    const time = document.createElement("time");
    time.className = "tool-activity-time";
    item.append(dot, label, time);
    activity = {item, label, time, startedAt: performance.now(), finishedAt: null, pluginId: ""};
    toolActivities.set(id, activity);
    toolTimeline.append(item);
    while (toolTimeline.children.length > 8) toolTimeline.firstElementChild?.remove();
  }
  if (activity.pluginId && activity.pluginId !== eventData.plugin_id) setPluginToolActive(activity.pluginId, false);
  activity.pluginId = String(eventData.plugin_id || "");
  activity.label.textContent = String(eventData.label || "Tool activity");
  activity.item.dataset.state = state;
  activity.finishedAt = ["completed", "failed"].includes(state) ? performance.now() : null;
  const active = state === "started";
  setPluginToolActive(activity.pluginId, active);
  const stateLabel = state === "waiting_approval" ? "approval required" : state;
  activity.item.title = `${activity.label.textContent} · ${stateLabel}`;
  toolTimeline.hidden = false;
  updateToolTimelineClock();
}

function finishOpenToolActivities(state = "completed") {
  for (const activity of toolActivities.values()) {
    if (activity.item.dataset.state !== "started") continue;
    activity.item.dataset.state = state;
    activity.finishedAt = performance.now();
    setPluginToolActive(activity.pluginId, false);
  }
  updateToolTimelineClock();
}

function resizeComposer() {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 192)}px`;
}

input.addEventListener("input", resizeComposer);
resizeComposer();

function rememberPrompt(prompt) {
  if (promptHistory[promptHistory.length - 1] !== prompt) promptHistory.push(prompt);
  promptHistory = promptHistory.slice(-PROMPT_HISTORY_LIMIT);
  localStorage.setItem(PROMPT_HISTORY_KEY, JSON.stringify(promptHistory));
  promptHistoryIndex = promptHistory.length;
  promptDraft = "";
}

input.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    form.requestSubmit();
    return;
  }
  if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
  if (input.value.includes("\n") || !promptHistory.length) return;
  event.preventDefault();

  if (event.key === "ArrowUp") {
    if (promptHistoryIndex === promptHistory.length) promptDraft = input.value;
    promptHistoryIndex = Math.max(0, promptHistoryIndex - 1);
    input.value = promptHistory[promptHistoryIndex];
  } else {
    promptHistoryIndex = Math.min(promptHistory.length, promptHistoryIndex + 1);
    input.value = promptHistoryIndex === promptHistory.length
      ? promptDraft
      : promptHistory[promptHistoryIndex];
  }
  input.setSelectionRange(input.value.length, input.value.length);
  resizeComposer();
});

const chatTab = document.getElementById("chat-tab");
const entitiesTab = document.getElementById("entities-tab");
const settingsTab = document.getElementById("settings-tab");
const chatPanel = document.getElementById("chat-panel");
const entitiesPanel = document.getElementById("entities-panel");
const settingsPanel = document.getElementById("settings-panel");
const generalInstructions = document.getElementById("general-instructions");
const saveSettings = document.getElementById("save-settings");
const settingsSaveState = document.getElementById("settings-save-state");
const themeInputs = [...document.querySelectorAll('input[name="theme"]')];
const elevenLabsVoiceInputs = {
  stability: document.getElementById("elevenlabs-stability"),
  similarity: document.getElementById("elevenlabs-similarity"),
  style: document.getElementById("elevenlabs-style"),
  speed: document.getElementById("elevenlabs-speed"),
};
const resetVoiceSettings = document.getElementById("reset-voice-settings");
const testVoice = document.getElementById("test-voice");
const elevenLabsModel = document.getElementById("elevenlabs-model");
const elevenLabsSpeakerBoost = document.getElementById("elevenlabs-speaker-boost");
const settingsAutoSpeak = document.getElementById("settings-auto-speak");
const responseLength = document.getElementById("response-length");
const confirmationStrictness = document.getElementById("confirmation-strictness");
const webSearchMode = document.getElementById("web-search-mode");
const webSearchEnabled = document.getElementById("web-search-enabled");
const webSearchContextSize = document.getElementById("web-search-context-size");
const contextMessages = document.getElementById("context-messages");
const retentionDays = document.getElementById("retention-days");
const fastMemoryEnabled = document.getElementById("fast-memory-enabled");
const fastMemoryAutoCapture = document.getElementById("fast-memory-auto-capture");
const fastMemoryContextItems = document.getElementById("fast-memory-context-items");
const preferredLanguage = document.getElementById("preferred-language");
const pronunciationDictionary = document.getElementById("pronunciation-dictionary");
const reducedMotionSetting = document.getElementById("reduced-motion");
const releaseMemoryAutoSync = document.getElementById("release-memory-auto-sync");
const releaseMemorySyncStatus = document.getElementById("release-memory-sync-status");
const releaseMemorySyncRetry = document.getElementById("release-memory-sync-retry");
let releaseMemorySyncPollTimer = 0;
const neuralStyle = document.getElementById("neural-style");
const neuralScale = document.getElementById("neural-scale");
const neuralNodeSize = document.getElementById("neural-node-size");
const neuralOpacity = document.getElementById("neural-opacity");
const neuralScaleValue = document.getElementById("neural-scale-value");
const neuralNodeSizeValue = document.getElementById("neural-node-size-value");
const neuralOpacityValue = document.getElementById("neural-opacity-value");
const textSize = document.getElementById("text-size");
const interfaceDensity = document.getElementById("interface-density");
const quietHoursEnabled = document.getElementById("quiet-hours-enabled");
const quietHoursStart = document.getElementById("quiet-hours-start");
const quietHoursEnd = document.getElementById("quiet-hours-end");
const voiceVolume = document.getElementById("voice-volume");
const voiceVolumeValue = document.getElementById("voice-volume-value");
const voiceSpeed = document.getElementById("voice-speed");
const voiceSpeedValue = document.getElementById("voice-speed-value");
const exportBackup = document.getElementById("export-backup");
const restoreBackup = document.getElementById("restore-backup");
const clearAllChats = document.getElementById("clear-all-chats");
let elevenLabsVoiceDefaults = {stability: 0.55, similarity: 0.75, style: 0.15, speed: 0.96};
let jarvisPreferences = {};
const THEME_KEY = "jarvis_theme_v1";

function setElevenLabsVoiceControls(settings) {
  for (const [name, input] of Object.entries(elevenLabsVoiceInputs)) {
    const value = Number(settings?.[name]);
    if (Number.isFinite(value)) input.value = String(value);
    document.getElementById(`${input.id}-value`).textContent = Number(input.value).toFixed(2);
  }
}

for (const input of Object.values(elevenLabsVoiceInputs)) {
  input.addEventListener("input", () => {
    document.getElementById(`${input.id}-value`).textContent = Number(input.value).toFixed(2);
  });
}

resetVoiceSettings.addEventListener("click", () => {
  setElevenLabsVoiceControls(elevenLabsVoiceDefaults);
  settingsSaveState.textContent = "Defaults restored locally. Select Save Settings to apply them.";
});

function applyTheme(theme, persist = true) {
  const nextTheme = ["dark", "light", "gray"].includes(theme) ? theme : "dark";
  document.documentElement.dataset.theme = nextTheme;
  for (const option of themeInputs) option.checked = option.value === nextTheme;
  if (persist) localStorage.setItem(THEME_KEY, nextTheme);
  window.dispatchEvent(new CustomEvent("jarvis-theme-change", {detail: {theme: nextTheme}}));
}

function applyInterfacePreferences(preferences = {}) {
  const theme = preferences.theme || document.documentElement.dataset.theme || "dark";
  applyTheme(theme);
  document.documentElement.dataset.textSize = preferences.text_size || "medium";
  document.documentElement.dataset.density = preferences.interface_density || "comfortable";
  const style = ["constellation", "mesh", "orbital", "minimal"].includes(preferences.neural_style)
    ? preferences.neural_style : "constellation";
  const scale = Math.min(1.4, Math.max(.7, Number(preferences.neural_scale) || 1));
  const nodeSize = Math.min(1.6, Math.max(.6, Number(preferences.neural_node_size) || 1));
  const opacity = Math.min(.8, Math.max(.05, Number(preferences.neural_opacity) || .38));
  document.documentElement.dataset.neuralStyle = style;
  document.documentElement.dataset.neuralScale = String(scale);
  document.documentElement.dataset.neuralNodeSize = String(nodeSize);
  document.documentElement.style.setProperty("--neural-opacity", String(opacity));
  if (neuralStyle) neuralStyle.value = style;
  if (neuralScale) neuralScale.value = String(scale);
  if (neuralNodeSize) neuralNodeSize.value = String(nodeSize);
  if (neuralOpacity) neuralOpacity.value = String(opacity);
  if (neuralScaleValue) neuralScaleValue.textContent = `${Math.round(scale * 100)}%`;
  if (neuralNodeSizeValue) neuralNodeSizeValue.textContent = `${Math.round(nodeSize * 100)}%`;
  if (neuralOpacityValue) neuralOpacityValue.textContent = `${Math.round(opacity * 100)}%`;
  document.documentElement.dataset.reducedMotion = String(Boolean(preferences.reduced_motion));
  window.dispatchEvent(new CustomEvent("zbrano-neural-change"));
}

for (const [control, output] of [
  [neuralScale, neuralScaleValue],
  [neuralNodeSize, neuralNodeSizeValue],
  [neuralOpacity, neuralOpacityValue],
]) {
  control.addEventListener("input", () => {
    output.textContent = `${Math.round(Number(control.value) * 100)}%`;
    applyInterfacePreferences({
      ...jarvisPreferences,
      neural_style: neuralStyle.value,
      neural_scale: Number(neuralScale.value),
      neural_node_size: Number(neuralNodeSize.value),
      neural_opacity: Number(neuralOpacity.value),
    });
  });
}
neuralStyle.addEventListener("change", () => applyInterfacePreferences({
  ...jarvisPreferences,
  neural_style: neuralStyle.value,
  neural_scale: Number(neuralScale.value),
  neural_node_size: Number(neuralNodeSize.value),
  neural_opacity: Number(neuralOpacity.value),
}));

voiceVolume.addEventListener("input", () => {
  voiceVolumeValue.textContent = `${Math.round(Number(voiceVolume.value) * 100)}%`;
  if (activeAudio) activeAudio.volume = Number(voiceVolume.value);
});

voiceSpeed.value=String(speechPlaybackRate);voiceSpeedValue.textContent=`${speechPlaybackRate.toFixed(2)}×`;
voiceSpeed.addEventListener("input",()=>{speechPlaybackRate=Math.min(1.4,Math.max(.8,Number(voiceSpeed.value)||1));voiceSpeedValue.textContent=`${speechPlaybackRate.toFixed(2)}×`;saveVoiceSettings()});

testVoice.addEventListener("click", () => speakText("ZBRANO voice systems online. How may I assist?", true));
settingsAutoSpeak.addEventListener("change", saveVoiceSettings);

exportBackup.addEventListener("click", () => {
  const link = document.createElement("a");
  link.href = "api/settings/backup";
  link.download = "zbrano-backup.json";
  link.click();
});

restoreBackup.addEventListener("change", async () => {
  const file = restoreBackup.files?.[0];
  if (!file) return;
  settingsSaveState.textContent = "Restoring backup…";
  try {
    const backup = JSON.parse(await file.text());
    const response = await fetch("api/settings/restore", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({backup}),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    await loadSettings();
    await refreshChatList();
    settingsSaveState.textContent = `Backup restored · ${data.chat_count} chats available.`;
  } catch (error) {
    settingsSaveState.textContent = `Restore failed: ${error.message || error}`;
  } finally {
    restoreBackup.value = "";
  }
});

clearAllChats.addEventListener("click", async () => {
  if (!window.confirm("Clear every saved ZBRANO conversation? This cannot be undone without a backup.")) return;
  const response = await fetch("api/chats", {method: "DELETE"});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    settingsSaveState.textContent = `Clear failed: ${data.detail || `HTTP ${response.status}`}`;
    return;
  }
  await createNewChat();
  settingsSaveState.textContent = `Cleared ${data.deleted || 0} saved chats.`;
});

applyTheme(document.documentElement.dataset.theme, false);
for (const option of themeInputs) {
  option.addEventListener("change", () => {
    if (option.checked) applyTheme(option.value);
  });
}

const entitySearch = document.getElementById("entity-search");
const domainFilter = document.getElementById("domain-filter");
const refreshEntities = document.getElementById("refresh-entities");
const exportEntities = document.getElementById("export-entities");
const saveMemoryDraft = document.getElementById("save-memory-draft");
const showApproved = document.getElementById("show-approved");
const entityRows = document.getElementById("entity-rows");
const entitySummary = document.getElementById("entity-summary");

let entityInventory = [];
let inventoryLoaded = false;
const entityReview = new Map();
const ENTITY_ALIAS_BACKUP_KEY = "jarvis_entity_aliases_v1";
let entityAliasBackup = {};
try {
  const storedAliases = JSON.parse(localStorage.getItem(ENTITY_ALIAS_BACKUP_KEY) || "{}");
  if (storedAliases && typeof storedAliases === "object" && !Array.isArray(storedAliases)) {
    entityAliasBackup = storedAliases;
  }
} catch {
  entityAliasBackup = {};
}

function backupEntityAliases(entityId, aliasesText) {
  const normalized = String(aliasesText || "");
  entityAliasBackup[entityId] = normalized;
  localStorage.setItem(ENTITY_ALIAS_BACKUP_KEY, JSON.stringify(entityAliasBackup));
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderInlineMarkdown(text) {
  return escapeHtml(text)
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

function renderMarkdownText(text) {
  const lines = String(text || "").replace(/\r\n/g, "\n").split("\n");
  const html = [];
  let paragraph = [];
  let listType = "";

  function closeParagraph() {
    if (!paragraph.length) return;
    html.push(`<p>${paragraph.map(renderInlineMarkdown).join("<br>")}</p>`);
    paragraph = [];
  }

  function closeList() {
    if (!listType) return;
    html.push(`</${listType}>`);
    listType = "";
  }

  function openList(nextType) {
    closeParagraph();
    if (listType === nextType) return;
    closeList();
    listType = nextType;
    html.push(`<${listType}>`);
  }

  for (let lineIndex = 0; lineIndex < lines.length; lineIndex += 1) {
    const line = lines[lineIndex];
    const trimmed = line.trim();
    if (!trimmed) {
      closeParagraph();
      closeList();
      continue;
    }

    const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      closeParagraph();
      closeList();
      const headingTag = heading[1].length === 1 ? "h2" : heading[1].length === 2 ? "h3" : "h4";
      html.push(`<${headingTag}>${renderInlineMarkdown(heading[2])}</${headingTag}>`);
      continue;
    }

    const standaloneBold = trimmed.match(/^\*\*([^*]+)\*\*$/);
    if (standaloneBold) {
      closeParagraph();
      closeList();
      html.push(`<h4>${renderInlineMarkdown(standaloneBold[1])}</h4>`);
      continue;
    }

    const bullet = trimmed.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      openList("ul");
      html.push(`<li>${renderInlineMarkdown(bullet[1])}</li>`);
      continue;
    }

    const numbered = trimmed.match(/^(\d+)[.)]\s+(.+)$/);
    if (numbered) {
      let nextContent = "";
      for (let nextIndex = lineIndex + 1; nextIndex < lines.length; nextIndex += 1) {
        nextContent = lines[nextIndex].trim();
        if (nextContent) break;
      }
      const followedByDetails = /^[-*]\s+/.test(nextContent);
      const looksLikeSectionTitle = followedByDetails && numbered[2].length <= 120;
      if (looksLikeSectionTitle) {
        closeParagraph();
        closeList();
        html.push(`<h3>${renderInlineMarkdown(`${numbered[1]}. ${numbered[2]}`)}</h3>`);
      } else {
        openList("ol");
        html.push(`<li value="${Number(numbered[1])}">${renderInlineMarkdown(numbered[2])}</li>`);
      }
      continue;
    }

    closeList();
    paragraph.push(line);
  }

  closeParagraph();
  closeList();
  return html.join("") || "<p></p>";
}

function renderMessageContent(item, text) {
  item.dataset.rawText = text;
  if (item.classList.contains("jarvis")) {
    item.innerHTML = renderMarkdownText(text);
  } else {
    item.textContent = text;
  }
}

function setNeuronIntensity(intense) {
  document.querySelector(".core-stage")?.classList.toggle("neuron-intense", Boolean(intense));
}

function isNearMessagesBottom(threshold = 72) {
  return messages.scrollHeight - messages.scrollTop - messages.clientHeight <= threshold;
}

function formatAttachmentSize(bytes) {
  const size = Number(bytes) || 0;
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(size < 10240 ? 1 : 0)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function appendMessageAttachments(item, attachments = []) {
  if (!Array.isArray(attachments) || !attachments.length) return;
  const list = document.createElement("div");
  list.className = "message-attachments";
  list.setAttribute("aria-label", `${attachments.length} attached file${attachments.length === 1 ? "" : "s"}`);
  for (const attachment of attachments) {
    const chip = document.createElement("span");
    chip.className = "message-attachment";
    const name = document.createElement("strong");
    name.textContent = `📎 ${attachment.name || "Attached file"}`;
    const metadata = document.createElement("small");
    metadata.textContent = [attachment.mime_type, formatAttachmentSize(attachment.size)].filter(Boolean).join(" · ");
    chip.append(name, metadata);
    list.appendChild(chip);
  }
  item.appendChild(list);
}

function addMessage(text, role, attachments = []) {
  const item = document.createElement("div");
  item.className = `message ${role}`;
  renderMessageContent(item, text);
  appendMessageAttachments(item, attachments);
  messages.appendChild(item);
  messages.scrollTop = messages.scrollHeight;
  return item;
}

function createSessionId() {
  return crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function showChatWelcome() {
  messages.innerHTML = "";
  setNeuronIntensity(true);
  addMessage("ZBRANO intelligence core online.", "jarvis");
}

function updateSessionDisplay() {
  localStorage.setItem("jarvis_chat_session_id", jarvisChatSessionId);
  const sessionFragment = document.getElementById("session-fragment");
  if (sessionFragment) sessionFragment.textContent = jarvisChatSessionId.slice(0, 8).toUpperCase();
}

async function refreshChatList() {
  try {
    const response = await fetch("api/chats");
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    const chats = Array.isArray(data.chats) ? data.chats : [];
    chatList.innerHTML = "";
    for (const chat of chats) {
      const row = document.createElement("div");
      row.className = `chat-list-item${chat.session_id === jarvisChatSessionId ? " active" : ""}`;

      const openButton = document.createElement("button");
      openButton.type = "button";
      openButton.className = "chat-open";
      openButton.textContent = chat.title || "New chat";
      openButton.title = chat.title || "New chat";
      openButton.addEventListener("click", () => openChat(chat.session_id));

      const renameButton = document.createElement("button");
      renameButton.type = "button";
      renameButton.className = "chat-rename";
      renameButton.textContent = "✎";
      renameButton.title = "Rename chat";
      renameButton.setAttribute("aria-label", `Rename ${chat.title || "chat"}`);
      renameButton.addEventListener("click", event => {
        event.stopPropagation();
        beginChatRename(row, openButton, chat, renameButton, deleteButton);
      });

      const deleteButton = document.createElement("button");
      deleteButton.type = "button";
      deleteButton.className = "chat-delete";
      deleteButton.textContent = "×";
      deleteButton.title = "Delete chat";
      deleteButton.setAttribute("aria-label", `Delete ${chat.title || "chat"}`);
      deleteButton.addEventListener("click", async event => {
        event.preventDefault();
        event.stopPropagation();
        try {
          await deleteChat(chat.session_id);
        } catch (error) {
          deleteButton.title = `Delete failed: ${error.message || error}`;
        }
      });

      const actions = document.createElement("span");
      actions.className = "chat-actions";
      actions.append(renameButton, deleteButton);
      row.append(openButton, actions);
      chatList.appendChild(row);
    }
  } catch {
    chatList.innerHTML = '<div class="chat-empty">Chat list unavailable.</div>';
  }
}

async function renameChat(sessionId, title) {
  const response = await fetch(`api/chats/${encodeURIComponent(sessionId)}/title`, {
    method: "PUT",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title}),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  return data.title;
}

function beginChatRename(row, openButton, chat, renameButton, deleteButton) {
  if (row.querySelector(".chat-title-editor")) return;
  const previousTitle = chat.title || "New chat";
  const editor = document.createElement("input");
  editor.className = "chat-title-editor";
  editor.type = "text";
  editor.maxLength = 100;
  editor.value = previousTitle;
  openButton.replaceWith(editor);
  const actionHeight = Math.max(
    renameButton?.getBoundingClientRect().height || 0,
    deleteButton?.getBoundingClientRect().height || 0,
  );
  if (actionHeight > 0) {
    const measuredHeight = `${actionHeight}px`;
    editor.style.setProperty("height", measuredHeight, "important");
    editor.style.setProperty("min-height", measuredHeight, "important");
    editor.style.setProperty("max-height", measuredHeight, "important");
  }
  editor.focus();
  editor.select();
  let finished = false;

  const finish = async save => {
    if (finished) return;
    finished = true;
    const requestedTitle = editor.value.trim();
    if (!save || !requestedTitle) {
      openButton.textContent = previousTitle;
      openButton.title = previousTitle;
      editor.replaceWith(openButton);
      return;
    }
    try {
      const savedTitle = await renameChat(chat.session_id, requestedTitle);
      chat.title = savedTitle;
      openButton.textContent = savedTitle;
      openButton.title = savedTitle;
      editor.replaceWith(openButton);
    } catch (error) {
      finished = false;
      editor.setCustomValidity(error.message || "Rename failed");
      editor.reportValidity();
      editor.focus();
    }
  };

  editor.addEventListener("keydown", event => {
    if (event.key === "Enter") {
      event.preventDefault();
      finish(true);
    } else if (event.key === "Escape") {
      event.preventDefault();
      finish(false);
    }
  });
  editor.addEventListener("blur", () => finish(true));
}

async function openChat(sessionId) {
  if (activeRequest) return;
  chatList.querySelector('.chat-list-item[data-draft="true"]')?.remove();
  try {
    const response = await fetch(`api/chat/history/${encodeURIComponent(sessionId)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    jarvisChatSessionId = sessionId;
    updateSessionDisplay();
    await applyChatAutoSpeakPreference(sessionId, data.auto_speak);
    messages.innerHTML = "";
    const restoredMessages = data.messages || [];
    setNeuronIntensity(restoredMessages.length === 0);
    for (const message of restoredMessages) {
      addMessage(message.content, message.role === "user" ? "user" : "jarvis", message.attachments || []);
    }
    if (!messages.children.length) showChatWelcome();
    await refreshChatList();
    input.focus();
  } catch (error) {
    showChatWelcome();
    addMessage(`Could not restore chat: ${error.message || error}`, "jarvis");
  }
}

function renderDraftChatRow() {
  const existing = chatList.querySelector('.chat-list-item[data-draft="true"]');
  if (existing) existing.remove();
  for (const row of chatList.querySelectorAll('.chat-list-item.active')) {
    row.classList.remove('active');
  }
  const row = document.createElement('div');
  row.className = 'chat-list-item active';
  row.dataset.draft = 'true';
  row.dataset.sessionId = jarvisChatSessionId;
  const open = document.createElement('button');
  open.type = 'button';
  open.className = 'chat-open';
  open.textContent = 'New chat';
  open.setAttribute('aria-current', 'page');
  row.appendChild(open);
  chatList.prepend(row);
}

async function createNewChat() {
  if (activeRequest) {
    activeRequest.stopped = true;
    const staleSocket = activeRequest.socket;
    try {
      if (staleSocket?.readyState === WebSocket.OPEN) {
        staleSocket.send(JSON.stringify({type: "stop"}));
      }
      staleSocket?.close();
    } catch (_) {}
    activeRequest = null;
  }
  stopAudioPlayback("VOICE READY");
  input.disabled = false;
  sendButton.disabled = false;
  micButton.disabled = false;
  stopButton.disabled = true;
  resetToolTimeline();
  if (responseTimerId) window.clearInterval(responseTimerId);
  responseTimerId = null;
  responseStartedAt = null;
  firstResponseSeconds = null;
  aiActivity.hidden = true;
  aiActivityLabel.textContent = "";
  aiResponseTimer.textContent = "";
  showPanel("chat");
  jarvisChatSessionId = createSessionId();
  localStorage.setItem("jarvis_chat_session_id", jarvisChatSessionId);
  updateSessionDisplay();
  renderDraftChatRow();
  showChatWelcome();
  input.value = "";
  input.dispatchEvent(new Event("input", {bubbles: true}));
  if (typeof window.zbranoClearPendingAttachments === "function") {
    window.zbranoClearPendingAttachments();
  }
  const attachmentState = document.getElementById("attachment-state");
  if (attachmentState) attachmentState.textContent = "";
  input.focus();
}

async function deleteChat(sessionId) {
  if (activeRequest && sessionId === jarvisChatSessionId) return;
  const response = await fetch(
    `api/chat/history/${encodeURIComponent(sessionId)}`,
    {method: "DELETE"}
  );
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  deleteChatAutoSpeakPreference(sessionId);

  if (sessionId !== jarvisChatSessionId) {
    await refreshChatList();
    return;
  }

  const listResponse = await fetch("api/chats");
  const listData = await listResponse.json().catch(() => ({}));
  const remaining = Array.isArray(listData.chats) ? listData.chats : [];
  const next = remaining.find(chat => chat.session_id !== sessionId);
  if (next) await openChat(next.session_id);
  else await createNewChat();
}

newChatButton.addEventListener("click", createNewChat);

async function checkHealth() {
  try {
    const response = await fetch("api/health");
    const data = await response.json();
    health.textContent = data.status === "ok" ? `Online · ${data.version}` : "Degraded";
    const providers = data.speech_providers || {};
    for (const option of speechProvider.options) {
      option.disabled = providers[option.value]?.configured === false;
    }
    if (!hasSavedSpeechProvider && providers[data.speech_provider]?.configured) {
      speechProvider.value = data.speech_provider;
    }
    if (providers[speechProvider.value]?.configured === false) {
      const preferred = providers[data.speech_provider]?.configured
        ? data.speech_provider
        : (providers.openai?.configured ? "openai" : "elevenlabs");
      speechProvider.value = preferred;
    }
    updateVoiceProviderControls(providers.elevenlabs?.voice_name || "ZBRANO");
    saveVoiceSettings();
  } catch {
    health.textContent = "Offline";
  }
}

function showPanel(panel) {
  const showChat = panel === "chat";
  const showEntities = panel === "entities";
  const showSettings = panel === "settings";
  const showPlugins = panel === "plugins";
  const showFiles = panel === "files";
  const showAutomations = panel === "automations";
  const showCalendar = panel === "calendar";
  chatPanel.classList.toggle("hidden", !showChat);
  entitiesPanel.classList.toggle("hidden", !showEntities);
  settingsPanel.classList.toggle("hidden", !showSettings);
  pluginsPanel.classList.toggle("hidden", !showPlugins);
  document.getElementById("files-panel")?.classList.toggle("hidden", !showFiles);
  document.getElementById("automations-panel")?.classList.toggle("hidden", !showAutomations);
  document.getElementById("calendar-panel")?.classList.toggle("hidden", !showCalendar);
  chatTab.classList.toggle("active", showChat);
  entitiesTab.classList.toggle("active", showEntities);
  settingsTab.classList.toggle("active", showSettings);
  pluginsTab.classList.toggle("active", showPlugins);
  document.getElementById("files-tab")?.classList.toggle("active", showFiles);
  document.getElementById("automations-tab")?.classList.toggle("active", showAutomations);
  document.getElementById("calendar-tab")?.classList.toggle("active", showCalendar);
}

chatTab.addEventListener("click", () => showPanel("chat"));
entitiesTab.addEventListener("click", async () => {
  showPanel("entities");
  if (!inventoryLoaded) await loadEntities();
});

function renderReleaseSyncStatus(status = {}) {
  const state = String(status.state || "pending");
  const progress = [status.note_progress, status.current_note].filter(Boolean).join(" - ");
  releaseMemorySyncStatus.dataset.state = state;
  const version = status.version ? `v${status.version}` : "current release";
  const detail = status.last_error ? ` · ${status.last_error}` : "";
  releaseMemorySyncStatus.textContent = status.enabled === false
    ? "Automatic release synchronization is disabled."
    : `${version} · ${state}${status.already_present ? " · already recorded" : ""}${detail}`;
  if (progress) releaseMemorySyncStatus.textContent += ` - ${progress}`;
}

async function refreshReleaseSyncStatus() {
  try {
    const response = await fetch("api/release-memory-sync", {cache: "no-store"});
    const status = await response.json();
    if (!response.ok) throw new Error(status.detail || `HTTP ${response.status}`);
    renderReleaseSyncStatus(status);
    window.clearTimeout(releaseMemorySyncPollTimer);
    if (status.task_active || ["pending", "synchronizing", "retrying"].includes(status.state)) {
      releaseMemorySyncPollTimer = window.setTimeout(refreshReleaseSyncStatus, 2500);
    }
  } catch (error) {
    renderReleaseSyncStatus({state: "failed", last_error: error.message || String(error)});
  }
}

releaseMemorySyncRetry.addEventListener("click", async () => {
  releaseMemorySyncRetry.disabled = true;
  releaseMemorySyncStatus.textContent = "Scheduling release synchronization…";
  try {
    const response = await fetch("api/release-memory-sync/retry", {method: "POST"});
    const status = await response.json();
    if (!response.ok) throw new Error(status.detail || `HTTP ${response.status}`);
    renderReleaseSyncStatus(status);
    window.setTimeout(refreshReleaseSyncStatus, 1500);
  } catch (error) {
    renderReleaseSyncStatus({state: "failed", last_error: error.message || String(error)});
  } finally {
    releaseMemorySyncRetry.disabled = false;
  }
});

async function loadSettings() {
  settingsSaveState.textContent = "Loading…";
  try {
    const response = await fetch("api/settings");
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    generalInstructions.value = data.general_instructions || "";
    if (data.max_characters) generalInstructions.maxLength = data.max_characters;
    elevenLabsVoiceDefaults = data.elevenlabs_voice_defaults || elevenLabsVoiceDefaults;
    setElevenLabsVoiceControls(data.elevenlabs_voice_settings || elevenLabsVoiceDefaults);
    jarvisPreferences = data.preferences || {};
    await loadAgentControls(jarvisPreferences);
    elevenLabsModel.value = jarvisPreferences.elevenlabs_model || "eleven_flash_v2_5";
    elevenLabsSpeakerBoost.checked = jarvisPreferences.elevenlabs_speaker_boost === true;
    settingsAutoSpeak.checked = jarvisPreferences.auto_speak !== false;
    document.getElementById("proactive-voice-enabled").checked = jarvisPreferences.proactive_voice_enabled !== false;
    document.getElementById("voice-approval-enabled").checked = jarvisPreferences.voice_approval_enabled !== false;
    document.getElementById("wake-word-enabled").checked = jarvisPreferences.wake_word_enabled === true;
    document.getElementById("wake-phrase").value = jarvisPreferences.wake_phrase || "hey zbrano";
    window.dispatchEvent(new CustomEvent("zbrano-voice-preferences-loaded"));
    responseLength.value = jarvisPreferences.response_length || "balanced";
    confirmationStrictness.value = jarvisPreferences.confirmation_strictness || "standard";
    webSearchEnabled.checked = jarvisPreferences.web_search_enabled !== false;
    webSearchContextSize.value = jarvisPreferences.web_search_context_size || "medium";
    contextMessages.value = String(jarvisPreferences.context_messages ?? 20);
    retentionDays.value = String(jarvisPreferences.retention_days ?? 90);
    fastMemoryEnabled.checked = jarvisPreferences.fast_memory_enabled !== false;
    fastMemoryAutoCapture.checked = jarvisPreferences.fast_memory_auto_capture !== false;
    fastMemoryContextItems.value = String(jarvisPreferences.fast_memory_context_items ?? 10);
    preferredLanguage.value = jarvisPreferences.preferred_language || "auto";
    pronunciationDictionary.value = jarvisPreferences.pronunciation_dictionary || "";
    neuralStyle.value = jarvisPreferences.neural_style || "constellation";
    neuralScale.value = String(jarvisPreferences.neural_scale ?? 1);
    neuralNodeSize.value = String(jarvisPreferences.neural_node_size ?? 1);
    neuralOpacity.value = String(jarvisPreferences.neural_opacity ?? .38);
    releaseMemoryAutoSync.checked = jarvisPreferences.auto_sync_releases_to_workshop_memory !== false;
    reducedMotionSetting.checked = Boolean(jarvisPreferences.reduced_motion);
    textSize.value = jarvisPreferences.text_size || "medium";
    interfaceDensity.value = jarvisPreferences.interface_density || "comfortable";
    quietHoursEnabled.checked = Boolean(jarvisPreferences.quiet_hours_enabled);
    quietHoursStart.value = jarvisPreferences.quiet_hours_start || "22:00";
    quietHoursEnd.value = jarvisPreferences.quiet_hours_end || "07:00";
    voiceVolume.value = String(jarvisPreferences.voice_volume ?? 0.9);
    voiceVolumeValue.textContent = `${Math.round(Number(voiceVolume.value) * 100)}%`;
    applyInterfacePreferences(jarvisPreferences);
    saveVoiceSettings();
    await refreshReleaseSyncStatus();
    settingsSaveState.textContent = "";
  } catch (error) {
    settingsSaveState.textContent = `Could not load: ${error.message || error}`;
  }
}

settingsTab.addEventListener("click", async () => {
  showPanel("settings");
  await loadSettings();
});

saveSettings.addEventListener("click", async () => {
  saveSettings.disabled = true;
  settingsSaveState.textContent = "Saving…";
  try {
    const response = await fetch("api/settings", {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        general_instructions: generalInstructions.value,
        elevenlabs_stability: Number(elevenLabsVoiceInputs.stability.value),
        elevenlabs_similarity: Number(elevenLabsVoiceInputs.similarity.value),
        elevenlabs_style: Number(elevenLabsVoiceInputs.style.value),
        elevenlabs_speed: Number(elevenLabsVoiceInputs.speed.value),
        elevenlabs_model: elevenLabsModel.value,
        elevenlabs_speaker_boost: elevenLabsSpeakerBoost.checked,
        agent_model: agentModel.value,
        reasoning_effort: reasoningEffort.value,
        auto_speak: settingsAutoSpeak.checked,
        proactive_voice_enabled: document.getElementById("proactive-voice-enabled").checked,
        voice_approval_enabled: document.getElementById("voice-approval-enabled").checked,
        wake_word_enabled: document.getElementById("wake-word-enabled").checked,
        wake_phrase: document.getElementById("wake-phrase").value.trim() || "hey zbrano",
        response_length: responseLength.value,
        confirmation_strictness: confirmationStrictness.value,
        web_search_enabled: webSearchEnabled.checked,
        web_search_context_size: webSearchContextSize.value,
        context_messages: Number(contextMessages.value),
        retention_days: Number(retentionDays.value),
        fast_memory_enabled: fastMemoryEnabled.checked,
        fast_memory_auto_capture: fastMemoryAutoCapture.checked,
        fast_memory_context_items: Number(fastMemoryContextItems.value),
        preferred_language: preferredLanguage.value.trim() || "auto",
        pronunciation_dictionary: pronunciationDictionary.value,
        theme: document.querySelector('input[name="theme"]:checked')?.value || "dark",
        neural_style: neuralStyle.value,
        neural_scale: Number(neuralScale.value),
        neural_node_size: Number(neuralNodeSize.value),
        neural_opacity: Number(neuralOpacity.value),
        reduced_motion: reducedMotionSetting.checked,
        text_size: textSize.value,
        interface_density: interfaceDensity.value,
        quiet_hours_enabled: quietHoursEnabled.checked,
        quiet_hours_start: quietHoursStart.value,
        quiet_hours_end: quietHoursEnd.value,
        voice_volume: Number(voiceVolume.value),
        auto_sync_releases_to_workshop_memory: releaseMemoryAutoSync.checked,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    generalInstructions.value = data.general_instructions || "";
    setElevenLabsVoiceControls(data.elevenlabs_voice_settings || {});
    jarvisPreferences = data.preferences || jarvisPreferences;
    settingsAutoSpeak.checked = jarvisPreferences.auto_speak !== false;
    applyInterfacePreferences(jarvisPreferences);
    saveVoiceSettings();
    renderReleaseSyncStatus(data.release_sync || {});
    settingsSaveState.textContent = "Saved. New replies, speech, and release synchronization will use these settings.";
  } catch (error) {
    settingsSaveState.textContent = `Save failed: ${error.message || error}`;
  } finally {
    saveSettings.disabled = false;
  }
});

function entityMatches(entity) {
  const query = entitySearch.value.trim().toLowerCase();
  const selectedDomain = domainFilter.value;

  const matchesSearch =
    !query ||
    entity.entity_id.toLowerCase().includes(query) ||
    entity.friendly_name.toLowerCase().includes(query) ||
    String(entity.device_class || "").toLowerCase().includes(query) ||
    String(entity.area_name || "").toLowerCase().includes(query) ||
    String(entity.site_name || "").toLowerCase().includes(query) ||
    (entity.labels || []).some(label => String(label).toLowerCase().includes(query));

  const matchesDomain = !selectedDomain || entity.domain === selectedDomain;
  return matchesSearch && matchesDomain;
}

function ensureReview(entity) {
  if (!entityReview.has(entity.entity_id)) {
    entityReview.set(entity.entity_id, {
      selected: Boolean(entity.auto_approved),
      access: entity.auto_approved ? "low_risk_control_proposed" : entity.risk,
      aliases: "",
    });
  }
  return entityReview.get(entity.entity_id);
}

let policySaveTimers = new Map();
const pendingPolicySaves = new Map();
const policySaveRevisions = new Map();
const policySaveChains = new Map();

async function saveEntityPolicy(entity, review, keepalive = false) {
  const aliases = review.aliases
    .split(",")
    .map(alias => alias.trim())
    .filter(Boolean);

  const response = await fetch(
    `api/ha/entity-policy/${encodeURIComponent(entity.entity_id)}`,
    {
      method: "PUT",
      keepalive,
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        enabled: review.selected,
        friendly_name: entity.friendly_name,
        domain: entity.domain,
        device_class: entity.device_class,
        unit: entity.unit,
        access: review.access,
        aliases,
      }),
    }
  );

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || `HTTP ${response.status}`);
  }
  return data;
}

function queuePolicySave(entity, review, delay = 0) {
  const existing = policySaveTimers.get(entity.entity_id);
  if (existing) window.clearTimeout(existing);

  const revision = (policySaveRevisions.get(entity.entity_id) || 0) + 1;
  policySaveRevisions.set(entity.entity_id, revision);
  pendingPolicySaves.set(entity.entity_id, {entity, review, revision});
  const timer = window.setTimeout(async () => {
    try {
      entitySummary.textContent = `Saving approval for ${entity.friendly_name}…`;
      const previousSave = policySaveChains.get(entity.entity_id) || Promise.resolve();
      const currentSave = previousSave
        .catch(() => {})
        .then(() => saveEntityPolicy(entity, review));
      policySaveChains.set(entity.entity_id, currentSave);
      await currentSave;
      if (policySaveRevisions.get(entity.entity_id) === revision) {
        pendingPolicySaves.delete(entity.entity_id);
      }
      updateSelectionSummary();
    } catch (error) {
      entitySummary.textContent =
        `Failed to approve ${entity.friendly_name}: ${error.message || error}`;
    } finally {
      policySaveTimers.delete(entity.entity_id);
    }
  }, delay);

  policySaveTimers.set(entity.entity_id, timer);
}

function flushEntityPolicy(entity, review) {
  const existing = policySaveTimers.get(entity.entity_id);
  if (existing) window.clearTimeout(existing);
  policySaveTimers.delete(entity.entity_id);
  queuePolicySave(entity, review);
}

function flushPendingPoliciesOnExit() {
  for (const {entity, review} of pendingPolicySaves.values()) {
    saveEntityPolicy(entity, review, true).catch(() => {});
  }
}

window.addEventListener("pagehide", flushPendingPoliciesOnExit);
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden") flushPendingPoliciesOnExit();
});

function renderEntities() {
  const filtered = entityInventory.filter(entityMatches);
  entityRows.replaceChildren();

  for (const entity of filtered) {
    const review = ensureReview(entity);
    const row = document.createElement("tr");

    const selectCell = document.createElement("td");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = review.selected;
    checkbox.disabled = Boolean(entity.auto_approved);
    checkbox.title = entity.auto_approved
      ? "Automatically approved by socket/HVAC policy"
      : "Include this entity in ZBRANO policy";
    checkbox.addEventListener("change", () => {
      review.selected = checkbox.checked;
      updateSelectionSummary();
      queuePolicySave(entity, review);
    });
    selectCell.appendChild(checkbox);
    row.appendChild(selectCell);

    const nameCell = document.createElement("td");
    nameCell.textContent = entity.friendly_name;
    if (entity.auto_approved) nameCell.textContent += " · AUTO";
    row.appendChild(nameCell);

    const idCell = document.createElement("td");
    idCell.className = "entity-id";
    idCell.textContent = entity.entity_id;
    row.appendChild(idCell);

    const domainCell = document.createElement("td");
    domainCell.textContent = entity.domain;
    row.appendChild(domainCell);

    const areaCell = document.createElement("td");
    areaCell.textContent = entity.area_name || "Unassigned";
    areaCell.title = entity.area_name
      ? `Inherited from Home Assistant ${entity.area_source || "area"} assignment`
      : "Assign this entity or its device to an Area in Home Assistant";
    row.appendChild(areaCell);

    const siteCell = document.createElement("td");
    siteCell.textContent = entity.site_name || "Unlinked";
    siteCell.title = entity.zone_entity_id
      ? `${entity.site_label || entity.site_name} → ${entity.zone_entity_id}`
      : "Add a site-* label matching a Home Assistant Zone to this Area";
    row.appendChild(siteCell);

    const labelsCell = document.createElement("td");
    labelsCell.textContent = (entity.labels || []).join(", ") || "—";
    row.appendChild(labelsCell);

    const stateCell = document.createElement("td");
    stateCell.classList.add(entity.available ? "available" : "unavailable");
    stateCell.textContent = entity.state ?? "—";
    row.appendChild(stateCell);

    const classCell = document.createElement("td");
    classCell.textContent = [entity.device_class, entity.unit]
      .filter(Boolean)
      .join(" · ") || "—";
    row.appendChild(classCell);

    const accessCell = document.createElement("td");
    const accessSelect = document.createElement("select");
    [
      ["read_only", "read_only"],
      ["state_only", "state_only"],
      ["low_risk_control_proposed", "low_risk_control (approved)"],
      ["confirmation_required", "confirmation_required"],
      ["restricted", "restricted"],
    ].forEach(([access, label]) => {
      const option = document.createElement("option");
      option.value = access;
      option.textContent = label;
      option.selected = review.access === access;
      accessSelect.appendChild(option);
    });
    accessSelect.addEventListener("change", () => {
      review.access = accessSelect.value;
      if (review.selected) queuePolicySave(entity, review);
    });
    accessSelect.disabled = Boolean(entity.auto_approved);
    accessCell.appendChild(accessSelect);
    row.appendChild(accessCell);

    const aliasesCell = document.createElement("td");
    const aliasesInput = document.createElement("input");
    aliasesInput.placeholder = "comma-separated aliases";
    aliasesInput.value = review.aliases;
    aliasesInput.addEventListener("input", () => {
      review.aliases = aliasesInput.value;
      backupEntityAliases(entity.entity_id, review.aliases);
      queuePolicySave(entity, review, 600);
    });
    aliasesInput.addEventListener("blur", () => {
      review.aliases = aliasesInput.value;
      flushEntityPolicy(entity, review);
    });
    aliasesInput.addEventListener("keydown", event => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      review.aliases = aliasesInput.value;
      flushEntityPolicy(entity, review);
      aliasesInput.blur();
    });
    aliasesCell.appendChild(aliasesInput);
    row.appendChild(aliasesCell);

    entityRows.appendChild(row);
  }

  updateSelectionSummary(filtered.length);
  window.zbranoApplyEntityColumnLayout?.();
}

function updateSelectionSummary(filteredCount = null) {
  const selectedCount = [...entityReview.values()]
    .filter(item => item.selected).length;
  const shown = filteredCount ?? entityInventory.filter(entityMatches).length;

  entitySummary.textContent =
    `${shown} shown · ${entityInventory.length} total · ` +
    `${selectedCount} approved now. Changes save immediately to ZBRANO runtime policy.`;
}

async function loadEntities() {
  entitySummary.textContent = "Loading Home Assistant entities…";
  refreshEntities.disabled = true;

  try {
    const response = await fetch("api/ha/entities?refresh=1");
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}`);
    }

    entityInventory = data.entities || [];
    if (!entityInventory.length) {
      throw new Error("Home Assistant returned an empty entity inventory");
    }
    const inventorySource = data.source ? ` · source: ${data.source}` : "";

    const approvedResponse = await fetch("api/ha/approved");
    const approvedData = await approvedResponse.json();
    const policy = approvedData.policy || {};

    entityReview.clear();
    const interruptedSaves = [];
    for (const entity of entityInventory) {
      const existing = policy[entity.entity_id];
      const serverAliases = existing && Array.isArray(existing.aliases)
        ? existing.aliases.join(", ")
        : "";
      const hasLocalAliases = Object.prototype.hasOwnProperty.call(
        entityAliasBackup,
        entity.entity_id
      );
      const localAliases = hasLocalAliases && typeof entityAliasBackup[entity.entity_id] === "string"
        ? entityAliasBackup[entity.entity_id]
        : "";
      if (existing || hasLocalAliases) {
        const restoredAliases = hasLocalAliases ? localAliases : serverAliases;
        entityReview.set(entity.entity_id, {
          selected: entity.auto_approved || Boolean(existing && existing.enabled),
          access: entity.auto_approved
            ? "low_risk_control_proposed"
            : ((existing && existing.access) || entity.risk),
          aliases: restoredAliases,
        });
        if (!hasLocalAliases && serverAliases) {
          backupEntityAliases(entity.entity_id, serverAliases);
        } else if (hasLocalAliases && localAliases !== serverAliases) {
          interruptedSaves.push(entity);
        }
      }
    }

    for (const entity of interruptedSaves) {
      queuePolicySave(entity, entityReview.get(entity.entity_id));
    }

    inventoryLoaded = true;

    domainFilter.innerHTML = '<option value="">All domains</option>';
    for (const domain of data.domains || []) {
      const option = document.createElement("option");
      option.value = domain;
      option.textContent = domain;
      domainFilter.appendChild(option);
    }

    renderEntities();
    entitySummary.textContent += inventorySource;
  } catch (error) {
    entitySummary.textContent = `Failed to load entities: ${error.message || error}`;
  } finally {
    refreshEntities.disabled = false;
  }
}

entitySearch.addEventListener("input", renderEntities);
domainFilter.addEventListener("change", renderEntities);
refreshEntities.addEventListener("click", loadEntities);

function selectedCatalog() {
  return entityInventory
    .filter(entity => ensureReview(entity).selected)
    .map(entity => {
      const review = ensureReview(entity);
      return {
        entity_id: entity.entity_id,
        friendly_name: entity.friendly_name,
        domain: entity.domain,
        area: entity.area_name || "",
        site: entity.site_name || "",
        zone: entity.zone_entity_id || "",
        labels: entity.labels || [],
        zbrano_role: entity.zbrano_role || "",
        device_class: entity.device_class,
        unit: entity.unit,
        access: review.access,
        aliases: review.aliases
          .split(",")
          .map(alias => alias.trim())
          .filter(Boolean),
      };
    });
}

exportEntities.addEventListener("click", () => {
  const selected = selectedCatalog();
  const source = selected.length ? selected : entityInventory.map(entity => ({
    entity_id: entity.entity_id,
    friendly_name: entity.friendly_name,
    domain: entity.domain,
    area: entity.area_name || "",
    site: entity.site_name || "",
    zone: entity.zone_entity_id || "",
    labels: entity.labels || [],
    zbrano_role: entity.zbrano_role || "",
    device_class: entity.device_class,
    unit: entity.unit,
    access: ensureReview(entity).access,
    aliases: ensureReview(entity).aliases
      .split(",")
      .map(alias => alias.trim())
      .filter(Boolean),
  }));

  const blob = new Blob(
    [JSON.stringify({generated_by: "ZBRANO", entities: source}, null, 2)],
    {type: "application/json"}
  );
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "home-assistant-entity-catalog.json";
  link.click();
  URL.revokeObjectURL(url);
});

saveMemoryDraft.addEventListener("click", async () => {
  const entities = selectedCatalog();
  if (!entities.length) {
    entitySummary.textContent = "Select at least one entity before preparing an inventory update.";
    return;
  }

  saveMemoryDraft.disabled = true;
  entitySummary.textContent = `Preparing a reviewable update for ${entities.length} selected entities…`;
  try {
    const response = await fetch("api/memory/entity-catalog-draft", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({project: "ZBRANO Workshop Assistant", entities}),
    });
    const responseText = await response.text();
    let data = {};
    try { data = responseText ? JSON.parse(responseText) : {}; }
    catch { data = {detail: responseText.slice(0, 500) || `HTTP ${response.status}`}; }
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    if (!data.catalog_markdown) throw new Error("The server returned no entity inventory content");

    const blob = new Blob([data.catalog_markdown], {type: "text/markdown;charset=utf-8"});
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = data.filename || "HA OS Entities Update Draft.md";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    entitySummary.textContent = `Prepared ${entities.length} entities as ${link.download}. No Workshop Memory note was changed; attach the draft in chat when you want an approved reconciliation.`;
  } catch (error) {
    entitySummary.textContent = `Could not prepare entity inventory update: ${error.message || error}`;
  } finally {
    saveMemoryDraft.disabled = false;
  }
});

showApproved.addEventListener("click", async () => {
  try {
    const response = await fetch("api/ha/approved");
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    entitySummary.textContent =
      `Read approved: ${data.read_entities.length} · ` +
      `Control approved: ${data.control_entities.length} · ` +
      `Safe control domains: ${data.safe_control_domains.join(", ")}`;
  } catch (error) {
    entitySummary.textContent =
      `Failed to load approved entities: ${error.message || error}`;
  }
});

stopButton.addEventListener("click", () => {
  if (!activeRequest) {
    stopAudioPlayback("VOICE STOPPED");
    return;
  }
  activeRequest.stopped = true;
  const {socket, jarvisMessage} = activeRequest;
  if (socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({type: "stop"}));
  } else {
    socket.close();
  }
  const existing = jarvisMessage.textContent.trim();
  renderMessageContent(jarvisMessage, existing && existing !== "Connecting…"
    ? `${existing}\n\n[Response stopped]`
    : "Response stopped.");
  stopAudioPlayback("STOPPED");
  stopButton.disabled = true;
  finishResponseActivity("Stopped");
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message || activeRequest) return;

  stopAudioPlayback("PROCESSING");
  rememberPrompt(message);
  const messageAttachments = typeof window.zbranoAttachmentItems === "function"
    ? window.zbranoAttachmentItems()
    : [];
  addMessage(message, "user", messageAttachments);
  input.value = "";
  resizeComposer();
  document.body.classList.remove("jarvis-input-active");
  resetToolTimeline();
  startResponseActivity("Thinking");
  input.disabled = true;
  sendButton.disabled = true;
  micButton.disabled = false;
  stopButton.disabled = false;

  setNeuronIntensity(false);
  const jarvisMessage = addMessage("Connecting…", "jarvis");
  let answer = "";
  let speechBuffer = "";
  let statusText = "Connecting…";

  const endpoint = new URL("api/chat/ws", document.baseURI);
  endpoint.protocol = endpoint.protocol === "https:" ? "wss:" : "ws:";

  const socket = new WebSocket(endpoint);
  let opened = false;
  const requestState = {socket, jarvisMessage, stopped: false};
  activeRequest = requestState;

  const connectionTimer = window.setTimeout(() => {
    if (!opened && socket.readyState !== WebSocket.OPEN) {
      renderMessageContent(jarvisMessage, "Request failed: WebSocket did not connect. Check the ZBRANO app log.");
      socket.close();
    }
  }, 8000);

  socket.addEventListener("open", () => {
    opened = true;
    window.clearTimeout(connectionTimer);
    const attachmentIds =
      typeof window.zbranoAttachmentIds === "function"
        ? window.zbranoAttachmentIds()
        : [];
    socket.send(JSON.stringify({
      session_id: jarvisChatSessionId,
      message,
      attachment_ids: attachmentIds,
      search_mode: webSearchMode?.value || "auto",
    }));
    if (typeof window.zbranoClearPendingAttachments === "function") {
      window.zbranoClearPendingAttachments();
    }
  });

  socket.addEventListener("message", (messageEvent) => {
    let eventData;
    try {
      eventData = JSON.parse(messageEvent.data);
    } catch {
      renderMessageContent(jarvisMessage, `Invalid stream event: ${messageEvent.data}`);
      return;
    }

    if (requestState.stopped && eventData.type !== "stopped") return;

    if (eventData.type === "activity") {
      applyToolActivity(eventData);
    } else if (eventData.type === "status") {
      statusText = eventData.message || "Working…";
      setResponseActivity(statusText);
      if (!answer) renderMessageContent(jarvisMessage, statusText);
    } else if (eventData.type === "delta") {
      markFirstResponse();
      setResponseActivity("Responding…");
      if (!answer) renderMessageContent(jarvisMessage, "");
      const followLatest = isNearMessagesBottom();
      const delta = eventData.text || "";
      answer += delta;
      speechBuffer += delta;
      renderMessageContent(jarvisMessage, answer);
      if (followLatest) messages.scrollTop = messages.scrollHeight;
      const fastSpeechStart=!speechQueueRunning&&!speechQueue.length&&!activeAudio;
      const speech = extractSpeakableChunks(speechBuffer,false,fastSpeechStart);
      speechBuffer = speech.remaining;
      speech.chunks.forEach(chunk => queueSpeech(chunk));
    } else if (eventData.type === "sources") {
      const sources = Array.isArray(eventData.sources) ? eventData.sources : [];
      const unique = sources.filter((source, index, items) => source?.url && items.findIndex(item => item?.url === source.url) === index).slice(0, 8);
      if (unique.length) {
        const sourceText = "\n\n### Sources\n" + unique.map(source => `- [${String(source.title || source.url).replaceAll("[", "").replaceAll("]", "")} ](${source.url})`).join("\n");
        answer += sourceText;
        renderMessageContent(jarvisMessage, answer);
        messages.scrollTop = messages.scrollHeight;
      }
    } else if (eventData.type === "error") {
      finishOpenToolActivities("failed");
      finishResponseActivity("Failed");
      renderMessageContent(jarvisMessage, `Request failed: ${eventData.message || "Unknown error"}`);
    } else if (eventData.type === "stopped") {
      if (!jarvisMessage.textContent.includes("[Response stopped]")) {
        renderMessageContent(jarvisMessage, `${jarvisMessage.dataset.rawText || jarvisMessage.textContent}\n\n[Response stopped]`);
      }
    }
  });

  socket.addEventListener("error", () => {
    finishResponseActivity("Connection failed");
    if (!answer) {
      renderMessageContent(jarvisMessage, "Request failed: WebSocket connection error");
    }
  });

  socket.addEventListener("close", (closeEvent) => {
    window.clearTimeout(connectionTimer);
    if (!requestState.stopped && !answer && !jarvisMessage.textContent.startsWith("Request failed:")) {
      renderMessageContent(
        jarvisMessage,
        closeEvent.code === 1000
          ? (statusText || "No response received.")
        : `Request failed: WebSocket closed (${closeEvent.code}).`
      );
    }
    if(activeRequest!==requestState){if(requestState.stopped)refreshChatList();return}
    activeRequest = null;
    finishOpenToolActivities(requestState.stopped ? "failed" : "completed");
    finishResponseActivity(requestState.stopped ? "Stopped" : (answer ? "Completed" : "No response"));
    if (!requestState.stopped && answer) window.zbranoMarkTabChanged?.("chat-tab");
    input.disabled = false;
    sendButton.disabled = false;
    micButton.disabled = false;
    stopButton.disabled = true;
    refreshChatList();
    input.focus();
    if (!requestState.stopped && answer) {
      const speech = extractSpeakableChunks(speechBuffer, true);
      speech.chunks.forEach(chunk => queueSpeech(chunk));
    } else if (!requestState.stopped) setVoiceState("VOICE READY");
  });
});

function startBrainNetwork() {
  const canvas = document.getElementById("brain-network");
  const context = canvas.getContext("2d");
  const prefersReducedMotion = () =>
    window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
    document.documentElement.dataset.reducedMotion === "true";
  let nodes = [];
  let links = [];
  let width = 0;
  let height = 0;
  let frame = 0;
  let lastFrame = 0;

  function cssRgb(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function buildCollective() {
    const count = Math.min(320, Math.max(170, Math.floor((width * height) / 1800)));
    nodes = Array.from({length: count}, (_, index) => {
      const azimuth = Math.random() * Math.PI * 2;
      const cosPolar = Math.random() * 2 - 1;
      const sinPolar = Math.sqrt(1 - cosPolar * cosPolar);
      const radius = Math.pow(Math.random(), index % 5 === 0 ? .9 : .48);
      return {
        x: Math.cos(azimuth) * sinPolar * radius,
        y: Math.sin(azimuth) * sinPolar * radius,
        z: cosPolar * radius,
        phase: Math.random() * Math.PI * 2,
        weight: .65 + Math.random() * .9,
      };
    });

    const pairs = new Set();
    links = [];
    nodes.forEach((node, index) => {
      const nearest = [];
      for (let otherIndex = 0; otherIndex < nodes.length; otherIndex += 1) {
        if (otherIndex === index) continue;
        const other = nodes[otherIndex];
        const distance = Math.hypot(node.x - other.x, node.y - other.y, node.z - other.z);
        if (distance < .34) nearest.push({otherIndex, distance});
      }
      nearest.sort((left, right) => left.distance - right.distance);
      nearest.slice(0, index % 7 === 0 ? 3 : 2).forEach(({otherIndex, distance}) => {
        const from = Math.min(index, otherIndex);
        const to = Math.max(index, otherIndex);
        const key = `${from}:${to}`;
        if (!pairs.has(key)) {
          pairs.add(key);
          links.push({from, to, distance});
        }
      });
    });
  }

  function resize() {
    const ratio = Math.min(window.devicePixelRatio || 1, 1.5);
    const bounds = canvas.parentElement.getBoundingClientRect();
    width = Math.max(1, bounds.width);
    height = Math.max(1, bounds.height);
    canvas.width = Math.floor(width * ratio);
    canvas.height = Math.floor(height * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    buildCollective();
    draw(performance.now(), true);
  }

  function draw(now = performance.now(), force = false) {
    if (!force && now - lastFrame < 32) {
      frame = window.requestAnimationFrame(draw);
      return;
    }
    lastFrame = now;
    context.clearRect(0, 0, width, height);
    const reducedMotion = prefersReducedMotion();
    const angle = reducedMotion ? .32 : now * .000035;
    const tilt = -.15 + Math.sin(reducedMotion ? 0 : now * .00009) * .035;
    const cosAngle = Math.cos(angle);
    const sinAngle = Math.sin(angle);
    const cosTilt = Math.cos(tilt);
    const sinTilt = Math.sin(tilt);
    const neuralStyleName = document.documentElement.dataset.neuralStyle || "constellation";
    const neuralScaleFactor = Number(document.documentElement.dataset.neuralScale) || 1;
    const neuralNodeScale = Number(document.documentElement.dataset.neuralNodeSize) || 1;
    const sphereRadius = Math.min(width * .41, height * .39, 300) * neuralScaleFactor;
    const centerX = width * .5;
    const centerY = height * .43;
    const projected = nodes.map(node => {
      const rotatedX = node.x * cosAngle + node.z * sinAngle;
      const rotatedZ = -node.x * sinAngle + node.z * cosAngle;
      const rotatedY = node.y * cosTilt - rotatedZ * sinTilt;
      const depth = node.y * sinTilt + rotatedZ * cosTilt;
      const perspective = 1 / (1.18 - depth * .22);
      return {
        x: centerX + rotatedX * sphereRadius * perspective,
        y: centerY + rotatedY * sphereRadius * perspective * (neuralStyleName === "orbital" ? .48 : 1),
        z: depth,
        perspective,
        node,
      };
    });
    const linkRgb = cssRgb("--node-link");
    const edgeRgb = cssRgb("--node-edge");
    const coreRgb = cssRgb("--node-core");

    context.lineCap = "round";
    for (const [linkIndex, link] of links.entries()) {
      if (neuralStyleName === "minimal" && linkIndex % 5 !== 0) continue;
      if (neuralStyleName === "orbital" && linkIndex % 2 !== 0) continue;
      const from = projected[link.from];
      const to = projected[link.to];
      const depthAlpha = Math.max(.18, Math.min(.62, .34 + (from.z + to.z) * .14));
      const proximity = .45 + .55 * Math.max(0, 1 - link.distance / .34);
      context.strokeStyle = `rgba(${linkRgb}, ${depthAlpha * proximity})`;
      context.lineWidth = (.85 + Math.max(0, (from.z + to.z) * .12)) * (neuralStyleName === "mesh" ? 1.7 : neuralStyleName === "minimal" ? .65 : 1);
      context.shadowColor = `rgba(${linkRgb}, ${depthAlpha * .42})`;
      context.shadowBlur = 2.6;
      context.beginPath();
      context.moveTo(from.x, from.y);
      context.lineTo(to.x, to.y);
      context.stroke();
    }
    context.shadowBlur = 0;

    projected.sort((left, right) => left.z - right.z);
    for (const [pointIndex, point] of projected.entries()) {
      if (neuralStyleName === "minimal" && pointIndex % 3 !== 0) continue;
      const pulse = reducedMotion ? 1 : .82 + Math.sin(now * .0012 + point.node.phase) * .18;
      const styleNodeScale = neuralStyleName === "mesh" ? .72 : neuralStyleName === "orbital" ? 1.18 : 1;
      const nodeRadius = Math.max(.65, (1.35 + point.node.weight * 1.05) * point.perspective * pulse * neuralNodeScale * styleNodeScale);
      const depthAlpha = Math.max(.42, Math.min(1, .68 + point.z * .3));
      context.shadowColor = `rgba(${edgeRgb}, ${depthAlpha * .48})`;
      context.shadowBlur = nodeRadius * 5.2;
      context.fillStyle = `rgba(${coreRgb}, ${Math.min(.98, depthAlpha + .15)})`;
      context.strokeStyle = `rgba(${edgeRgb}, ${depthAlpha})`;
      context.lineWidth = Math.max(.8, nodeRadius * .38);
      context.beginPath();
      context.arc(point.x, point.y, nodeRadius, 0, Math.PI * 2);
      context.fill();
      context.stroke();
      context.shadowBlur = 0;
      context.fillStyle = `rgba(255, 255, 240, ${depthAlpha * .82})`;
      context.beginPath();
      context.arc(point.x - nodeRadius * .28, point.y - nodeRadius * .3, Math.max(.28, nodeRadius * .22), 0, Math.PI * 2);
      context.fill();
    }
    if (!reducedMotion) frame = window.requestAnimationFrame(draw);
  }

  const resizeObserver = new ResizeObserver(() => {
    if (frame) window.cancelAnimationFrame(frame);
    resize();
  });
  resizeObserver.observe(canvas.parentElement);
  window.addEventListener("jarvis-theme-change", () => {
    if (frame) window.cancelAnimationFrame(frame);
    draw(performance.now(), true);
  });
  window.addEventListener("zbrano-neural-change", () => {
    if (frame) window.cancelAnimationFrame(frame);
    draw(performance.now(), true);
  });
  resize();
}

checkHealth();
loadSettings().finally(() => openChat(jarvisChatSessionId));
const hudClock = document.getElementById("hud-clock");
if (hudClock) window.setInterval(() => {
  hudClock.textContent = new Date().toLocaleTimeString([], {hour12: false});
}, 1000);
fetch("api/ha/approved")
  .then(response => response.json())
  .then(data => {
    const entityBusCount = document.getElementById("entity-bus-count");
    if (entityBusCount) {
      entityBusCount.textContent =
        String((data.read_entities || []).length + (data.control_entities || []).length).padStart(3, "0");
    }
  })
  .catch(() => {});
startBrainNetwork();

(() => {
  const tabs = [...document.querySelectorAll(".settings-category-tab")];
  const cards = [...document.querySelectorAll(".settings-card[data-settings-category]")];
  if (!tabs.length || !cards.length) return;
  const activate = target => {
    const selected = tabs.some(tab => tab.dataset.settingsTarget === target) ? target : "appearance";
    for (const tab of tabs) {
      const active = tab.dataset.settingsTarget === selected;
      tab.classList.toggle("active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    }
    for (const card of cards) card.hidden = card.dataset.settingsCategory !== selected;
    try { localStorage.setItem("zbrano_settings_category_v1", selected); } catch (_) {}
  };
  for (const tab of tabs) {
    tab.addEventListener("click", () => activate(tab.dataset.settingsTarget));
    tab.addEventListener("keydown", event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const current = tabs.indexOf(tab);
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1
        : (current + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
      activate(tabs[next].dataset.settingsTarget);
      tabs[next].focus();
    });
  }
  let initial = "appearance";
  try { initial = localStorage.getItem("zbrano_settings_category_v1") || initial; } catch (_) {}
  activate(initial);
})();
