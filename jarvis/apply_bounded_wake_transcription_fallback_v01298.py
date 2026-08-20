import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.98 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.98 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    frontend = replace_once(
        frontend,
        '''  function stopRecognition(instance){if(!instance)return;instance.onend=null;try{instance.abort()}catch{}}
  function stopWake(){if(wakeRestart)clearTimeout(wakeRestart);wakeRestart=null;stopRecognition(wakeRecognition);wakeRecognition=null}''',
        '''  let wakeFallbackStream=null,wakeFallbackContext=null,wakeFallbackAnalyser=null,wakeFallbackRecorder=null,wakeFallbackTimer=null;
  let wakeFallbackChunks=[],wakeFallbackSpeechStart=0,wakeFallbackLastVoice=0,wakeFallbackVoiceFrames=0,wakeFallbackBusy=false;
  let wakeFallbackMode="wake",wakeFallbackGeneration=0,wakeFallbackCommandTimer=null,wakeNativeMatchAt=0,wakeFallbackStarting=false,wakeNoiseFloor=.008;
  const wakeFallbackAttempts=[];
  const WAKE_FALLBACK_LIMIT=20;

  function stopRecognition(instance){if(!instance)return;instance.onend=null;try{instance.abort()}catch{}}
  function clearWakeFallbackCommandTimer(){if(wakeFallbackCommandTimer)clearTimeout(wakeFallbackCommandTimer);wakeFallbackCommandTimer=null}
  function stopWakeFallback(){
    wakeFallbackGeneration++;clearWakeFallbackCommandTimer();
    if(wakeFallbackTimer)clearInterval(wakeFallbackTimer);wakeFallbackTimer=null;
    if(wakeFallbackRecorder){wakeFallbackRecorder.ondataavailable=null;try{if(wakeFallbackRecorder.state!=="inactive")wakeFallbackRecorder.stop()}catch{}}
    if(wakeFallbackStream)wakeFallbackStream.getTracks().forEach(track=>track.stop());
    if(wakeFallbackContext)wakeFallbackContext.close().catch(()=>{});
    wakeFallbackStream=null;wakeFallbackContext=null;wakeFallbackAnalyser=null;wakeFallbackRecorder=null;wakeFallbackChunks=[];
    wakeFallbackSpeechStart=0;wakeFallbackLastVoice=0;wakeFallbackVoiceFrames=0;wakeFallbackBusy=false;wakeFallbackMode="wake";wakeFallbackStarting=false;
  }
  function stopWake(preserveFallback=false){if(wakeRestart)clearTimeout(wakeRestart);wakeRestart=null;stopRecognition(wakeRecognition);wakeRecognition=null;if(!preserveFallback)stopWakeFallback()}

  function startFallbackCommandWindow(){
    wakeFallbackGeneration++;wakeFallbackMode="command";wakeFallbackChunks=[];wakeFallbackSpeechStart=0;wakeFallbackLastVoice=0;wakeFallbackVoiceFrames=0;
    clearWakeFallbackCommandTimer();
    wakeFallbackCommandTimer=setTimeout(()=>{wakeFallbackMode="wake";hideWakeOverlay(250);status(`No command heard - listening for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");scheduleWake()},9000);
    status("Wake phrase heard - reliable listener is waiting for your command","listening");
  }

  function fallbackRateAllowed(){
    const cutoff=Date.now()-3600000;while(wakeFallbackAttempts.length&&wakeFallbackAttempts[0]<cutoff)wakeFallbackAttempts.shift();
    if(wakeFallbackAttempts.length>=WAKE_FALLBACK_LIMIT){wakeEnabled.checked=false;status("Reliable wake listening reached its 20-transcription hourly safety limit. Turn it on again later.","error");stopWake();return false}
    wakeFallbackAttempts.push(Date.now());return true;
  }

  async function transcribeWakeFallback(blob,mode,generation){
    if(wakeFallbackBusy||generation!==wakeFallbackGeneration||!wakeEnabled.checked||!fallbackRateAllowed())return;
    wakeFallbackBusy=true;status(mode==="command"?"Transcribing your command...":"Checking detected speech for the wake phrase...","listening");
    try{
      const extension=blob.type.includes("mp4")?"m4a":"webm";const body=new FormData();body.append("audio",blob,`zbrano-wake.${extension}`);
      const response=await fetch("api/voice/transcribe",{method:"POST",body});const data=await response.json().catch(()=>({}));
      if(generation!==wakeFallbackGeneration)return;
      if(!response.ok){if(response.status!==422)throw new Error(data.detail||`HTTP ${response.status}`);return}
      const transcript=String(data.text||"").trim();if(!transcript)return;
      if(mode==="command"){
        clearWakeFallbackCommandTimer();stopWake();updateWakeOverlay(transcript);submitVoiceCommand(transcript);return;
      }
      const match=matchWakePhrase(transcript);
      if(!match){status(`Reliable listener heard "${transcript}" - waiting for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");return}
      stopRecognition(wakeRecognition);wakeRecognition=null;showWakeOverlay("WAKE PHRASE HEARD",match.command||"Speak your command...");
      if(match.command){stopWake();submitVoiceCommand(match.command)}else startFallbackCommandWindow();
    }catch(error){if(generation===wakeFallbackGeneration)status(`Reliable wake transcription unavailable: ${error.message||error}`,"error")}
    finally{wakeFallbackBusy=false}
  }

  function finishWakeFallbackUtterance(now){
    const started=wakeFallbackSpeechStart;const ended=wakeFallbackLastVoice;const mode=wakeFallbackMode;const generation=wakeFallbackGeneration;
    wakeFallbackSpeechStart=0;wakeFallbackLastVoice=0;wakeFallbackVoiceFrames=0;
    const selected=wakeFallbackChunks.filter(item=>item.time>=started-750);wakeFallbackChunks=[];
    if(ended-started<300||!selected.length)return;
    const blob=new Blob(selected.map(item=>item.data),{type:wakeFallbackRecorder?.mimeType||"audio/webm"});
    setTimeout(()=>{if(generation!==wakeFallbackGeneration)return;if(mode==="wake"&&wakeNativeMatchAt>=started)return;transcribeWakeFallback(blob,mode,generation)},400);
  }

  function sampleWakeFallback(){
    if(!wakeFallbackAnalyser||!wakeFallbackRecorder||wakeFallbackRecorder.state==="inactive")return;
    const samples=new Uint8Array(wakeFallbackAnalyser.fftSize);wakeFallbackAnalyser.getByteTimeDomainData(samples);
    let energy=0;for(const sample of samples){const value=(sample-128)/128;energy+=value*value}const rms=Math.sqrt(energy/samples.length);const now=performance.now();
    const threshold=Math.max(.018,wakeNoiseFloor*2.8);
    if(!wakeFallbackSpeechStart){
      wakeNoiseFloor=Math.min(.025,wakeNoiseFloor*.97+rms*.03);
      wakeFallbackVoiceFrames=rms>threshold?wakeFallbackVoiceFrames+1:0;
      if(wakeFallbackVoiceFrames>=2){wakeFallbackSpeechStart=now-160;wakeFallbackLastVoice=now}
      else wakeFallbackChunks=wakeFallbackChunks.filter(item=>item.time>=now-1500);
      return;
    }
    if(rms>threshold)wakeFallbackLastVoice=now;
    if(now-wakeFallbackSpeechStart>=8000||now-wakeFallbackLastVoice>=900)finishWakeFallbackUtterance(now);
  }

  async function startWakeFallback(){
    if(wakeFallbackStream||wakeFallbackStarting||!wakeEnabled.checked||document.hidden)return;wakeFallbackStarting=true;
    try{
      const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}});
      if(!wakeEnabled.checked||document.hidden){stream.getTracks().forEach(track=>track.stop());return}
      const AudioContextClass=window.AudioContext||window.webkitAudioContext;if(!AudioContextClass||!window.MediaRecorder)throw new Error("browser audio monitoring is unavailable");
      const context=new AudioContextClass();await context.resume();const analyser=context.createAnalyser();analyser.fftSize=512;context.createMediaStreamSource(stream).connect(analyser);
      const mimeType=recordingMimeType();const recorder=new MediaRecorder(stream,mimeType?{mimeType}:undefined);
      wakeFallbackStream=stream;wakeFallbackContext=context;wakeFallbackAnalyser=analyser;wakeFallbackRecorder=recorder;wakeFallbackMode="wake";wakeFallbackChunks=[];
      recorder.ondataavailable=event=>{if(event.data.size)wakeFallbackChunks.push({data:event.data,time:performance.now()})};recorder.start(250);
      wakeFallbackTimer=setInterval(sampleWakeFallback,80);status(`Reliable wake listening active for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");
    }catch(error){status(`Reliable wake listener unavailable: ${error.message||error}`,"error");stopWakeFallback()}
    finally{wakeFallbackStarting=false}
  }''',
        "bounded wake transcription fallback",
    )

    frontend = replace_once(
        frontend,
        '''    if(!wakeCanRun())return;
    stopWake();const recognition=new Recognition();''',
        '''    if(!wakeCanRun())return;
    startWakeFallback().catch(()=>{});stopWake(true);const recognition=new Recognition();''',
        "fallback startup",
    )
    frontend = replace_once(
        frontend,
        '''        const rawTranscript=event.results[index][0]?.transcript||"";const match=matchWakePhrase(rawTranscript);''',
        '''        const rawTranscript=event.results[index][0]?.transcript||"";const match=matchWakePhrase(rawTranscript);if(match)wakeNativeMatchAt=performance.now();''',
        "native match evidence",
    )
    frontend = replace_once(
        frontend,
        '''        stopWake();showWakeOverlay("WAKE PHRASE HEARD",match.command||"Speak your command...");
        if(match.command)submitVoiceCommand(match.command);else setTimeout(startCommandWindow,180);break;''',
        '''        if(match.command){stopWake();showWakeOverlay("WAKE PHRASE HEARD",match.command);submitVoiceCommand(match.command)}
        else if(wakeFallbackStream){stopRecognition(wakeRecognition);wakeRecognition=null;showWakeOverlay("WAKE PHRASE HEARD","Speak your command...");startFallbackCommandWindow()}
        else{stopWake();showWakeOverlay("WAKE PHRASE HEARD","Speak your command...");setTimeout(startCommandWindow,180)}break;''',
        "native reliable command handoff",
    )
    frontend = replace_once(
        frontend,
        '''  wakeOverlayCancel.addEventListener("click",()=>{stopRecognition(commandRecognition);commandRecognition=null;pendingSuggestion=null;hideWakeOverlay();status("Listening cancelled");scheduleWake()});''',
        '''  wakeOverlayCancel.addEventListener("click",()=>{stopRecognition(commandRecognition);commandRecognition=null;pendingSuggestion=null;clearWakeFallbackCommandTimer();wakeFallbackMode="wake";wakeFallbackGeneration++;wakeFallbackChunks=[];hideWakeOverlay();status("Listening cancelled");scheduleWake()});''',
        "fallback cancellation",
    )
    frontend = replace_once(
        frontend,
        "Browser speech recognition may use the browser vendor's speech service.",
        "Browser speech recognition may use the browser vendor's speech service. If Chrome produces no transcript, local voice activity detection sends only a short detected utterance to ZBRANO transcription, with a 20-request hourly safety limit and no saved audio.",
        "fallback disclosure",
    )

    backend = backend.replace('version="0.12.97"', 'version="0.12.98"')
    backend = backend.replace('"version": "0.12.97"', '"version": "0.12.98"')
    frontend = frontend.replace("HUD 0.12.97", "HUD 0.12.98")

    for marker, location in [
        ('version="0.12.98"', backend),
        ('const WAKE_FALLBACK_LIMIT=20', frontend),
        ('function sampleWakeFallback()', frontend),
        ('async function transcribeWakeFallback(', frontend),
        ('startWakeFallback().catch(()=>{})', frontend),
        ('no saved audio', frontend),
        ('HUD 0.12.98', frontend),
    ]:
        require(location, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
