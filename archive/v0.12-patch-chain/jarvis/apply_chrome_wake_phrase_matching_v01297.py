import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.97 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.97 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    frontend = replace_once(
        frontend,
        '''  function clean(value){return String(value||"").toLowerCase().replace(/[^a-z0-9\\u0370-\\u03ff]+/g," ").trim()}
  function stopRecognition(instance){''',
        '''  function clean(value){return String(value||"").toLowerCase().replace(/[^a-z0-9\\u0370-\\u03ff]+/g," ").trim()}
  function wakeCandidates(){
    const configured=clean(wakePhrase.value||"hey zbrano");const candidates=[configured];
    if(configured==="hey zbrano"||configured==="zbrano")candidates.push("hey zbrano","zbrano","hey z brano","z brano","hey zebrano","zebrano","hey zabrano","zabrano");
    return [...new Set(candidates.filter(Boolean))].sort((left,right)=>right.length-left.length);
  }
  function matchWakePhrase(value){
    const transcript=clean(value);if(!transcript)return null;const padded=` ${transcript} `;
    for(const phrase of wakeCandidates()){
      const needle=` ${phrase} `;const position=padded.indexOf(needle);
      if(position>=0)return {transcript,phrase,command:padded.slice(position+needle.length).trim()};
    }
    return null;
  }
  function stopRecognition(instance){''',
        "wake phrase aliases",
    )

    wake_start = frontend.find("  function startWake(){")
    result_start = frontend.find("    recognition.onresult=event=>{", wake_start)
    result_end = frontend.find("\n    recognition.onerror=", result_start)
    if wake_start < 0 or result_start < 0 or result_end < 0:
        raise RuntimeError("ZBRANO v0.12.97 could not locate the wake recognition handler")
    prefix = frontend[wake_start:result_start]
    old_mode = "recognition.continuous=true;recognition.interimResults=false;"
    if prefix.count(old_mode) != 1:
        raise RuntimeError("ZBRANO v0.12.97 could not locate the wake recognition mode")
    prefix = prefix.replace(
        old_mode,
        "recognition.continuous=true;recognition.interimResults=true;",
        1,
    )
    handler = '''    recognition.onstart=()=>status(`Microphone active - listening for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");
    recognition.onresult=event=>{
      for(let index=event.resultIndex;index<event.results.length;index++){
        const rawTranscript=event.results[index][0]?.transcript||"";const match=matchWakePhrase(rawTranscript);
        if(!match){if(event.results[index].isFinal&&clean(rawTranscript))status(`Heard "${rawTranscript.trim()}" - waiting for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");continue}
        stopWake();showWakeOverlay("WAKE PHRASE HEARD",match.command||"Speak your command...");
        if(match.command)submitVoiceCommand(match.command);else setTimeout(startCommandWindow,180);break;
      }
    };'''
    frontend = frontend[:wake_start] + prefix + handler + frontend[result_end:]

    frontend = replace_once(
        frontend,
        '''  function scheduleWake(){if(wakeRestart)clearTimeout(wakeRestart);wakeRestart=setTimeout(()=>{wakeRestart=null;startWake()},1200)}''',
        '''  function scheduleWake(delay=1200){if(wakeRestart)clearTimeout(wakeRestart);wakeRestart=setTimeout(()=>{wakeRestart=null;startWake()},Math.max(250,delay))}''',
        "wake restart delay",
    )

    backend = backend.replace('version="0.12.96"', 'version="0.12.97"')
    backend = backend.replace('"version": "0.12.96"', '"version": "0.12.97"')
    frontend = frontend.replace("HUD 0.12.96", "HUD 0.12.97")

    for marker, location in [
        ('version="0.12.97"', backend),
        ('function wakeCandidates()', frontend),
        ('function matchWakePhrase(value)', frontend),
        ('recognition.interimResults=true', frontend),
        ('Microphone active - listening for', frontend),
        ('setTimeout(startCommandWindow,180)', frontend),
        ('HUD 0.12.97', frontend),
    ]:
        require(location, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
