import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.101 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.101 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    frontend = replace_once(
        frontend,
        '''  let wakeFallbackStream=null,wakeFallbackContext=null,wakeFallbackAnalyser=null,wakeFallbackRecorder=null,wakeFallbackTimer=null;''',
        '''  let wakeFallbackStream=null,wakeFallbackContext=null,wakeFallbackAnalyser=null,wakeFallbackRecorder=null,wakeFallbackTimer=null,wakeFallbackCaptureTimer=null,wakeFallbackCalibratingUntil=0,wakeFallbackPeak=0;''',
        "capture watchdog state",
    )
    frontend = replace_once(
        frontend,
        '''    if(wakeFallbackTimer)clearInterval(wakeFallbackTimer);wakeFallbackTimer=null;''',
        '''    if(wakeFallbackTimer)clearInterval(wakeFallbackTimer);wakeFallbackTimer=null;
    if(wakeFallbackCaptureTimer)clearTimeout(wakeFallbackCaptureTimer);wakeFallbackCaptureTimer=null;''',
        "capture watchdog cleanup",
    )
    frontend = replace_once(
        frontend,
        '''    let energy=0;for(const sample of samples){const value=(sample-128)/128;energy+=value*value}const rms=Math.sqrt(energy/samples.length);const now=performance.now();
    const threshold=Math.max(.03,wakeNoiseFloor*3.5);
    if(!wakeFallbackSpeechStart){
      wakeNoiseFloor=Math.min(.025,wakeNoiseFloor*.97+rms*.03);
      wakeFallbackVoiceFrames=rms>threshold?wakeFallbackVoiceFrames+1:0;''',
        '''    let energy=0,peak=0;for(const sample of samples){const value=(sample-128)/128;energy+=value*value;peak=Math.max(peak,Math.abs(value))}const rms=Math.sqrt(energy/samples.length);const now=performance.now();
    if(now<wakeFallbackCalibratingUntil){wakeNoiseFloor=Math.min(.08,wakeNoiseFloor*.9+rms*.1);wakeFallbackVoiceFrames=0;return}
    const threshold=Math.max(.032,wakeNoiseFloor*2.8);const strongVoice=rms>threshold&&peak>Math.max(.085,wakeNoiseFloor*4.2);
    if(!wakeFallbackSpeechStart){
      if(!strongVoice)wakeNoiseFloor=Math.min(.08,wakeNoiseFloor*.98+rms*.02);
      wakeFallbackVoiceFrames=strongVoice?wakeFallbackVoiceFrames+1:0;''',
        "calibrated RMS and peak voice gate",
    )
    frontend = replace_once(
        frontend,
        '''  function finishWakeFallbackUtterance(now){
    const started=wakeFallbackSpeechStart;const ended=wakeFallbackLastVoice;const mode=wakeFallbackMode;const generation=wakeFallbackGeneration;
    const recorder=wakeFallbackRecorder;const chunks=wakeFallbackChunks;wakeFallbackRecorder=null;wakeFallbackChunks=[];
    wakeFallbackSpeechStart=0;wakeFallbackLastVoice=0;wakeFallbackVoiceFrames=0;
    if(!recorder||recorder.state==="inactive")return;
    const validDuration=ended-started>=550;
    recorder.onstop=()=>{
      if(!validDuration||generation!==wakeFallbackGeneration||!chunks.length)return;
      const blob=new Blob(chunks,{type:recorder.mimeType||"audio/webm"});
      setTimeout(()=>{if(generation!==wakeFallbackGeneration)return;if(mode==="wake"&&wakeNativeMatchAt>=started)return;transcribeWakeFallback(blob,mode,generation)},400);
    };
    try{recorder.stop()}catch{}
  }''',
        '''  function finishWakeFallbackUtterance(now){
    const started=wakeFallbackSpeechStart;const ended=Math.max(wakeFallbackLastVoice,now);const mode=wakeFallbackMode;const generation=wakeFallbackGeneration;
    const recorder=wakeFallbackRecorder;const chunks=wakeFallbackChunks;wakeFallbackRecorder=null;wakeFallbackChunks=[];
    if(wakeFallbackCaptureTimer)clearTimeout(wakeFallbackCaptureTimer);wakeFallbackCaptureTimer=null;
    wakeFallbackSpeechStart=0;wakeFallbackLastVoice=0;wakeFallbackVoiceFrames=0;
    if(!recorder||recorder.state==="inactive"){status(`Reliable wake listening active for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");return}
    const validDuration=ended-started>=550;status("Finalizing wake audio...","listening");
    recorder.onstop=()=>{
      if(generation!==wakeFallbackGeneration)return;
      if(!validDuration||!chunks.length){status(`Reliable wake listening active for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");return}
      const blob=new Blob(chunks,{type:recorder.mimeType||"audio/webm"});
      setTimeout(()=>{if(generation!==wakeFallbackGeneration)return;if(mode==="wake"&&wakeNativeMatchAt>=started)return;transcribeWakeFallback(blob,mode,generation)},250);
    };
    recorder.onerror=event=>{if(generation===wakeFallbackGeneration)status(`Reliable wake audio failed: ${event.error?.message||"recorder error"}`,"error")};
    try{recorder.requestData();recorder.stop()}catch(error){status(`Reliable wake audio finalization failed: ${error.message||error}`,"error")}
  }''',
        "watchdog-backed finalization",
    )
    frontend = replace_once(
        frontend,
        '''          wakeFallbackRecorder=recorder;wakeFallbackChunks=chunks;wakeFallbackSpeechStart=now;wakeFallbackLastVoice=now;
          status("Speech detected - recording wake utterance...","listening");''',
        '''          wakeFallbackRecorder=recorder;wakeFallbackChunks=chunks;wakeFallbackSpeechStart=now;wakeFallbackLastVoice=now;
          if(wakeFallbackCaptureTimer)clearTimeout(wakeFallbackCaptureTimer);
          wakeFallbackCaptureTimer=setTimeout(()=>{if(wakeFallbackRecorder===recorder&&wakeFallbackSpeechStart)finishWakeFallbackUtterance(performance.now())},8500);
          status("Speech detected - recording wake utterance...","listening");''',
        "independent capture hard stop",
    )
    frontend = replace_once(
        frontend,
        '''      wakeFallbackStream=stream;wakeFallbackContext=context;wakeFallbackAnalyser=analyser;wakeFallbackRecorder=null;wakeFallbackMode="wake";wakeFallbackChunks=[];
      wakeFallbackTimer=setInterval(sampleWakeFallback,80);status(`Reliable wake listening active for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");''',
        '''      wakeFallbackStream=stream;wakeFallbackContext=context;wakeFallbackAnalyser=analyser;wakeFallbackRecorder=null;wakeFallbackMode="wake";wakeFallbackChunks=[];
      wakeNoiseFloor=.008;wakeFallbackCalibratingUntil=performance.now()+2500;wakeFallbackPeak=0;
      wakeFallbackTimer=setInterval(sampleWakeFallback,80);status("Calibrating reliable wake microphone...","listening");
      setTimeout(()=>{if(wakeFallbackStream&&wakeEnabled.checked)status(`Reliable wake listening active for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening")},2600);''',
        "microphone noise calibration",
    )

    backend = replace_once(
        backend,
        '''    normalized = " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())
    silence_hallucinations = {''',
        '''    normalized = " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())
    wake_characters = re.sub(r"[^a-z0-9\\u0370-\\u03ff]+", "", text.lower())
    silence_hallucinations = {''',
        "wake transcript character evidence",
    )
    backend = replace_once(
        backend,
        '''    if not text or (wake and normalized in silence_hallucinations):''',
        '''    if not text or (wake and (not wake_characters or normalized in silence_hallucinations)):''',
        "non-speech transcript rejection",
    )

    backend = backend.replace('version="0.12.100"', 'version="0.12.101"')
    backend = backend.replace('"version": "0.12.100"', '"version": "0.12.101"')
    frontend = frontend.replace("HUD 0.12.100", "HUD 0.12.101")

    for marker, location in [
        ('version="0.12.101"', backend),
        ('wakeFallbackCaptureTimer=setTimeout', frontend),
        ('Finalizing wake audio...', frontend),
        ('recorder.requestData();recorder.stop()', frontend),
        ('Reliable wake audio finalization failed', frontend),
        ('Calibrating reliable wake microphone', frontend),
        ('const strongVoice=rms>threshold&&peak>', frontend),
        ('HUD 0.12.101', frontend),
    ]:
        require(location, marker, marker)
    require(backend, 'wake_characters = re.sub(', "wake character evidence")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
