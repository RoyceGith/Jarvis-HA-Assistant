import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.94 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.94 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        '''    "auto_speak": True,
    "response_length": "balanced",''',
        '''    "auto_speak": True,
    "proactive_voice_enabled": True,
    "voice_approval_enabled": True,
    "wake_word_enabled": False,
    "wake_phrase": "hey zbrano",
    "response_length": "balanced",''',
        "voice preference defaults",
    )
    backend = replace_once(
        backend,
        '''    auto_speak: bool = True
    response_length: str = Field(default="balanced", pattern="^(brief|balanced|detailed)$")''',
        '''    auto_speak: bool = True
    proactive_voice_enabled: bool = True
    voice_approval_enabled: bool = True
    wake_word_enabled: bool = False
    wake_phrase: str = Field(default="hey zbrano", min_length=2, max_length=40)
    response_length: str = Field(default="balanced", pattern="^(brief|balanced|detailed)$")''',
        "voice settings request fields",
    )
    backend = replace_once(
        backend,
        '''                "auto_speak": request.auto_speak,
                "response_length": request.response_length,''',
        '''                "auto_speak": request.auto_speak,
                "proactive_voice_enabled": request.proactive_voice_enabled,
                "voice_approval_enabled": request.voice_approval_enabled,
                "wake_word_enabled": request.wake_word_enabled,
                "wake_phrase": " ".join(request.wake_phrase.lower().split()),
                "response_length": request.response_length,''',
        "voice preference persistence",
    )

    frontend = replace_once(
        frontend,
        '''      <div class="settings-actions"><button id="test-voice" type="button">Test Voice</button><button id="reset-voice-settings" type="button">Reset Voice Defaults</button></div>''',
        '''      <div class="settings-actions"><button id="test-voice" type="button">Test Voice</button><button id="reset-voice-settings" type="button">Reset Voice Defaults</button></div>
      <div class="voice-handsfree-settings">
        <h3>PROACTIVE &amp; HANDS-FREE VOICE</h3>
        <label class="toggle-row"><input id="proactive-voice-enabled" type="checkbox" checked> Speak new autonomous suggestions on this open ZBRANO interface</label>
        <label class="toggle-row"><input id="voice-approval-enabled" type="checkbox" checked> Listen briefly for “approve” or “decline” after a spoken suggestion</label>
        <label class="toggle-row"><input id="wake-word-enabled" type="checkbox"> Enable browser wake phrase</label>
        <div class="setting-field"><label for="wake-phrase">Wake phrase</label><input id="wake-phrase" type="text" minlength="2" maxlength="40" value="hey zbrano" autocomplete="off"><small>Say the phrase followed by a command, or pause and speak after ZBRANO starts listening.</small></div>
        <p id="wake-word-status" class="muted">Wake listening is off. It works only while this page is open and microphone permission is granted.</p>
        <small>Voice approval is intended for a trusted room. Browser speech recognition may use the browser vendor's speech service. Screen approval and all existing automation authority limits remain available.</small>
      </div>''',
        "hands-free voice settings",
    )
    frontend = replace_once(
        frontend,
        '''    settingsAutoSpeak.checked = jarvisPreferences.auto_speak !== false;
    responseLength.value = jarvisPreferences.response_length || "balanced";''',
        '''    settingsAutoSpeak.checked = jarvisPreferences.auto_speak !== false;
    document.getElementById("proactive-voice-enabled").checked = jarvisPreferences.proactive_voice_enabled !== false;
    document.getElementById("voice-approval-enabled").checked = jarvisPreferences.voice_approval_enabled !== false;
    document.getElementById("wake-word-enabled").checked = jarvisPreferences.wake_word_enabled === true;
    document.getElementById("wake-phrase").value = jarvisPreferences.wake_phrase || "hey zbrano";
    window.dispatchEvent(new CustomEvent("zbrano-voice-preferences-loaded"));
    responseLength.value = jarvisPreferences.response_length || "balanced";''',
        "hands-free voice settings load",
    )
    frontend = replace_once(
        frontend,
        '''        auto_speak: settingsAutoSpeak.checked,
        response_length: responseLength.value,''',
        '''        auto_speak: settingsAutoSpeak.checked,
        proactive_voice_enabled: document.getElementById("proactive-voice-enabled").checked,
        voice_approval_enabled: document.getElementById("voice-approval-enabled").checked,
        wake_word_enabled: document.getElementById("wake-word-enabled").checked,
        wake_phrase: document.getElementById("wake-phrase").value.trim() || "hey zbrano",
        response_length: responseLength.value,''',
        "hands-free voice settings save",
    )

    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.94 could not locate stylesheet")
    styles = r'''
    /* v0.12.94 proactive voice and wake phrase. */
    .voice-handsfree-settings { margin-top:1rem; padding-top:.85rem; border-top:1px solid var(--line); display:grid; gap:.65rem; }
    .voice-handsfree-settings h3 { margin:0; font-size:.78rem; letter-spacing:.08em; }
    #wake-word-status[data-state="listening"] { color:var(--cyan); }
    #wake-word-status[data-state="error"] { color:var(--danger); }
'''
    frontend = frontend[:style_close] + styles + frontend[style_close:]

    body_close = frontend.rfind("</body>")
    if body_close < 0:
        raise RuntimeError("ZBRANO v0.12.94 could not locate body close")
    runtime = r'''
<script id="zbrano-v01294-proactive-voice">
(() => {
  const proactive=document.getElementById("proactive-voice-enabled");
  const voiceApproval=document.getElementById("voice-approval-enabled");
  const wakeEnabled=document.getElementById("wake-word-enabled");
  const wakePhrase=document.getElementById("wake-phrase");
  const wakeStatus=document.getElementById("wake-word-status");
  if(!proactive||!voiceApproval||!wakeEnabled||!wakePhrase||!wakeStatus)return;
  const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;
  const SEEN_KEY="zbrano_spoken_suggestions_v1";
  let seen=new Set();
  try{const stored=JSON.parse(localStorage.getItem(SEEN_KEY)||"[]");if(Array.isArray(stored))seen=new Set(stored.slice(-250))}catch{}
  let suggestionBaseline=false,pollActive=false,pendingSuggestion=null,wakeRecognition=null,commandRecognition=null,wakeRestart=null;

  function saveSeen(){localStorage.setItem(SEEN_KEY,JSON.stringify([...seen].slice(-250)))}
  function status(text,state=""){wakeStatus.textContent=text;wakeStatus.dataset.state=state}
  function clean(value){return String(value||"").toLowerCase().replace(/[^a-z0-9\u0370-\u03ff]+/g," ").trim()}
  function stopRecognition(instance){if(!instance)return;instance.onend=null;try{instance.abort()}catch{}}
  function stopWake(){if(wakeRestart)clearTimeout(wakeRestart);wakeRestart=null;stopRecognition(wakeRecognition);wakeRecognition=null}
  function recognitionLanguage(){const preferred=String(jarvisPreferences?.preferred_language||"").trim();return preferred&&preferred!=="auto"?preferred:document.documentElement.lang||navigator.language||"en-US"}
  function wakeCanRun(){return Boolean(wakeEnabled.checked&&Recognition&&!document.hidden&&!pendingSuggestion&&!activeAudio&&!speechQueueRunning&&!mediaRecorder&&!activeRequest)}

  function submitVoiceCommand(command){
    const value=String(command||"").trim();if(!value)return false;
    input.value=value;input.dispatchEvent(new Event("input",{bubbles:true}));form.requestSubmit();return true;
  }

  function startCommandWindow(){
    stopWake();stopRecognition(commandRecognition);
    if(!Recognition){status("Wake phrase is unavailable in this browser.","error");return}
    const recognition=new Recognition();commandRecognition=recognition;recognition.lang=recognitionLanguage();recognition.continuous=false;recognition.interimResults=false;
    let handled=false;const timer=setTimeout(()=>{try{recognition.stop()}catch{}},9000);
    recognition.onresult=event=>{const transcript=event.results?.[event.results.length-1]?.[0]?.transcript||"";handled=submitVoiceCommand(transcript);if(handled)status(`Heard: ${transcript}`)};
    recognition.onerror=event=>{if(event.error!=="aborted")status(`Voice command unavailable: ${event.error}`,"error")};
    recognition.onend=()=>{clearTimeout(timer);if(commandRecognition===recognition)commandRecognition=null;if(!handled&&wakeEnabled.checked)status(`Listening for “${wakePhrase.value.trim()||"hey zbrano"}”`,"listening");scheduleWake()};
    status("Wake phrase heard. Listening for your command…","listening");
    try{recognition.start()}catch(error){clearTimeout(timer);status(`Voice command unavailable: ${error.message||error}`,"error")}
  }

  function startWake(){
    if(!wakeCanRun())return;
    stopWake();const recognition=new Recognition();wakeRecognition=recognition;recognition.lang=recognitionLanguage();recognition.continuous=true;recognition.interimResults=false;
    recognition.onresult=event=>{
      const phrase=clean(wakePhrase.value||"hey zbrano");
      for(let index=event.resultIndex;index<event.results.length;index++){
        if(!event.results[index].isFinal)continue;
        const transcript=clean(event.results[index][0]?.transcript||"");const position=transcript.indexOf(phrase);
        if(position<0)continue;const command=transcript.slice(position+phrase.length).trim();stopWake();
        if(command)submitVoiceCommand(command);else startCommandWindow();break;
      }
    };
    recognition.onerror=event=>{if(event.error==="not-allowed"||event.error==="service-not-allowed"){wakeEnabled.checked=false;status("Microphone permission was denied. Enable it in the browser, then turn wake listening on again.","error")}else if(event.error!=="aborted")status(`Wake listening paused: ${event.error}`,"error")};
    recognition.onend=()=>{if(wakeRecognition===recognition)wakeRecognition=null;scheduleWake()};
    try{recognition.start();status(`Listening for “${wakePhrase.value.trim()||"hey zbrano"}”`,"listening")}catch(error){status(`Wake listening unavailable: ${error.message||error}`,"error")}
  }
  function scheduleWake(){if(wakeRestart)clearTimeout(wakeRestart);wakeRestart=setTimeout(()=>{wakeRestart=null;startWake()},1200)}

  async function decideSuggestion(suggestion,decision){
    const verb=decision==="approve"?"approve":"dismiss";
    try{
      const response=await fetch(`api/automations/suggestions/${encodeURIComponent(suggestion.id)}/${verb}`,{method:"POST"});
      const data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(data.detail||`HTTP ${response.status}`);
      await speakText(decision==="approve"?"Approved. I carried out the proposed action.":"Understood. I dismissed the suggestion.",true);
      window.zbranoAutomationWorkspace?.load?.().catch(()=>{});
    }catch(error){await speakText(`I could not ${verb} that suggestion. ${error.message||error}`,true)}
    finally{pendingSuggestion=null;scheduleWake()}
  }

  function listenForSuggestionDecision(suggestion){
    if(!voiceApproval.checked||!Recognition){pendingSuggestion=null;scheduleWake();return}
    stopWake();stopRecognition(commandRecognition);const recognition=new Recognition();commandRecognition=recognition;recognition.lang=recognitionLanguage();recognition.continuous=false;recognition.interimResults=false;
    let handled=false;const timer=setTimeout(()=>{try{recognition.stop()}catch{}},12000);
    recognition.onresult=event=>{
      const transcript=clean(event.results?.[event.results.length-1]?.[0]?.transcript||"");
      if(/\b(approve|approved|yes|okay|ok|do it|go ahead|proceed)\b/.test(transcript)){handled=true;stopRecognition(recognition);decideSuggestion(suggestion,"approve")}
      else if(/\b(no|decline|dismiss|cancel|not now)\b/.test(transcript)){handled=true;stopRecognition(recognition);decideSuggestion(suggestion,"dismiss")}
      else status(`I heard “${transcript||"nothing"}”. Use the on-screen Approve or Dismiss button.`);
    };
    recognition.onerror=event=>{if(event.error!=="aborted")status(`Voice approval unavailable: ${event.error}`,"error")};
    recognition.onend=()=>{clearTimeout(timer);if(commandRecognition===recognition)commandRecognition=null;if(!handled){pendingSuggestion=null;scheduleWake()}};
    status("Listening for approve or decline…","listening");try{recognition.start()}catch(error){pendingSuggestion=null;status(`Voice approval unavailable: ${error.message||error}`,"error");scheduleWake()}
  }

  async function announceSuggestion(item){
    if(!proactive.checked||document.hidden||isQuietHours())return;
    pendingSuggestion=item;stopWake();const prompt=[item.title,item.detail,"Say approve or decline."].filter(Boolean).join(". ");
    status("Speaking an autonomous suggestion…");await speakText(prompt,true);
    if(pendingSuggestion===item)listenForSuggestionDecision(item);
  }

  async function pollSuggestions(){
    if(pollActive||document.hidden)return;pollActive=true;
    try{
      const response=await fetch("api/automations",{cache:"no-store"});const data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(data.detail||`HTTP ${response.status}`);
      const actionable=(data.suggestions||[]).filter(item=>["pending","approval_required"].includes(item.status)&&item.id);
      if(!suggestionBaseline){actionable.forEach(item=>seen.add(item.id));saveSeen();suggestionBaseline=true;return}
      const fresh=actionable.filter(item=>!seen.has(item.id)).sort((a,b)=>Number(a.created_at||0)-Number(b.created_at||0));
      for(const item of fresh){seen.add(item.id)}saveSeen();if(fresh.length&&!pendingSuggestion)await announceSuggestion(fresh[0]);
    }catch{}finally{pollActive=false}
  }

  wakeEnabled.addEventListener("change",()=>{if(wakeEnabled.checked){if(!Recognition){wakeEnabled.checked=false;status("Wake phrase is not supported by this browser. Use current Chrome or Edge, or a Home Assistant voice satellite.","error")}else startWake()}else{stopWake();status("Wake listening is off. It works only while this page is open and microphone permission is granted.")}});
  wakePhrase.addEventListener("change",()=>{wakePhrase.value=clean(wakePhrase.value)||"hey zbrano";if(wakeEnabled.checked){stopWake();scheduleWake()}});
  document.addEventListener("visibilitychange",()=>{if(document.hidden)stopWake();else{pollSuggestions();scheduleWake()}});
  window.addEventListener("zbrano-voice-preferences-loaded",()=>{if(wakeEnabled.checked)startWake();else status("Wake listening is off. It works only while this page is open and microphone permission is granted.")});
  const voiceObserver=new MutationObserver(()=>{if(activeAudio||speechQueueRunning)stopWake();else if(!pendingSuggestion)scheduleWake()});voiceObserver.observe(document.getElementById("voice-state"),{childList:true,subtree:true});
  pollSuggestions();setInterval(pollSuggestions,5000);
  window.zbranoHandsFreeVoice={poll:pollSuggestions,startWake,stopWake};
})();
</script>
'''
    frontend = frontend[:body_close] + runtime + frontend[body_close:]

    backend = backend.replace('version="0.12.93"', 'version="0.12.94"')
    backend = backend.replace('"version": "0.12.93"', '"version": "0.12.94"')
    frontend = frontend.replace("HUD 0.12.93", "HUD 0.12.94")

    for marker, location in [
        ('version="0.12.94"', backend),
        ('"proactive_voice_enabled": True', backend),
        ('wake_phrase: str = Field(', backend),
        ('id="zbrano-v01294-proactive-voice"', frontend),
        ('Speak new autonomous suggestions', frontend),
        ('Listening for approve or decline', frontend),
        ('window.SpeechRecognition||window.webkitSpeechRecognition', frontend),
        ('HUD 0.12.94', frontend),
    ]:
        require(location, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
