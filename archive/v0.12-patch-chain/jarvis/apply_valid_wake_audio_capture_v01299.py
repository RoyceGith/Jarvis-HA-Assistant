import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.99 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.99 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    frontend = replace_once(
        frontend,
        '''  function finishWakeFallbackUtterance(now){
    const started=wakeFallbackSpeechStart;const ended=wakeFallbackLastVoice;const mode=wakeFallbackMode;const generation=wakeFallbackGeneration;
    wakeFallbackSpeechStart=0;wakeFallbackLastVoice=0;wakeFallbackVoiceFrames=0;
    const selected=wakeFallbackChunks.filter(item=>item.time>=started-750);wakeFallbackChunks=[];
    if(ended-started<300||!selected.length)return;
    const blob=new Blob(selected.map(item=>item.data),{type:wakeFallbackRecorder?.mimeType||"audio/webm"});
    setTimeout(()=>{if(generation!==wakeFallbackGeneration)return;if(mode==="wake"&&wakeNativeMatchAt>=started)return;transcribeWakeFallback(blob,mode,generation)},400);
  }''',
        '''  function finishWakeFallbackUtterance(now){
    const started=wakeFallbackSpeechStart;const ended=wakeFallbackLastVoice;const mode=wakeFallbackMode;const generation=wakeFallbackGeneration;
    const recorder=wakeFallbackRecorder;const chunks=wakeFallbackChunks;wakeFallbackRecorder=null;wakeFallbackChunks=[];
    wakeFallbackSpeechStart=0;wakeFallbackLastVoice=0;wakeFallbackVoiceFrames=0;
    if(!recorder||recorder.state==="inactive")return;
    const validDuration=ended-started>=300;
    recorder.onstop=()=>{
      if(!validDuration||generation!==wakeFallbackGeneration||!chunks.length)return;
      const blob=new Blob(chunks,{type:recorder.mimeType||"audio/webm"});
      setTimeout(()=>{if(generation!==wakeFallbackGeneration)return;if(mode==="wake"&&wakeNativeMatchAt>=started)return;transcribeWakeFallback(blob,mode,generation)},400);
    };
    try{recorder.stop()}catch{}
  }''',
        "valid finalized utterance",
    )
    frontend = replace_once(
        frontend,
        '''  function sampleWakeFallback(){
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
  }''',
        '''  function sampleWakeFallback(){
    if(!wakeFallbackAnalyser)return;
    const samples=new Uint8Array(wakeFallbackAnalyser.fftSize);wakeFallbackAnalyser.getByteTimeDomainData(samples);
    let energy=0;for(const sample of samples){const value=(sample-128)/128;energy+=value*value}const rms=Math.sqrt(energy/samples.length);const now=performance.now();
    const threshold=Math.max(.018,wakeNoiseFloor*2.8);
    if(!wakeFallbackSpeechStart){
      wakeNoiseFloor=Math.min(.025,wakeNoiseFloor*.97+rms*.03);
      wakeFallbackVoiceFrames=rms>threshold?wakeFallbackVoiceFrames+1:0;
      if(wakeFallbackVoiceFrames>=2){
        try{
          const mimeType=recordingMimeType();const recorder=new MediaRecorder(wakeFallbackStream,mimeType?{mimeType}:undefined);const chunks=[];
          recorder.ondataavailable=event=>{if(event.data.size)chunks.push(event.data)};recorder.start(100);
          wakeFallbackRecorder=recorder;wakeFallbackChunks=chunks;wakeFallbackSpeechStart=now;wakeFallbackLastVoice=now;
        }catch(error){wakeFallbackVoiceFrames=0;status(`Reliable wake audio capture failed: ${error.message||error}`,"error")}
      }
      return;
    }
    if(rms>threshold)wakeFallbackLastVoice=now;
    if(now-wakeFallbackSpeechStart>=8000||now-wakeFallbackLastVoice>=900)finishWakeFallbackUtterance(now);
  }''',
        "per-utterance MediaRecorder",
    )
    frontend = replace_once(
        frontend,
        '''      const context=new AudioContextClass();await context.resume();const analyser=context.createAnalyser();analyser.fftSize=512;context.createMediaStreamSource(stream).connect(analyser);
      const mimeType=recordingMimeType();const recorder=new MediaRecorder(stream,mimeType?{mimeType}:undefined);
      wakeFallbackStream=stream;wakeFallbackContext=context;wakeFallbackAnalyser=analyser;wakeFallbackRecorder=recorder;wakeFallbackMode="wake";wakeFallbackChunks=[];
      recorder.ondataavailable=event=>{if(event.data.size)wakeFallbackChunks.push({data:event.data,time:performance.now()})};recorder.start(250);
      wakeFallbackTimer=setInterval(sampleWakeFallback,80);status(`Reliable wake listening active for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");''',
        '''      const context=new AudioContextClass();await context.resume();const analyser=context.createAnalyser();analyser.fftSize=512;context.createMediaStreamSource(stream).connect(analyser);
      wakeFallbackStream=stream;wakeFallbackContext=context;wakeFallbackAnalyser=analyser;wakeFallbackRecorder=null;wakeFallbackMode="wake";wakeFallbackChunks=[];
      wakeFallbackTimer=setInterval(sampleWakeFallback,80);status(`Reliable wake listening active for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");''',
        "idle analyzer without rolling container",
    )

    helper_marker = "AI-generated voice"
    helper_position = frontend.find(helper_marker)
    helper_start = frontend.rfind("<span", 0, helper_position)
    helper_end = frontend.find("</span>", helper_position)
    if helper_position < 0 or helper_start < 0 or helper_end < 0:
        raise RuntimeError("ZBRANO v0.12.99 could not locate the obsolete composer helper label")
    frontend = frontend[:helper_start] + frontend[helper_end + len("</span>"):]

    backend = backend.replace('version="0.12.98"', 'version="0.12.99"')
    backend = backend.replace('"version": "0.12.98"', '"version": "0.12.99"')
    frontend = frontend.replace("HUD 0.12.98", "HUD 0.12.99")

    for marker, location in [
        ('version="0.12.99"', backend),
        ('const chunks=[];', frontend),
        ('recorder.onstop=()=>{', frontend),
        ('new Blob(chunks,{type:recorder.mimeType', frontend),
        ('wakeFallbackRecorder=null;wakeFallbackMode="wake"', frontend),
        ('HUD 0.12.99', frontend),
    ]:
        require(location, marker, marker)
    if helper_marker in frontend:
        raise RuntimeError("ZBRANO v0.12.99 still contains the obsolete composer helper label")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
