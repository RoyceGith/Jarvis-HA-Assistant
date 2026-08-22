import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.103 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.103 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        '''WAKE_SHADOW_EMBEDDING_PATH = Path(__file__).resolve().parent.parent / "models/wakeword/embedding_model.onnx"


def _new_wake_shadow_model() -> tuple[Any, Any]:''',
        '''WAKE_SHADOW_EMBEDDING_PATH = Path(__file__).resolve().parent.parent / "models/wakeword/embedding_model.onnx"
WAKE_CALIBRATION_DIR = DATA_DIR / "wakeword_calibration"
WAKE_POSITIVE_DIR = WAKE_CALIBRATION_DIR / "positive"
WAKE_NEGATIVE_DIR = WAKE_CALIBRATION_DIR / "negative"
WAKE_VERIFIER_PATH = WAKE_CALIBRATION_DIR / "hey_zbrano_verifier.pkl"
WAKE_VERIFIER_TRAIN_LOCK = asyncio.Lock()


def _new_wake_shadow_model() -> tuple[Any, Any, bool]:''',
        "verifier storage",
    )
    backend = replace_once(
        backend,
        '''    model = OpenWakeWordModel(
        wakeword_models=[str(WAKE_SHADOW_MODEL_PATH)],
        inference_framework="onnx",
        melspec_model_path=str(WAKE_SHADOW_MELSPEC_PATH),
        embedding_model_path=str(WAKE_SHADOW_EMBEDDING_PATH),
    )
    return model, np''',
        '''    model_kwargs: dict[str, Any] = {
        "wakeword_models": [str(WAKE_SHADOW_MODEL_PATH)],
        "inference_framework": "onnx",
        "melspec_model_path": str(WAKE_SHADOW_MELSPEC_PATH),
        "embedding_model_path": str(WAKE_SHADOW_EMBEDDING_PATH),
    }
    verifier_enabled = WAKE_VERIFIER_PATH.is_file()
    if verifier_enabled:
        model_kwargs["custom_verifier_models"] = {WAKE_SHADOW_MODEL_PATH.stem: str(WAKE_VERIFIER_PATH)}
        model_kwargs["custom_verifier_threshold"] = 0.10
    model = OpenWakeWordModel(**model_kwargs)
    return model, np, verifier_enabled''',
        "verifier-aware model",
    )
    backend = replace_once(
        backend,
        '''        model, np = await asyncio.to_thread(_new_wake_shadow_model)
        model_name = next(iter(model.models.keys()), "hey_zbrano")
        await websocket.send_json({"type": "ready", "model": model_name})''',
        '''        model, np, verifier_enabled = await asyncio.to_thread(_new_wake_shadow_model)
        model_name = next(iter(model.models.keys()), "hey_zbrano")
        await websocket.send_json({"type": "ready", "model": model_name, "verifier": verifier_enabled})''',
        "verifier websocket status",
    )

    speech_marker = '''@app.post("/api/voice/speech")'''
    calibration_backend = r'''def _wake_calibration_status() -> dict[str, Any]:
    positive = len(list(WAKE_POSITIVE_DIR.glob("*.wav"))) if WAKE_POSITIVE_DIR.is_dir() else 0
    negative = len(list(WAKE_NEGATIVE_DIR.glob("*.wav"))) if WAKE_NEGATIVE_DIR.is_dir() else 0
    return {
        "positive": positive,
        "negative": negative,
        "required_each": 20,
        "ready_to_train": positive >= 20 and negative >= 20,
        "verifier_trained": WAKE_VERIFIER_PATH.is_file(),
    }


@app.get("/api/voice/wake-calibration")
async def get_wake_calibration() -> dict[str, Any]:
    return _wake_calibration_status()


@app.post("/api/voice/wake-calibration/{label}")
async def save_wake_calibration(label: str, audio: UploadFile = File(...)) -> dict[str, Any]:
    """Save one explicitly requested local calibration clip as bounded PCM WAV."""
    import io
    import time
    import wave

    destination = {"positive": WAKE_POSITIVE_DIR, "negative": WAKE_NEGATIVE_DIR}.get(label)
    if destination is None:
        raise HTTPException(status_code=400, detail="Calibration label must be positive or negative")
    content = await audio.read(256001)
    await audio.close()
    if len(content) > 256000:
        raise HTTPException(status_code=413, detail="Wake calibration clip is too large")
    try:
        with wave.open(io.BytesIO(content), "rb") as clip:
            valid = (
                clip.getnchannels() == 1
                and clip.getsampwidth() == 2
                and clip.getframerate() == 16000
                and 16000 <= clip.getnframes() <= 80000
                and clip.getcomptype() == "NONE"
            )
    except (EOFError, wave.Error):
        valid = False
    if not valid:
        raise HTTPException(status_code=422, detail="Expected 1–5 seconds of mono 16 kHz 16-bit PCM WAV audio")
    destination.mkdir(parents=True, exist_ok=True)
    (destination / f"{time.time_ns()}.wav").write_bytes(content)
    return {"saved": True, **_wake_calibration_status()}


def _train_personal_wake_verifier() -> None:
    import pickle
    import numpy as np
    from openwakeword.custom_verifier_model import get_reference_clip_features, train_verifier_model
    from openwakeword.model import Model as OpenWakeWordModel

    positive_paths = sorted(WAKE_POSITIVE_DIR.glob("*.wav"))
    negative_paths = sorted(WAKE_NEGATIVE_DIR.glob("*.wav"))
    if len(positive_paths) < 20 or len(negative_paths) < 20:
        raise ValueError("Collect at least 20 positive and 20 other-speech samples first")
    model = OpenWakeWordModel(
        wakeword_models=[str(WAKE_SHADOW_MODEL_PATH)],
        inference_framework="onnx",
        melspec_model_path=str(WAKE_SHADOW_MELSPEC_PATH),
        embedding_model_path=str(WAKE_SHADOW_EMBEDDING_PATH),
    )
    model_name = next(iter(model.models.keys()))
    positive_parts = [
        get_reference_clip_features(str(path), model, model_name, threshold=0.20, N=5)
        for path in positive_paths
    ]
    positive_parts = [part for part in positive_parts if part.shape[0]]
    if not positive_parts:
        raise ValueError("The base model could not find Hey ZBRANO in the positive recordings")
    negative_parts = [
        get_reference_clip_features(str(path), model, model_name, threshold=0.0, N=1)
        for path in negative_paths
    ]
    negative_parts = [part for part in negative_parts if part.shape[0]]
    if not negative_parts:
        raise ValueError("No usable other-speech features were found")
    positive_features = np.vstack(positive_parts)
    negative_features = np.vstack(negative_parts)
    verifier = train_verifier_model(
        np.vstack((positive_features, negative_features)),
        np.array([1] * positive_features.shape[0] + [0] * negative_features.shape[0]),
    )
    WAKE_CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)
    temporary = WAKE_VERIFIER_PATH.with_suffix(".tmp")
    with temporary.open("wb") as output:
        pickle.dump(verifier, output)
    temporary.replace(WAKE_VERIFIER_PATH)


@app.post("/api/voice/wake-calibration/train")
async def train_wake_calibration() -> dict[str, Any]:
    async with WAKE_VERIFIER_TRAIN_LOCK:
        try:
            await asyncio.to_thread(_train_personal_wake_verifier)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Personal wake verifier training failed: {exc}") from exc
    return {"trained": True, **_wake_calibration_status()}


@app.delete("/api/voice/wake-calibration")
async def reset_wake_calibration() -> dict[str, Any]:
    """Delete only ZBRANO-owned calibration clips and verifier after UI confirmation."""
    for directory in (WAKE_POSITIVE_DIR, WAKE_NEGATIVE_DIR):
        if directory.is_dir():
            for clip in directory.glob("*.wav"):
                clip.unlink(missing_ok=True)
    WAKE_VERIFIER_PATH.unlink(missing_ok=True)
    return {"reset": True, **_wake_calibration_status()}


'''
    backend = replace_once(backend, speech_marker, calibration_backend + speech_marker, "calibration endpoints")

    frontend = replace_once(
        frontend,
        '''          <div class="settings-actions"><button id="wake-shadow-mark-false" type="button">Mark last detection false</button><button id="wake-shadow-reset" type="button">Reset shadow statistics</button></div>
          <p id="wake-shadow-message" class="muted">Enable wake listening and shadow testing to begin local scoring.</p>''',
        '''          <div class="settings-actions"><button id="wake-shadow-mark-false" type="button">Mark last detection false</button><button id="wake-shadow-reset" type="button">Reset shadow statistics</button></div>
          <p id="wake-shadow-message" class="muted">Enable wake listening and shadow testing to begin local scoring.</p>
          <section class="wake-verifier-calibration">
            <h4>PERSONAL VOICE CALIBRATION</h4>
            <p>Record your wake phrase and ordinary speech. Clips remain in ZBRANO’s private add-on data and are saved only when you press a recording or false-trigger button.</p>
            <div class="wake-calibration-counts"><span>Hey ZBRANO<strong id="wake-positive-count">0 / 20</strong></span><span>Other speech<strong id="wake-negative-count">0 / 20</strong></span><span>Verifier<strong id="wake-verifier-state">Not trained</strong></span></div>
            <div class="settings-actions"><button id="wake-record-positive" type="button">Record “Hey ZBRANO”</button><button id="wake-record-negative" type="button">Record other speech</button><button id="wake-train-verifier" type="button" disabled>Train personal verifier</button><button id="wake-reset-calibration" type="button">Delete calibration</button></div>
            <p id="wake-calibration-message" class="muted">Collect 20 samples of each type. Use different distances and natural speaking styles.</p>
          </section>''',
        "personal verifier panel",
    )

    frontend = replace_once(
        frontend,
        '''  let wakeShadowSocket=null,wakeShadowProcessor=null,wakeShadowMute=null,wakeShadowPcm=[],wakeShadowAbove=0,wakeShadowLatched=false,wakeShadowSaveTimer=null;''',
        '''  let wakeShadowSocket=null,wakeShadowProcessor=null,wakeShadowMute=null,wakeShadowPcm=[],wakeShadowAbove=0,wakeShadowLatched=false,wakeShadowSaveTimer=null;
  let wakeShadowHistory=[],wakeShadowLastCandidate=null,wakeCalibrationCapture=null,wakeCalibrationBusy=false;''',
        "calibration audio state",
    )

    frontend = replace_once(
        frontend,
        '''  const WAKE_SHADOW_KEY="zbrano_wake_shadow_v1";''',
        '''  const WAKE_SHADOW_KEY="zbrano_wake_shadow_v1";
  const wakePositiveCount=document.getElementById("wake-positive-count"),wakeNegativeCount=document.getElementById("wake-negative-count"),wakeVerifierState=document.getElementById("wake-verifier-state"),wakeCalibrationMessage=document.getElementById("wake-calibration-message"),wakeTrainVerifier=document.getElementById("wake-train-verifier");''',
        "calibration controls",
    )

    frontend = replace_once(
        frontend,
        '''    if(wakeShadowMute){try{wakeShadowMute.disconnect()}catch{}}wakeShadowMute=null;wakeShadowPcm=[];wakeShadowAbove=0;wakeShadowLatched=false;''',
        '''    if(wakeShadowMute){try{wakeShadowMute.disconnect()}catch{}}wakeShadowMute=null;wakeShadowPcm=[];wakeShadowHistory=[];wakeShadowLastCandidate=null;wakeCalibrationCapture=null;wakeShadowAbove=0;wakeShadowLatched=false;''',
        "calibration cleanup",
    )

    frontend = replace_once(
        frontend,
        '''  function handleWakeShadowScore(score){''',
        r'''  function encodeWakeCalibrationWav(samples){
    const buffer=new ArrayBuffer(44+samples.length*2),view=new DataView(buffer);const text=(offset,value)=>{for(let i=0;i<value.length;i++)view.setUint8(offset+i,value.charCodeAt(i))};
    text(0,"RIFF");view.setUint32(4,36+samples.length*2,true);text(8,"WAVE");text(12,"fmt ");view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,16000,true);view.setUint32(28,32000,true);view.setUint16(32,2,true);view.setUint16(34,16,true);text(36,"data");view.setUint32(40,samples.length*2,true);for(let i=0;i<samples.length;i++)view.setInt16(44+i*2,samples[i],true);return new Blob([buffer],{type:"audio/wav"});
  }
  async function loadWakeCalibration(){
    try{const response=await fetch("api/voice/wake-calibration",{cache:"no-store"}),data=await response.json();if(!response.ok)throw new Error(data.detail||`HTTP ${response.status}`);wakePositiveCount.textContent=`${data.positive} / ${data.required_each}`;wakeNegativeCount.textContent=`${data.negative} / ${data.required_each}`;wakeVerifierState.textContent=data.verifier_trained?"Trained":"Not trained";wakeTrainVerifier.disabled=!data.ready_to_train||wakeCalibrationBusy;return data}catch(error){wakeCalibrationMessage.textContent=`Calibration status unavailable: ${error.message||error}`;return null}
  }
  async function uploadWakeCalibration(label,samples,message){
    if(!samples||samples.length<16000)return;wakeCalibrationBusy=true;wakeCalibrationMessage.textContent="Saving calibration clip locally...";
    try{const body=new FormData();body.append("audio",encodeWakeCalibrationWav(samples),`${label}.wav`);const response=await fetch(`api/voice/wake-calibration/${label}`,{method:"POST",body}),data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(data.detail||`HTTP ${response.status}`);wakeCalibrationMessage.textContent=message}catch(error){wakeCalibrationMessage.textContent=`Calibration clip failed: ${error.message||error}`}finally{wakeCalibrationBusy=false;await loadWakeCalibration()}
  }
  function recordWakeCalibration(label){
    if(wakeCalibrationBusy||wakeCalibrationCapture)return;if(!wakeShadowSocket||wakeShadowSocket.readyState!==WebSocket.OPEN){wakeCalibrationMessage.textContent="Enable wake listening and Local Wake Shadow Test first.";return}
    wakeCalibrationCapture={label,samples:[]};wakeCalibrationMessage.textContent=label==="positive"?'Recording now — say “Hey ZBRANO” once.':"Recording now — speak a normal sentence without the wake phrase.";
  }
  function finishWakeCalibrationCapture(){
    const capture=wakeCalibrationCapture;wakeCalibrationCapture=null;if(!capture)return;uploadWakeCalibration(capture.label,new Int16Array(capture.samples),capture.label==="positive"?'Wake-phrase sample saved. Record another with a natural variation.':"Other-speech sample saved. Use a different normal sentence next.");
  }
  function handleWakeShadowScore(score){''',
        "calibration WAV and API workflow",
    )
    frontend = replace_once(
        frontend,
        '''if(wakeShadowAbove>=2&&!wakeShadowLatched){wakeShadowLatched=true;wakeShadowStats.detections++;wakeShadowMessage.textContent=`Silent detection ${wakeShadowStats.detections} at ${score.toFixed(3)}. Chat was not activated.`}''',
        '''if(wakeShadowAbove>=2&&!wakeShadowLatched){wakeShadowLatched=true;wakeShadowStats.detections++;wakeShadowLastCandidate=new Int16Array(wakeShadowHistory.slice(-64000));wakeShadowMessage.textContent=`Silent detection ${wakeShadowStats.detections} at ${score.toFixed(3)}. Chat was not activated.`}''',
        "false-trigger candidate retention",
    )
    frontend = replace_once(
        frontend,
        '''    processor.onaudioprocess=event=>{if(socket.readyState!==WebSocket.OPEN)return;const converted=resampleWakeShadow(event.inputBuffer.getChannelData(0),context.sampleRate);for(const sample of converted)wakeShadowPcm.push(sample);while(wakeShadowPcm.length>=1280&&socket.bufferedAmount<65536){const frame=new Int16Array(wakeShadowPcm.splice(0,1280));socket.send(frame.buffer)}};''',
        '''    processor.onaudioprocess=event=>{if(socket.readyState!==WebSocket.OPEN)return;const converted=resampleWakeShadow(event.inputBuffer.getChannelData(0),context.sampleRate);for(const sample of converted){wakeShadowPcm.push(sample);wakeShadowHistory.push(sample);if(wakeCalibrationCapture)wakeCalibrationCapture.samples.push(sample)}if(wakeShadowHistory.length>80000)wakeShadowHistory.splice(0,wakeShadowHistory.length-80000);if(wakeCalibrationCapture&&wakeCalibrationCapture.samples.length>=56000)finishWakeCalibrationCapture();while(wakeShadowPcm.length>=1280&&socket.bufferedAmount<65536){const frame=new Int16Array(wakeShadowPcm.splice(0,1280));socket.send(frame.buffer)}};''',
        "bounded manual calibration capture",
    )
    frontend = replace_once(
        frontend,
        '''wakeShadowMessage.textContent="Local model ready. Scores are silent and cannot activate chat.";wakeShadowSaveTimer=setInterval(saveWakeShadow,5000)''',
        '''wakeShadowMessage.textContent=data.verifier?"Personal verifier ready in silent shadow mode.":"Local base model ready. Scores are silent and cannot activate chat.";wakeShadowSaveTimer=setInterval(saveWakeShadow,5000);loadWakeCalibration()''',
        "verifier-ready display",
    )

    frontend = replace_once(
        frontend,
        '''  document.getElementById("wake-shadow-mark-false").addEventListener("click",()=>{if(wakeShadowStats.detections>wakeShadowStats.falseDetections){wakeShadowStats.falseDetections++;wakeShadowMessage.textContent="Last silent detection marked as false.";saveWakeShadow()}});''',
        '''  document.getElementById("wake-shadow-mark-false").addEventListener("click",async()=>{if(wakeShadowStats.detections>wakeShadowStats.falseDetections){wakeShadowStats.falseDetections++;saveWakeShadow();if(wakeShadowLastCandidate){const candidate=wakeShadowLastCandidate;wakeShadowLastCandidate=null;await uploadWakeCalibration("negative",candidate,"False-trigger clip saved as personal-verifier negative evidence.")}else wakeShadowMessage.textContent="False detection counted; no transient candidate audio remained."}});''',
        "explicit false-trigger persistence",
    )
    listener_marker = '''  wakeEnabled.addEventListener("change",()=>{'''
    calibration_listeners = '''  document.getElementById("wake-record-positive").addEventListener("click",()=>recordWakeCalibration("positive"));
  document.getElementById("wake-record-negative").addEventListener("click",()=>recordWakeCalibration("negative"));
  wakeTrainVerifier.addEventListener("click",async()=>{if(wakeCalibrationBusy)return;wakeCalibrationBusy=true;wakeTrainVerifier.disabled=true;wakeCalibrationMessage.textContent="Training the personal verifier locally. Keep this page open...";try{const response=await fetch("api/voice/wake-calibration/train",{method:"POST"}),data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(data.detail||`HTTP ${response.status}`);wakeCalibrationMessage.textContent="Personal verifier trained. Restarting silent shadow evaluation...";await loadWakeCalibration();stopWake();if(wakeEnabled.checked)scheduleWake()}catch(error){wakeCalibrationMessage.textContent=`Verifier training failed: ${error.message||error}`}finally{wakeCalibrationBusy=false;await loadWakeCalibration()}});
  document.getElementById("wake-reset-calibration").addEventListener("click",async()=>{if(!confirm("Delete all personal wake clips and the trained verifier?"))return;wakeCalibrationBusy=true;try{const response=await fetch("api/voice/wake-calibration",{method:"DELETE"}),data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(data.detail||`HTTP ${response.status}`);wakeCalibrationMessage.textContent="Personal wake calibration deleted.";await loadWakeCalibration();stopWake();if(wakeEnabled.checked)scheduleWake()}catch(error){wakeCalibrationMessage.textContent=`Calibration reset failed: ${error.message||error}`}finally{wakeCalibrationBusy=false}});
  loadWakeCalibration();

'''
    frontend = replace_once(frontend, listener_marker, calibration_listeners + listener_marker, "calibration listeners")

    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.103 could not locate stylesheet")
    styles = r'''
    /* v0.12.103 personal wake verifier calibration. */
    .wake-verifier-calibration{border-top:1px solid var(--line);padding-top:.7rem;display:grid;gap:.55rem}.wake-verifier-calibration h4,.wake-verifier-calibration p{margin:0}.wake-verifier-calibration h4{font-size:.72rem;letter-spacing:.08em}
    .wake-calibration-counts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.4rem}.wake-calibration-counts span{border:1px solid var(--line);border-radius:8px;padding:.4rem;font-size:.68rem;color:var(--muted)}.wake-calibration-counts strong{display:block;margin-top:.15rem;color:var(--ink)}
    @media(max-width:700px){.wake-calibration-counts{grid-template-columns:1fr}}
'''
    frontend = frontend[:style_close] + styles + frontend[style_close:]

    backend = backend.replace('version="0.12.102"', 'version="0.12.103"')
    backend = backend.replace('"version": "0.12.102"', '"version": "0.12.103"')
    frontend = frontend.replace("HUD 0.12.102", "HUD 0.12.103")

    for marker, location in [
        ('version="0.12.103"', backend),
        ('@app.post("/api/voice/wake-calibration/{label}")', backend),
        ('@app.post("/api/voice/wake-calibration/train")', backend),
        ('custom_verifier_models', backend),
        ('threshold=0.20', backend),
        ('id="wake-record-positive"', frontend),
        ('function encodeWakeCalibrationWav', frontend),
        ('False-trigger clip saved', frontend),
        ('Personal verifier ready in silent shadow mode', frontend),
        ('HUD 0.12.103', frontend),
    ]:
        require(location, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
