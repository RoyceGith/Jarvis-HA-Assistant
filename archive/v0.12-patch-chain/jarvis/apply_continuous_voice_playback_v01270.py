import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"ZBRANO v0.12.70 expected one {label} marker; found {count}"
        )
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.70 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    frontend = replace_once(
        frontend,
        '''let speechQueue = [];
let speechQueueRunning = false;
let hasSavedSpeechProvider = false;''',
        '''let speechQueue = [];
let speechQueueRunning = false;
let speechPrefetch = null;
let speechPrefetchAbortController = null;
let hasSavedSpeechProvider = false;''',
        "speech prefetch state",
    )

    frontend = replace_once(
        frontend,
        '''  if (speechAbortController) speechAbortController.abort();
  speechAbortController = null;
  speechQueue = [];
  speechQueueRunning = false;''',
        '''  if (speechAbortController) speechAbortController.abort();
  speechAbortController = null;
  if (speechPrefetchAbortController) speechPrefetchAbortController.abort();
  speechPrefetchAbortController = null;
  speechPrefetch = null;
  speechQueue = [];
  speechQueueRunning = false;''',
        "speech prefetch cancellation",
    )

    frontend = replace_once(
        frontend,
        "async function playSpeechText(text, force = false) {",
        "async function playSpeechText(text, force = false, prefetchedBlob = null) {",
        "prefetched speech playback argument",
    )

    frontend = replace_once(
        frontend,
        '''  try {
    const response = await fetch("api/voice/speech", {''',
        '''  try {
    if (prefetchedBlob) {
      const blob = await prefetchedBlob;
      if (speechController.signal.aborted || !blob) return;
      activeAudioUrl = URL.createObjectURL(blob);
      activeAudio = new Audio(activeAudioUrl);
      activeAudio.volume = Number(jarvisPreferences.voice_volume ?? 0.9);
      activeAudio.addEventListener("ended", () => cleanupActiveAudio(speechQueue.length ? "SPEECH BUFFERING" : "VOICE READY"));
      activeAudio.addEventListener("error", () => stopAudioPlayback("VOICE PLAYBACK FAILED"));
      setVoiceState("SPEAKING");
      await activeAudio.play();
      await waitForAudioEnd(activeAudio);
      return;
    }

    const response = await fetch("api/voice/speech", {''',
        "prefetched blob playback",
    )

    old_queue = '''async function runSpeechQueue(force = false) {
  if (speechQueueRunning) return;
  speechQueueRunning = true;
  try {
    while (speechQueue.length) {
      const nextText = speechQueue.shift();
      await playSpeechText(nextText, force);
    }
  } finally {
    speechQueueRunning = false;
  }
}
'''
    new_queue = '''async function fetchSpeechBlob(text, force = false) {
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
'''
    frontend = replace_once(frontend, old_queue, new_queue, "prefetched speech queue")

    frontend = replace_once(
        frontend,
        '''  speechQueue.push(spoken);
  runSpeechQueue(force);''',
        '''  speechQueue.push(spoken);
  runSpeechQueue(force);
  primeSpeechPrefetch(force);''',
        "prefetch trigger while speaking",
    )

    backend = backend.replace('version="0.12.69"', 'version="0.12.70"')
    backend = backend.replace('"version": "0.12.69"', '"version": "0.12.70"')
    backend = backend.replace(
        '"X-ZBRANO-Frontend-Version": "0.12.69"',
        '"X-ZBRANO-Frontend-Version": "0.12.70"',
    )
    backend = backend.replace(
        '"name": "ZBRANO Developer Mode", "version": "0.12.69"',
        '"name": "ZBRANO Developer Mode", "version": "0.12.70"',
    )
    frontend = frontend.replace("HUD 0.12.69", "HUD 0.12.70")

    for marker in (
        "speechPrefetchAbortController",
        "async function fetchSpeechBlob(text, force = false)",
        "function primeSpeechPrefetch(force = false)",
        "await playSpeechText(nextText, force, prepared)",
        "primeSpeechPrefetch(force);",
        "speech.chunks.forEach(chunk => queueSpeech(chunk));",
        "HUD 0.12.70",
    ):
        require(frontend, marker, marker)
    require(backend, 'version="0.12.70"', "backend version")

    delta_block = frontend.split('} else if (eventData.type === "delta") {', 1)[1].split(
        '} else if (eventData.type === "error") {', 1
    )[0]
    if "queueSpeech(" not in delta_block:
        raise RuntimeError("ZBRANO v0.12.70 no longer starts speech while text is streaming")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
