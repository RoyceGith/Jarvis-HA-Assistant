import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.100 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.100 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    voice_start = backend.find('@app.post("/api/voice/transcribe")')
    voice_end = backend.find('\n\n@app.post("/api/voice/speech")', voice_start)
    if voice_start < 0 or voice_end < 0:
        raise RuntimeError("ZBRANO v0.12.100 could not locate the voice transcription endpoint")
    voice_endpoints = '''async def _transcribe_voice_upload(audio: UploadFile, *, wake: bool = False) -> dict[str, str]:
    """Transcribe one bounded browser recording without retaining audio or exposing the API key."""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OpenAI API key is not configured")

    content_type = (audio.content_type or "application/octet-stream").lower()
    if not (content_type.startswith("audio/") or content_type == "video/webm"):
        raise HTTPException(status_code=415, detail="Unsupported microphone recording format")

    audio_bytes = await audio.read(VOICE_UPLOAD_MAX_BYTES + 1)
    await audio.close()
    minimum_bytes = 2500 if wake else 1
    if len(audio_bytes) < minimum_bytes:
        raise HTTPException(status_code=422 if wake else 400, detail="No clear speech was detected")
    if len(audio_bytes) > VOICE_UPLOAD_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Microphone recording is too large")

    filename = audio.filename or ("zbrano-wake.webm" if wake else "zbrano-recording.webm")
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    files = {"file": (filename, audio_bytes, content_type)}
    data = {"model": OPENAI_TRANSCRIPTION_MODEL, "response_format": "json", "temperature": "0"}
    if not wake:
        data["prompt"] = "ZBRANO workshop assistant. Preserve Home Assistant entity names and commands."
    async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=10.0)) as client:
        response = await client.post(OPENAI_TRANSCRIPTIONS_URL, headers=headers, data=data, files=files)
    if response.is_error:
        raise HTTPException(status_code=502, detail=f"Voice transcription failed: {openai_error_message(response)}")

    text = str(response.json().get("text") or "").strip()
    normalized = " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())
    silence_hallucinations = {
        "zbrano workshop intelligence core assistant", "zbrano workshop assistant",
        "jarvis workshop assistant", "workshop intelligence core assistant",
        "thank you", "thanks for watching",
    }
    if not text or (wake and normalized in silence_hallucinations):
        raise HTTPException(status_code=422, detail="No clear speech was detected")
    return {"text": text, "model": OPENAI_TRANSCRIPTION_MODEL}


@app.post("/api/voice/transcribe")
async def transcribe_voice(audio: UploadFile = File(...)) -> dict[str, str]:
    """Transcribe a deliberate Talk-button recording."""
    return await _transcribe_voice_upload(audio)


@app.post("/api/voice/wake-transcribe")
async def transcribe_wake_voice(audio: UploadFile = File(...)) -> dict[str, str]:
    """Transcribe a voice-activity-gated wake utterance without assistant-name prompting."""
    return await _transcribe_voice_upload(audio, wake=True)
'''
    backend = backend[:voice_start] + voice_endpoints + backend[voice_end:]

    frontend = replace_once(
        frontend,
        '''  function startWake(){
    if(!wakeCanRun())return;
    startWakeFallback().catch(()=>{});stopWake(true);const recognition=new Recognition();wakeRecognition=recognition;recognition.lang=recognitionLanguage();recognition.continuous=true;recognition.interimResults=true;''',
        '''  async function startWake(){
    if(!wakeCanRun())return;
    stopWake(true);await startWakeFallback();
    if(wakeFallbackStream||wakeFallbackStarting){status(wakeFallbackStream?`Reliable wake listening active for "${wakePhrase.value.trim()||"hey zbrano"}"`:"Starting reliable wake listener...","listening");return}
    const recognition=new Recognition();wakeRecognition=recognition;recognition.lang=recognitionLanguage();recognition.continuous=true;recognition.interimResults=true;''',
        "reliable wake priority",
    )
    frontend = replace_once(
        frontend,
        '''          wakeFallbackRecorder=recorder;wakeFallbackChunks=chunks;wakeFallbackSpeechStart=now;wakeFallbackLastVoice=now;''',
        '''          wakeFallbackRecorder=recorder;wakeFallbackChunks=chunks;wakeFallbackSpeechStart=now;wakeFallbackLastVoice=now;
          status("Speech detected - recording wake utterance...","listening");''',
        "speech detection visibility",
    )
    frontend = replace_once(
        frontend,
        '''    }catch(error){status(`Reliable wake listener unavailable: ${error.message||error}`,"error");stopWakeFallback()}''',
        '''    }catch(error){status(`Reliable wake listener unavailable: ${error.message||error}. Trying Chrome speech recognition...`,"error");stopWakeFallback()}''',
        "native fallback clarity",
    )
    fallback_start = frontend.find("  async function transcribeWakeFallback(")
    fallback_end = frontend.find("\n  function finishWakeFallbackUtterance", fallback_start)
    if fallback_start < 0 or fallback_end < 0:
        raise RuntimeError("ZBRANO v0.12.100 could not locate reliable wake transcription")
    fallback_block = frontend[fallback_start:fallback_end]
    fallback_block = replace_once(
        fallback_block,
        'fetch("api/voice/transcribe",{method:"POST",body})',
        'fetch("api/voice/wake-transcribe",{method:"POST",body})',
        "dedicated wake endpoint",
    )
    fallback_block = replace_once(
        fallback_block,
        '''if(!response.ok){if(response.status!==422)throw new Error(data.detail||`HTTP ${response.status}`);return}''',
        '''if(!response.ok){if(response.status!==422)throw new Error(data.detail||`HTTP ${response.status}`);status(`Reliable wake listening active for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");return}''',
        "no-speech recovery",
    )
    frontend = frontend[:fallback_start] + fallback_block + frontend[fallback_end:]
    frontend = replace_once(frontend, "const validDuration=ended-started>=300;", "const validDuration=ended-started>=550;", "minimum wake duration")
    frontend = replace_once(frontend, "const threshold=Math.max(.018,wakeNoiseFloor*2.8);", "const threshold=Math.max(.03,wakeNoiseFloor*3.5);", "wake voice threshold")
    frontend = replace_once(frontend, "if(wakeFallbackVoiceFrames>=2){", "if(wakeFallbackVoiceFrames>=3){", "wake voice persistence")
    frontend = replace_once(
        frontend,
        '''  function fallbackRateAllowed(){
    const cutoff=Date.now()-3600000;while(wakeFallbackAttempts.length&&wakeFallbackAttempts[0]<cutoff)wakeFallbackAttempts.shift();
    if(wakeFallbackAttempts.length>=WAKE_FALLBACK_LIMIT){wakeEnabled.checked=false;status("Reliable wake listening reached its 20-transcription hourly safety limit. Turn it on again later.","error");stopWake();return false}
    wakeFallbackAttempts.push(Date.now());return true;
  }''',
        '''  function fallbackRateAllowed(mode){
    const now=Date.now();const cutoff=now-3600000;while(wakeFallbackAttempts.length&&wakeFallbackAttempts[0]<cutoff)wakeFallbackAttempts.shift();
    if(mode==="wake"&&now-Number(fallbackRateAllowed.lastWakeAt||0)<6000){status(`Reliable wake listening active for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");return false}
    if(wakeFallbackAttempts.length>=WAKE_FALLBACK_LIMIT){wakeEnabled.checked=false;status("Reliable wake listening reached its 20-transcription hourly safety limit. Turn it on again later.","error");stopWake();return false}
    if(mode==="wake")fallbackRateAllowed.lastWakeAt=now;wakeFallbackAttempts.push(now);return true;
  }''',
        "wake transcription cooldown",
    )
    frontend = replace_once(
        frontend,
        '''if(wakeFallbackBusy||generation!==wakeFallbackGeneration||!wakeEnabled.checked||!fallbackRateAllowed())return;''',
        '''if(wakeFallbackBusy||generation!==wakeFallbackGeneration||!wakeEnabled.checked||!fallbackRateAllowed(mode))return;''',
        "mode-aware wake rate limit",
    )

    backend = backend.replace('version="0.12.99"', 'version="0.12.100"')
    backend = backend.replace('"version": "0.12.99"', '"version": "0.12.100"')
    frontend = frontend.replace("HUD 0.12.99", "HUD 0.12.100")

    for marker, location in [
        ('version="0.12.100"', backend),
        ('async function startWake()', frontend),
        ('await startWakeFallback()', frontend),
        ('if(wakeFallbackStream||wakeFallbackStarting)', frontend),
        ('Speech detected - recording wake utterance', frontend),
        ('Trying Chrome speech recognition', frontend),
        ('api/voice/wake-transcribe', frontend),
        ('fallbackRateAllowed.lastWakeAt', frontend),
        ('HUD 0.12.100', frontend),
    ]:
        require(location, marker, marker)
    for marker in (
        '@app.post("/api/voice/wake-transcribe")',
        'silence_hallucinations = {',
        'if not wake:',
        'minimum_bytes = 2500 if wake else 1',
    ):
        require(backend, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
