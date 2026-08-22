import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.96 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.96 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    overlay = r'''
<div id="wake-listening-overlay" class="wake-listening-overlay" hidden role="dialog" aria-modal="true" aria-labelledby="wake-listening-title">
  <div class="wake-listening-card">
    <div class="wake-listening-visual" aria-hidden="true">
      <span class="wake-ring wake-ring-one"></span><span class="wake-ring wake-ring-two"></span><span class="wake-ring wake-ring-three"></span>
      <span class="wake-microphone"><svg viewBox="0 0 24 24" focusable="false"><path d="M12 15a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3Zm-6-3a1 1 0 0 1 2 0 4 4 0 0 0 8 0 1 1 0 1 1 2 0 6 6 0 0 1-5 5.91V20h2a1 1 0 1 1 0 2H9a1 1 0 1 1 0-2h2v-2.09A6 6 0 0 1 6 12Z"/></svg></span>
      <span class="wake-levels"><i></i><i></i><i></i><i></i><i></i></span>
    </div>
    <div id="wake-listening-title" class="wake-listening-title">ZBRANO IS LISTENING</div>
    <div id="wake-listening-transcript" class="wake-listening-transcript">Speak your command…</div>
    <div class="wake-listening-time"><span id="wake-listening-progress"></span></div>
    <button id="wake-listening-cancel" type="button">Cancel</button>
  </div>
</div>
'''
    script_marker = '<script id="zbrano-v01294-proactive-voice">'
    frontend = replace_once(frontend, script_marker, overlay + script_marker, "wake overlay markup")

    frontend = replace_once(
        frontend,
        '''  const wakeStatus=document.getElementById("wake-word-status");
  if(!proactive||!voiceApproval||!wakeEnabled||!wakePhrase||!wakeStatus)return;''',
        '''  const wakeStatus=document.getElementById("wake-word-status");
  const wakeOverlay=document.getElementById("wake-listening-overlay");
  const wakeOverlayTitle=document.getElementById("wake-listening-title");
  const wakeOverlayTranscript=document.getElementById("wake-listening-transcript");
  const wakeOverlayCancel=document.getElementById("wake-listening-cancel");
  if(!proactive||!voiceApproval||!wakeEnabled||!wakePhrase||!wakeStatus||!wakeOverlay)return;''',
        "wake overlay bindings",
    )
    frontend = replace_once(
        frontend,
        '''  function submitVoiceCommand(command){
    const value=String(command||"").trim();if(!value)return false;
    input.value=value;input.dispatchEvent(new Event("input",{bubbles:true}));form.requestSubmit();return true;
  }

  function startCommandWindow(){''',
        '''  let wakeOverlayTimer=null;
  function showWakeOverlay(title="ZBRANO IS LISTENING",transcript="Speak your command…"){
    if(wakeOverlayTimer)clearTimeout(wakeOverlayTimer);wakeOverlayTimer=null;
    wakeOverlayTitle.textContent=title;wakeOverlayTranscript.textContent=transcript;
    wakeOverlay.hidden=false;requestAnimationFrame(()=>wakeOverlay.classList.add("active"));
  }
  function updateWakeOverlay(transcript){wakeOverlayTranscript.textContent=String(transcript||"Speak your command…")}
  function hideWakeOverlay(delay=0){
    if(wakeOverlayTimer)clearTimeout(wakeOverlayTimer);
    wakeOverlayTimer=setTimeout(()=>{wakeOverlay.classList.remove("active");setTimeout(()=>{wakeOverlay.hidden=true},180)},Math.max(0,delay));
  }
  function submitVoiceCommand(command){
    const value=String(command||"").trim();if(!value)return false;
    updateWakeOverlay(value);input.value=value;input.dispatchEvent(new Event("input",{bubbles:true}));form.requestSubmit();hideWakeOverlay(420);return true;
  }

  function startCommandWindow(){''',
        "wake overlay controller",
    )
    frontend = replace_once(
        frontend,
        '''    stopWake();stopRecognition(commandRecognition);
    if(!Recognition){status("Wake phrase is unavailable in this browser.","error");return}
    const recognition=new Recognition();''',
        '''    stopWake();stopRecognition(commandRecognition);showWakeOverlay();
    if(!Recognition){status("Wake phrase is unavailable in this browser.","error");hideWakeOverlay();return}
    const recognition=new Recognition();''',
        "command overlay start",
    )
    frontend = replace_once(
        frontend,
        '''    recognition.onresult=event=>{const transcript=event.results?.[event.results.length-1]?.[0]?.transcript||"";handled=submitVoiceCommand(transcript);if(handled)status(`Heard: ${transcript}`)};
    recognition.onerror=event=>{if(event.error!=="aborted")status(`Voice command unavailable: ${event.error}`,"error")};
    recognition.onend=()=>{clearTimeout(timer);if(commandRecognition===recognition)commandRecognition=null;if(!handled&&wakeEnabled.checked)status(`Listening for “${wakePhrase.value.trim()||"hey zbrano"}”`,"listening");scheduleWake()};''',
        '''    recognition.onresult=event=>{const transcript=event.results?.[event.results.length-1]?.[0]?.transcript||"";updateWakeOverlay(transcript||"Listening…");handled=submitVoiceCommand(transcript);if(handled)status(`Heard: ${transcript}`)};
    recognition.onerror=event=>{if(event.error!=="aborted")status(`Voice command unavailable: ${event.error}`,"error");updateWakeOverlay(event.error==="no-speech"?"No command heard":`Microphone error: ${event.error}`);hideWakeOverlay(650)};
    recognition.onend=()=>{clearTimeout(timer);if(commandRecognition===recognition)commandRecognition=null;if(!handled){updateWakeOverlay("No command heard");hideWakeOverlay(650)}if(!handled&&wakeEnabled.checked)status(`Listening for “${wakePhrase.value.trim()||"hey zbrano"}”`,"listening");scheduleWake()};''',
        "command overlay result lifecycle",
    )
    frontend = replace_once(
        frontend,
        '''        if(position<0)continue;const command=transcript.slice(position+phrase.length).trim();stopWake();
        if(command)submitVoiceCommand(command);else startCommandWindow();break;''',
        '''        if(position<0)continue;const command=transcript.slice(position+phrase.length).trim();stopWake();showWakeOverlay("WAKE PHRASE HEARD",command||"Speak your command…");
        if(command)submitVoiceCommand(command);else startCommandWindow();break;''',
        "wake phrase overlay trigger",
    )
    frontend = replace_once(
        frontend,
        '''  wakeEnabled.addEventListener("change",()=>{if(wakeEnabled.checked){if(showWakeCompatibility())startWake()}else{stopWake();status(braveBrowser?"Browser wake phrase is unavailable in Brave. Use Chrome or Edge, or connect a local Home Assistant voice satellite. Push-to-talk still works.":"Wake listening is off. It works only while this page is open and microphone permission is granted.",braveBrowser?"error":"")}});''',
        '''  wakeOverlayCancel.addEventListener("click",()=>{stopRecognition(commandRecognition);commandRecognition=null;pendingSuggestion=null;hideWakeOverlay();status("Listening cancelled");scheduleWake()});
  wakeEnabled.addEventListener("change",()=>{if(wakeEnabled.checked){if(showWakeCompatibility())startWake()}else{stopWake();hideWakeOverlay();status(braveBrowser?"Browser wake phrase is unavailable in Brave. Use Chrome or Edge, or connect a local Home Assistant voice satellite. Push-to-talk still works.":"Wake listening is off. It works only while this page is open and microphone permission is granted.",braveBrowser?"error":"")}});''',
        "wake overlay cancel",
    )

    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.96 could not locate stylesheet")
    styles = r'''
    /* v0.12.96 wake listening overlay. */
    .wake-listening-overlay { position:fixed; inset:0; z-index:10000; display:grid; place-items:center; padding:1.25rem; background:rgba(2,8,10,.62); opacity:0; backdrop-filter:blur(10px); transition:opacity .18s ease; }
    .wake-listening-overlay[hidden] { display:none; }
    .wake-listening-overlay.active { opacity:1; }
    .wake-listening-card { width:min(420px,92vw); display:grid; justify-items:center; gap:.85rem; padding:2rem 1.5rem 1.35rem; border:1px solid color-mix(in srgb,var(--cyan) 58%,transparent); border-radius:22px; background:color-mix(in srgb,var(--surface-strong) 88%,transparent); box-shadow:0 24px 90px rgba(0,0,0,.48),inset 0 1px rgba(255,255,255,.08); text-align:center; }
    .wake-listening-visual { position:relative; width:154px; height:154px; display:grid; place-items:center; }
    .wake-ring { position:absolute; inset:28px; border:1px solid color-mix(in srgb,var(--cyan) 64%,transparent); border-radius:50%; animation:wake-ring-pulse 1.8s ease-out infinite; }
    .wake-ring-two { animation-delay:.55s; }.wake-ring-three { animation-delay:1.1s; }
    .wake-microphone { position:relative; z-index:2; width:72px; height:72px; display:grid; place-items:center; border-radius:50%; background:linear-gradient(145deg,color-mix(in srgb,var(--cyan) 25%,var(--surface-strong)),color-mix(in srgb,var(--phosphor) 14%,var(--surface-strong))); border:1px solid var(--cyan); box-shadow:0 0 30px color-mix(in srgb,var(--cyan) 30%,transparent); animation:wake-core-breathe 1.25s ease-in-out infinite; }
    .wake-microphone svg { width:33px; height:33px; fill:var(--cyan); }
    .wake-levels { position:absolute; bottom:3px; height:24px; display:flex; align-items:center; gap:4px; }
    .wake-levels i { display:block; width:3px; height:7px; border-radius:4px; background:var(--cyan); animation:wake-level .75s ease-in-out infinite alternate; }.wake-levels i:nth-child(2),.wake-levels i:nth-child(4){animation-delay:.2s}.wake-levels i:nth-child(3){animation-delay:.38s}
    .wake-listening-title { color:var(--cyan); font-size:.76rem; letter-spacing:.16em; }
    .wake-listening-transcript { min-height:2.8em; max-width:34ch; color:var(--text); font-size:1.08rem; line-height:1.4; overflow-wrap:anywhere; }
    .wake-listening-time { width:min(250px,70vw); height:3px; overflow:hidden; border-radius:99px; background:color-mix(in srgb,var(--line) 75%,transparent); }
    .wake-listening-time span { display:block; width:100%; height:100%; background:var(--cyan); transform-origin:left; animation:wake-listening-timeout 9s linear forwards; }
    #wake-listening-cancel { min-width:110px; padding:.48rem .8rem; }
    @keyframes wake-ring-pulse { 0%{transform:scale(.58);opacity:.8}100%{transform:scale(1.9);opacity:0} }
    @keyframes wake-core-breathe { 50%{transform:scale(1.06);box-shadow:0 0 44px color-mix(in srgb,var(--cyan) 42%,transparent)} }
    @keyframes wake-level { from{height:6px;opacity:.48}to{height:23px;opacity:1} }
    @keyframes wake-listening-timeout { to{transform:scaleX(0)} }
    :root[data-theme="light"] .wake-listening-overlay { background:rgba(225,232,225,.68); }
    :root[data-theme="light"] .wake-listening-card { background:rgba(250,252,248,.96); }
    :root[data-reduced-motion="true"] .wake-ring,:root[data-reduced-motion="true"] .wake-microphone,:root[data-reduced-motion="true"] .wake-levels i { animation:none !important; }
'''
    frontend = frontend[:style_close] + styles + frontend[style_close:]

    backend = backend.replace('version="0.12.95"', 'version="0.12.96"')
    backend = backend.replace('"version": "0.12.95"', '"version": "0.12.96"')
    frontend = frontend.replace("HUD 0.12.95", "HUD 0.12.96")

    for marker, location in [
        ('version="0.12.96"', backend),
        ('id="wake-listening-overlay"', frontend),
        ('function showWakeOverlay(', frontend),
        ('WAKE PHRASE HEARD', frontend),
        ('wakeOverlayCancel.addEventListener', frontend),
        ('@keyframes wake-ring-pulse', frontend),
        ('HUD 0.12.96', frontend),
    ]:
        require(location, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
