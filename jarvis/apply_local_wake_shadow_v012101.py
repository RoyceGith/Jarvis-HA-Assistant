import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.101 shadow patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.101 shadow patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    voice_marker = '''@app.post("/api/voice/speech")'''
    shadow_backend = r'''WAKE_SHADOW_MODEL_PATH = Path(__file__).resolve().parent.parent / "models/wakeword/hey_zbrano.onnx"


def _new_wake_shadow_model() -> tuple[Any, Any]:
    """Create an isolated streaming detector for one browser microphone."""
    import numpy as np
    from openwakeword.model import Model as OpenWakeWordModel

    if not WAKE_SHADOW_MODEL_PATH.is_file():
        raise RuntimeError("ZBRANO wake-word model is missing")
    model = OpenWakeWordModel(
        wakeword_models=[str(WAKE_SHADOW_MODEL_PATH)],
        inference_framework="onnx",
    )
    return model, np


@app.websocket("/api/voice/wake-shadow")
async def wake_shadow_websocket(websocket: WebSocket) -> None:
    """Score transient 16 kHz PCM frames locally; never retain audio or activate chat."""
    await websocket.accept()
    try:
        model, np = await asyncio.to_thread(_new_wake_shadow_model)
        model_name = next(iter(model.models.keys()), "hey_zbrano")
        await websocket.send_json({"type": "ready", "model": model_name})
        while True:
            packet = await websocket.receive_bytes()
            if not packet or len(packet) > 32768 or len(packet) % 2:
                continue
            samples = np.frombuffer(packet, dtype=np.int16)
            prediction = await asyncio.to_thread(model.predict, samples)
            score = max((float(value) for value in prediction.values()), default=0.0)
            await websocket.send_json({"type": "score", "score": max(0.0, min(1.0, score))})
    except WebSocketDisconnect:
        return
    except Exception as exc:
        with contextlib.suppress(Exception):
            await websocket.send_json({"type": "error", "message": str(exc)})
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()


'''
    backend = replace_once(backend, voice_marker, shadow_backend + voice_marker, "voice endpoint insertion")

    frontend = replace_once(
        frontend,
        '''        <p id="wake-word-status" class="muted">Wake listening is off. It works only while this page is open and microphone permission is granted.</p>''',
        '''        <p id="wake-word-status" class="muted">Wake listening is off. It works only while this page is open and microphone permission is granted.</p>
        <section class="wake-shadow-panel" aria-labelledby="wake-shadow-title">
          <div class="wake-shadow-heading"><div><h4 id="wake-shadow-title">LOCAL WAKE SHADOW TEST</h4><small>Measures the trained model without activating chat or using OpenAI.</small></div><span id="wake-shadow-health" data-state="off">OFF</span></div>
          <label class="toggle-row"><input id="wake-shadow-enabled" type="checkbox"> Evaluate “Hey ZBRANO” silently while wake listening is enabled</label>
          <label class="wake-shadow-threshold" for="wake-shadow-threshold">Detection threshold <output id="wake-shadow-threshold-value">0.50</output><input id="wake-shadow-threshold" type="range" min="0.20" max="0.95" value="0.50" step="0.01"></label>
          <div class="wake-shadow-metrics">
            <span>Live<strong id="wake-shadow-score">0.000</strong></span><span>Peak<strong id="wake-shadow-peak">0.000</strong></span><span>Detections<strong id="wake-shadow-detections">0</strong></span><span>Marked false<strong id="wake-shadow-false">0</strong></span><span>Runtime<strong id="wake-shadow-runtime">0m</strong></span>
          </div>
          <div class="settings-actions"><button id="wake-shadow-mark-false" type="button">Mark last detection false</button><button id="wake-shadow-reset" type="button">Reset shadow statistics</button></div>
          <p id="wake-shadow-message" class="muted">Enable wake listening and shadow testing to begin local scoring.</p>
        </section>''',
        "shadow settings panel",
    )

    state_old = '''  let wakeFallbackChunks=[],wakeFallbackSpeechStart=0,wakeFallbackLastVoice=0,wakeFallbackVoiceFrames=0,wakeFallbackBusy=false;'''
    state_new = '''  let wakeFallbackChunks=[],wakeFallbackSpeechStart=0,wakeFallbackLastVoice=0,wakeFallbackVoiceFrames=0,wakeFallbackBusy=false;
  let wakeShadowSocket=null,wakeShadowProcessor=null,wakeShadowMute=null,wakeShadowPcm=[],wakeShadowAbove=0,wakeShadowLatched=false,wakeShadowSaveTimer=null;'''
    frontend = replace_once(frontend, state_old, state_new, "shadow runtime state")

    controls_old = '''  const wakeFallbackAttempts=[];
  const WAKE_FALLBACK_LIMIT=20;'''
    controls_new = '''  const wakeFallbackAttempts=[];
  const WAKE_FALLBACK_LIMIT=20;
  const wakeShadowEnabled=document.getElementById("wake-shadow-enabled"),wakeShadowThreshold=document.getElementById("wake-shadow-threshold");
  const wakeShadowThresholdValue=document.getElementById("wake-shadow-threshold-value"),wakeShadowHealth=document.getElementById("wake-shadow-health");
  const wakeShadowScore=document.getElementById("wake-shadow-score"),wakeShadowPeak=document.getElementById("wake-shadow-peak"),wakeShadowDetections=document.getElementById("wake-shadow-detections");
  const wakeShadowFalse=document.getElementById("wake-shadow-false"),wakeShadowRuntime=document.getElementById("wake-shadow-runtime"),wakeShadowMessage=document.getElementById("wake-shadow-message");
  const WAKE_SHADOW_KEY="zbrano_wake_shadow_v1";
  let wakeShadowStats={peak:0,detections:0,falseDetections:0,frames:0,runtimeMs:0,startedAt:0};
  try{wakeShadowStats={...wakeShadowStats,...JSON.parse(localStorage.getItem(WAKE_SHADOW_KEY)||"{}")}}catch{}

  function renderWakeShadow(score=0){
    const activeMs=Number(wakeShadowStats.runtimeMs||0)+(wakeShadowStats.startedAt?Date.now()-wakeShadowStats.startedAt:0);
    wakeShadowScore.textContent=Number(score||0).toFixed(3);wakeShadowPeak.textContent=Number(wakeShadowStats.peak||0).toFixed(3);
    wakeShadowDetections.textContent=String(wakeShadowStats.detections||0);wakeShadowFalse.textContent=String(wakeShadowStats.falseDetections||0);
    wakeShadowRuntime.textContent=activeMs<3600000?`${Math.floor(activeMs/60000)}m`:`${(activeMs/3600000).toFixed(1)}h`;
  }
  function saveWakeShadow(){
    const snapshot={...wakeShadowStats};if(snapshot.startedAt){snapshot.runtimeMs=Number(snapshot.runtimeMs||0)+Date.now()-snapshot.startedAt;snapshot.startedAt=Date.now();wakeShadowStats.startedAt=snapshot.startedAt}
    localStorage.setItem(WAKE_SHADOW_KEY,JSON.stringify(snapshot));wakeShadowStats={...snapshot};renderWakeShadow(Number(wakeShadowScore.textContent)||0);
  }
  function stopWakeShadow(){
    if(wakeShadowSaveTimer)clearInterval(wakeShadowSaveTimer);wakeShadowSaveTimer=null;
    if(wakeShadowProcessor){wakeShadowProcessor.onaudioprocess=null;try{wakeShadowProcessor.disconnect()}catch{}}wakeShadowProcessor=null;
    if(wakeShadowMute){try{wakeShadowMute.disconnect()}catch{}}wakeShadowMute=null;wakeShadowPcm=[];wakeShadowAbove=0;wakeShadowLatched=false;
    if(wakeShadowSocket){try{wakeShadowSocket.close()}catch{}}wakeShadowSocket=null;
    if(wakeShadowStats.startedAt){wakeShadowStats.runtimeMs=Number(wakeShadowStats.runtimeMs||0)+Date.now()-wakeShadowStats.startedAt;wakeShadowStats.startedAt=0;localStorage.setItem(WAKE_SHADOW_KEY,JSON.stringify(wakeShadowStats))}
    wakeShadowHealth.textContent=wakeShadowEnabled.checked?"PAUSED":"OFF";wakeShadowHealth.dataset.state="off";renderWakeShadow(0);
  }
  function resampleWakeShadow(input,inputRate){
    const ratio=inputRate/16000,length=Math.max(1,Math.floor(input.length/ratio)),output=new Int16Array(length);
    for(let index=0;index<length;index++){const start=Math.floor(index*ratio),end=Math.min(input.length,Math.floor((index+1)*ratio));let sum=0;for(let sample=start;sample<end;sample++)sum+=input[sample];const value=sum/Math.max(1,end-start);output[index]=Math.max(-32768,Math.min(32767,Math.round(value*32767)))}return output;
  }
  function handleWakeShadowScore(score){
    score=Math.max(0,Math.min(1,Number(score)||0));wakeShadowStats.frames++;wakeShadowStats.peak=Math.max(Number(wakeShadowStats.peak||0),score);
    const threshold=Number(wakeShadowThreshold.value||.5);wakeShadowAbove=score>=threshold?wakeShadowAbove+1:0;
    if(wakeShadowAbove>=2&&!wakeShadowLatched){wakeShadowLatched=true;wakeShadowStats.detections++;wakeShadowMessage.textContent=`Silent detection ${wakeShadowStats.detections} at ${score.toFixed(3)}. Chat was not activated.`}
    if(score<threshold*.55)wakeShadowLatched=false;renderWakeShadow(score);
  }
  function startWakeShadow(context,source){
    stopWakeShadow();if(!wakeShadowEnabled.checked)return;
    const endpoint=new URL("api/voice/wake-shadow",document.baseURI);endpoint.protocol=endpoint.protocol==="https:"?"wss:":"ws:";
    const socket=new WebSocket(endpoint);wakeShadowSocket=socket;socket.binaryType="arraybuffer";wakeShadowHealth.textContent="STARTING";wakeShadowHealth.dataset.state="starting";
    const processor=context.createScriptProcessor(4096,1,1),mute=context.createGain();mute.gain.value=0;wakeShadowProcessor=processor;wakeShadowMute=mute;source.connect(processor);processor.connect(mute);mute.connect(context.destination);
    processor.onaudioprocess=event=>{if(socket.readyState!==WebSocket.OPEN)return;const converted=resampleWakeShadow(event.inputBuffer.getChannelData(0),context.sampleRate);for(const sample of converted)wakeShadowPcm.push(sample);while(wakeShadowPcm.length>=1280&&socket.bufferedAmount<65536){const frame=new Int16Array(wakeShadowPcm.splice(0,1280));socket.send(frame.buffer)}};
    socket.addEventListener("message",event=>{let data;try{data=JSON.parse(event.data)}catch{return}if(data.type==="ready"){wakeShadowStats.startedAt=Date.now();wakeShadowHealth.textContent="SHADOW";wakeShadowHealth.dataset.state="active";wakeShadowMessage.textContent="Local model ready. Scores are silent and cannot activate chat.";wakeShadowSaveTimer=setInterval(saveWakeShadow,5000)}else if(data.type==="score")handleWakeShadowScore(data.score);else if(data.type==="error"){wakeShadowHealth.textContent="ERROR";wakeShadowHealth.dataset.state="error";wakeShadowMessage.textContent=`Local model unavailable: ${data.message||"unknown error"}`}});
    socket.addEventListener("error",()=>{wakeShadowHealth.textContent="ERROR";wakeShadowHealth.dataset.state="error";wakeShadowMessage.textContent="Local shadow detector could not connect."});
    socket.addEventListener("close",()=>{if(wakeShadowSocket===socket){wakeShadowSocket=null;if(wakeShadowEnabled.checked){wakeShadowHealth.textContent="PAUSED";wakeShadowHealth.dataset.state="off"}}});
  }
  wakeShadowEnabled.checked=localStorage.getItem("zbrano_wake_shadow_enabled")==="true";wakeShadowThreshold.value=localStorage.getItem("zbrano_wake_shadow_threshold")||"0.50";wakeShadowThresholdValue.textContent=Number(wakeShadowThreshold.value).toFixed(2);renderWakeShadow();'''
    frontend = replace_once(frontend, controls_old, controls_new, "shadow controls")

    cleanup_old = '''    if(wakeFallbackContext)wakeFallbackContext.close().catch(()=>{});
    wakeFallbackStream=null;wakeFallbackContext=null;wakeFallbackAnalyser=null;wakeFallbackRecorder=null;wakeFallbackChunks=[];'''
    cleanup_new = '''    stopWakeShadow();
    if(wakeFallbackContext)wakeFallbackContext.close().catch(()=>{});
    wakeFallbackStream=null;wakeFallbackContext=null;wakeFallbackAnalyser=null;wakeFallbackRecorder=null;wakeFallbackChunks=[];'''
    frontend = replace_once(frontend, cleanup_old, cleanup_new, "shadow cleanup")

    frontend = replace_once(
        frontend,
        '''  function sampleWakeFallback(){
    if(!wakeFallbackAnalyser)return;''',
        '''  function sampleWakeFallback(){
    if(!wakeFallbackAnalyser||wakeShadowEnabled.checked)return;''',
        "exclusive local shadow scoring",
    )

    source_old = '''      const context=new AudioContextClass();await context.resume();const analyser=context.createAnalyser();analyser.fftSize=512;context.createMediaStreamSource(stream).connect(analyser);'''
    source_new = '''      const context=new AudioContextClass();await context.resume();const analyser=context.createAnalyser();analyser.fftSize=512;const source=context.createMediaStreamSource(stream);source.connect(analyser);'''
    frontend = replace_once(frontend, source_old, source_new, "shared microphone source")

    startup_old = '''      wakeNoiseFloor=.008;wakeFallbackCalibratingUntil=performance.now()+2500;wakeFallbackPeak=0;
      wakeFallbackTimer=setInterval(sampleWakeFallback,80);status("Calibrating reliable wake microphone...","listening");'''
    startup_new = '''      wakeNoiseFloor=.008;wakeFallbackCalibratingUntil=performance.now()+2500;wakeFallbackPeak=0;
      startWakeShadow(context,source);
      wakeFallbackTimer=setInterval(sampleWakeFallback,80);status("Calibrating reliable wake microphone...","listening");'''
    frontend = replace_once(frontend, startup_old, startup_new, "shadow startup")

    listener_marker = '''  wakeEnabled.addEventListener("change",()=>{'''
    shadow_listeners = '''  wakeShadowEnabled.addEventListener("change",()=>{localStorage.setItem("zbrano_wake_shadow_enabled",String(wakeShadowEnabled.checked));stopWake();if(wakeEnabled.checked)scheduleWake();else renderWakeShadow()});
  wakeShadowThreshold.addEventListener("input",()=>{wakeShadowThresholdValue.textContent=Number(wakeShadowThreshold.value).toFixed(2);localStorage.setItem("zbrano_wake_shadow_threshold",wakeShadowThreshold.value);wakeShadowAbove=0;wakeShadowLatched=false});
  document.getElementById("wake-shadow-mark-false").addEventListener("click",()=>{if(wakeShadowStats.detections>wakeShadowStats.falseDetections){wakeShadowStats.falseDetections++;wakeShadowMessage.textContent="Last silent detection marked as false.";saveWakeShadow()}});
  document.getElementById("wake-shadow-reset").addEventListener("click",()=>{wakeShadowStats={peak:0,detections:0,falseDetections:0,frames:0,runtimeMs:0,startedAt:wakeShadowSocket?Date.now():0};wakeShadowAbove=0;wakeShadowLatched=false;saveWakeShadow();wakeShadowMessage.textContent="Shadow statistics reset."});

'''
    frontend = replace_once(frontend, listener_marker, shadow_listeners + listener_marker, "shadow event listeners")

    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.101 shadow patch could not locate stylesheet")
    styles = r'''
    /* v0.12.101 local OpenWakeWord shadow calibration. */
    .wake-shadow-panel{margin-top:.75rem;padding:.75rem;border:1px solid var(--line);border-radius:10px;display:grid;gap:.65rem;background:color-mix(in srgb,var(--panel) 88%,transparent)}
    .wake-shadow-heading{display:flex;justify-content:space-between;gap:.75rem;align-items:flex-start}.wake-shadow-heading h4{margin:0 0 .2rem;font-size:.75rem;letter-spacing:.08em}.wake-shadow-heading small{display:block}
    #wake-shadow-health{font-size:.68rem;letter-spacing:.08em;border:1px solid var(--line);border-radius:999px;padding:.18rem .45rem}#wake-shadow-health[data-state="active"]{color:var(--cyan);border-color:var(--cyan)}#wake-shadow-health[data-state="error"]{color:var(--danger);border-color:var(--danger)}
    .wake-shadow-threshold{display:grid;grid-template-columns:1fr auto;gap:.35rem .65rem;align-items:center}.wake-shadow-threshold input{grid-column:1/-1;width:100%}
    .wake-shadow-metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:.4rem}.wake-shadow-metrics span{border:1px solid var(--line);border-radius:8px;padding:.4rem;font-size:.68rem;color:var(--muted)}.wake-shadow-metrics strong{display:block;margin-top:.15rem;font-size:.88rem;color:var(--ink)}
    @media(max-width:700px){.wake-shadow-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}
'''
    frontend = frontend[:style_close] + styles + frontend[style_close:]

    for marker, location in [
        ('@app.websocket("/api/voice/wake-shadow")', backend),
        ('OpenWakeWordModel(', backend),
        ('id="wake-shadow-enabled"', frontend),
        ('function startWakeShadow(context,source)', frontend),
        ('if(!wakeFallbackAnalyser||wakeShadowEnabled.checked)return', frontend),
        ('Silent detection', frontend),
        ('Chat was not activated', frontend),
        ('wake-shadow-metrics', frontend),
        ('HUD 0.12.101', frontend),
    ]:
        require(location, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
