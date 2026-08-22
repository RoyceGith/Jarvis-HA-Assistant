import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.111 patch expected one {label}; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.111 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    require(backend, 'version="0.12.110"', "backend version")
    require(frontend, "HUD 0.12.110", "frontend version")

    frontend = replace_once(
        frontend,
        '''        <label class="toggle-row"><input id="wake-word-enabled" type="checkbox"> Enable browser wake phrase</label>
        <div class="setting-field"><label for="wake-phrase">Wake phrase</label>''',
        '''        <label class="toggle-row"><input id="wake-word-enabled" type="checkbox"> Enable browser wake phrase</label>
        <label class="toggle-row"><input id="wake-conversation-enabled" type="checkbox"> Keep listening for follow-up conversation after voice replies</label>
        <div class="setting-field"><label for="wake-conversation-stop">Stop conversation phrase</label><input id="wake-conversation-stop" type="text" minlength="2" maxlength="60" value="ok thank you" autocomplete="off"><small>Say this during a follow-up window to end conversation mode without sending another prompt.</small></div>
        <div class="setting-field"><label for="wake-phrase">Wake phrase</label>''',
        "conversation setting",
    )
    frontend = replace_once(
        frontend,
        '''          <label class="toggle-row"><input id="wake-shadow-enabled" type="checkbox"> Evaluate “Hey ZBRANO” silently while wake listening is enabled</label>''',
        '''          <label class="toggle-row"><input id="wake-shadow-enabled" type="checkbox"> Evaluate “Hey ZBRANO” locally while wake listening is enabled</label>
          <label class="toggle-row"><input id="wake-local-activate" type="checkbox"> Use the local wake model to activate ZBRANO</label>''',
        "local activation setting",
    )

    frontend = replace_once(
        frontend,
        '''  const wakeShadowEnabled=document.getElementById("wake-shadow-enabled"),wakeShadowThreshold=document.getElementById("wake-shadow-threshold");''',
        '''  const wakeShadowEnabled=document.getElementById("wake-shadow-enabled"),wakeShadowThreshold=document.getElementById("wake-shadow-threshold");
  const wakeLocalActivate=document.getElementById("wake-local-activate"),wakeConversationEnabled=document.getElementById("wake-conversation-enabled"),wakeConversationStop=document.getElementById("wake-conversation-stop");''',
        "local activation controls",
    )
    frontend = replace_once(
        frontend,
        '''  const WAKE_SHADOW_KEY="zbrano_wake_shadow_v1";''',
        '''  const WAKE_SHADOW_KEY="zbrano_wake_shadow_v1";
  let wakeLocalActivationAt=0,wakeConversationArmed=false,wakeConversationListening=false,wakeConversationWaitTimer=null;''',
        "local activation state",
    )

    frontend = replace_once(
        frontend,
        '''  function submitVoiceCommand(command){
    const value=String(command||"").trim();if(!value)return false;
    updateWakeOverlay(value);input.value=value;input.dispatchEvent(new Event("input",{bubbles:true}));form.requestSubmit();hideWakeOverlay(420);return true;
  }''',
        '''  function submitVoiceCommand(command){
    const value=String(command||"").trim();if(!value)return false;
    const normalized=clean(value),preferredStop=clean(wakeConversationStop.value||"ok thank you");
    if(wakeConversationListening&&(normalized===preferredStop||/^(stop|end|exit|cancel)( the)? conversation$/i.test(normalized))){
      wakeConversationListening=false;wakeConversationArmed=false;clearWakeFallbackCommandTimer();wakeFallbackMode="wake";hideWakeOverlay(250);status("Conversation mode ended");scheduleWake();return true;
    }
    wakeConversationListening=false;wakeConversationArmed=true;updateWakeOverlay(value);input.value=value;input.dispatchEvent(new Event("input",{bubbles:true}));form.requestSubmit();hideWakeOverlay(420);return true;
  }''',
        "voice conversation command tracking",
    )
    frontend = replace_once(
        frontend,
        '''    wakeFallbackCommandTimer=setTimeout(()=>{wakeFallbackMode="wake";hideWakeOverlay(250);status(`No command heard - listening for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");scheduleWake()},9000);''',
        '''    wakeFallbackCommandTimer=setTimeout(()=>{wakeConversationListening=false;wakeFallbackMode="wake";hideWakeOverlay(250);status(`No command heard - listening for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");scheduleWake()},wakeConversationListening?15000:9000);''',
        "conversation command timeout",
    )

    detection = '''if(wakeShadowAbove>=2&&!wakeShadowLatched){wakeShadowLatched=true;wakeShadowStats.detections++;wakeShadowLastCandidate=new Int16Array(wakeShadowHistory.slice(-64000));wakeShadowMessage.textContent=`Silent detection ${wakeShadowStats.detections} at ${score.toFixed(3)}. Chat was not activated.`}'''
    activation = '''if(wakeShadowAbove>=2&&!wakeShadowLatched){
      wakeShadowLatched=true;wakeShadowStats.detections++;wakeShadowLastCandidate=new Int16Array(wakeShadowHistory.slice(-64000));
      const canActivate=wakeLocalActivate.checked&&wakeFallbackMode==="wake"&&!wakeShadowAttempt&&!wakeCalibrationCapture&&!activeRequest&&!pendingSuggestion&&Date.now()-wakeLocalActivationAt>=8000;
      if(canActivate){wakeLocalActivationAt=Date.now();wakeShadowMessage.textContent=`Local wake activation ${wakeShadowStats.detections} at ${score.toFixed(3)}.`;stopRecognition(wakeRecognition);wakeRecognition=null;showWakeOverlay("LOCAL WAKE PHRASE HEARD","Speak your command...");if(wakeFallbackStream)startFallbackCommandWindow();else{stopWake();setTimeout(startCommandWindow,180)}}
      else wakeShadowMessage.textContent=`Silent detection ${wakeShadowStats.detections} at ${score.toFixed(3)}.${wakeLocalActivate.checked?" Activation was busy or cooling down.":" Chat was not activated."}`;
    }'''
    frontend = replace_once(frontend, detection, activation, "local wake detection action")

    frontend = replace_once(
        frontend,
        '''  wakeShadowEnabled.checked=localStorage.getItem("zbrano_wake_shadow_enabled")==="true";wakeShadowThreshold.value=localStorage.getItem("zbrano_wake_shadow_threshold")||"0.50";wakeShadowThresholdValue.textContent=Number(wakeShadowThreshold.value).toFixed(2);renderWakeShadow();''',
        '''  wakeShadowEnabled.checked=localStorage.getItem("zbrano_wake_shadow_enabled")==="true";wakeShadowThreshold.value=localStorage.getItem("zbrano_wake_shadow_threshold")||"0.50";wakeShadowThresholdValue.textContent=Number(wakeShadowThreshold.value).toFixed(2);wakeLocalActivate.checked=localStorage.getItem("zbrano_wake_local_activate")==="true";wakeConversationEnabled.checked=localStorage.getItem("zbrano_wake_conversation")==="true";wakeConversationStop.value=localStorage.getItem("zbrano_wake_conversation_stop")||"ok thank you";renderWakeShadow();''',
        "browser-local voice settings load",
    )

    frontend = replace_once(
        frontend,
        '''  wakeShadowEnabled.addEventListener("change",()=>{localStorage.setItem("zbrano_wake_shadow_enabled",String(wakeShadowEnabled.checked));stopWake();if(wakeEnabled.checked)scheduleWake();else renderWakeShadow()});''',
        '''  wakeLocalActivate.addEventListener("change",()=>{if(wakeLocalActivate.checked&&!wakeShadowEnabled.checked){wakeShadowEnabled.checked=true;localStorage.setItem("zbrano_wake_shadow_enabled","true")}localStorage.setItem("zbrano_wake_local_activate",String(wakeLocalActivate.checked));stopWake();if(wakeEnabled.checked)scheduleWake();else renderWakeShadow()});
  wakeConversationEnabled.addEventListener("change",()=>{localStorage.setItem("zbrano_wake_conversation",String(wakeConversationEnabled.checked));if(!wakeConversationEnabled.checked){wakeConversationArmed=false;wakeConversationListening=false;if(wakeConversationWaitTimer)clearTimeout(wakeConversationWaitTimer)}});
  wakeConversationStop.addEventListener("change",()=>{wakeConversationStop.value=clean(wakeConversationStop.value)||"ok thank you";localStorage.setItem("zbrano_wake_conversation_stop",wakeConversationStop.value)});
  wakeShadowEnabled.addEventListener("change",()=>{if(!wakeShadowEnabled.checked){wakeLocalActivate.checked=false;localStorage.setItem("zbrano_wake_local_activate","false")}localStorage.setItem("zbrano_wake_shadow_enabled",String(wakeShadowEnabled.checked));stopWake();if(wakeEnabled.checked)scheduleWake();else renderWakeShadow()});''',
        "local wake setting listeners",
    )

    conversation_runtime = '''
  function startConversationFollowup(){
    if(wakeConversationWaitTimer)clearTimeout(wakeConversationWaitTimer);const expires=Date.now()+45000;
    const attempt=async()=>{
      if(!wakeConversationEnabled.checked||!wakeEnabled.checked||document.hidden)return;
      if(Date.now()>=expires){status("Conversation follow-up expired");scheduleWake();return}
      if(activeRequest||activeAudio||speechQueueRunning||mediaRecorder||pendingSuggestion){wakeConversationWaitTimer=setTimeout(attempt,300);return}
      await startWakeFallback();if(!wakeFallbackStream){status("Conversation microphone unavailable","error");scheduleWake();return}
      stopRecognition(wakeRecognition);wakeRecognition=null;wakeConversationListening=true;showWakeOverlay("CONVERSATION MODE","Listening for your follow-up...");startFallbackCommandWindow();status("Conversation mode - listening for a follow-up","listening");
    };
    attempt();
  }
  window.addEventListener("zbrano-response-finished",()=>{if(!wakeConversationArmed)return;wakeConversationArmed=false;if(wakeConversationEnabled.checked)startConversationFollowup()});
'''
    frontend = replace_once(
        frontend,
        '''  pollSuggestions();setInterval(pollSuggestions,5000);''',
        conversation_runtime + '''  pollSuggestions();setInterval(pollSuggestions,5000);''',
        "conversation follow-up runtime",
    )
    frontend = replace_once(
        frontend,
        '''function finishResponseActivity(label = "Completed") {
  if (responseTimerId) window.clearInterval(responseTimerId);
  responseTimerId = null;
  updateResponseTimer();
  setResponseActivity(label);
}''',
        '''function finishResponseActivity(label = "Completed") {
  if (responseTimerId) window.clearInterval(responseTimerId);
  responseTimerId = null;
  updateResponseTimer();
  setResponseActivity(label);
  if (label === "Completed") window.dispatchEvent(new CustomEvent("zbrano-response-finished"));
}''',
        "completed response signal",
    )
    frontend = replace_once(
        frontend,
        '''wakeOverlayCancel.addEventListener("click",()=>{stopRecognition(commandRecognition);commandRecognition=null;pendingSuggestion=null;clearWakeFallbackCommandTimer();wakeFallbackMode="wake";wakeFallbackGeneration++;wakeFallbackChunks=[];hideWakeOverlay();status("Listening cancelled");scheduleWake()});''',
        '''wakeOverlayCancel.addEventListener("click",()=>{stopRecognition(commandRecognition);commandRecognition=null;pendingSuggestion=null;wakeConversationArmed=false;wakeConversationListening=false;if(wakeConversationWaitTimer)clearTimeout(wakeConversationWaitTimer);clearWakeFallbackCommandTimer();wakeFallbackMode="wake";wakeFallbackGeneration++;wakeFallbackChunks=[];hideWakeOverlay();status("Listening cancelled");scheduleWake()});''',
        "conversation cancellation",
    )

    backend = backend.replace(
        '"""Score transient 16 kHz PCM frames locally; never retain audio or activate chat."""',
        '"""Score transient 16 kHz PCM frames locally; never retain audio; browser activation is explicitly optional."""',
        1,
    )
    backend = backend.replace('version="0.12.110"', 'version="0.12.111"')
    backend = backend.replace('"version": "0.12.110"', '"version": "0.12.111"')
    frontend = frontend.replace("HUD 0.12.110", "HUD 0.12.111")

    for marker, location in [
        ('version="0.12.111"', backend),
        ('browser activation is explicitly optional', backend),
        ('id="wake-local-activate"', frontend),
        ('id="wake-conversation-enabled"', frontend),
        ('id="wake-conversation-stop"', frontend),
        ('preferredStop=clean(', frontend),
        ('LOCAL WAKE PHRASE HEARD', frontend),
        ('CONVERSATION MODE', frontend),
        ('zbrano-response-finished', frontend),
        ('wakeConversationListening?15000:9000', frontend),
        ('HUD 0.12.111', frontend),
    ]:
        require(location, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
