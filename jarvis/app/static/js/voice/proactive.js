(() => {
  const proactive=document.getElementById("proactive-voice-enabled");
  const voiceApproval=document.getElementById("voice-approval-enabled");
  const wakeEnabled=document.getElementById("wake-word-enabled");
  const wakePhrase=document.getElementById("wake-phrase");
  const wakeStatus=document.getElementById("wake-word-status");
  const wakeOverlay=document.getElementById("wake-listening-overlay");
  const wakeOverlayTitle=document.getElementById("wake-listening-title");
  const wakeOverlayTranscript=document.getElementById("wake-listening-transcript");
  const wakeOverlayCancel=document.getElementById("wake-listening-cancel");
  if(!proactive||!voiceApproval||!wakeEnabled||!wakePhrase||!wakeStatus||!wakeOverlay)return;
  const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;
  const braveBrowser=Boolean(navigator.brave)||Boolean(navigator.userAgentData?.brands?.some(item=>String(item.brand||"").toLowerCase().includes("brave")));
  const SEEN_KEY="zbrano_spoken_suggestions_v1";
  let seen=new Set();
  try{const stored=JSON.parse(localStorage.getItem(SEEN_KEY)||"[]");if(Array.isArray(stored))seen=new Set(stored.slice(-250))}catch{}
  let suggestionBaseline=false,pollActive=false,pendingSuggestion=null,wakeRecognition=null,commandRecognition=null,wakeRestart=null;

  function saveSeen(){localStorage.setItem(SEEN_KEY,JSON.stringify([...seen].slice(-250)))}
  function status(text,state=""){wakeStatus.textContent=text;wakeStatus.dataset.state=state}
  function clean(value){return String(value||"").toLowerCase().replace(/[^a-z0-9\u0370-\u03ff]+/g," ").trim()}
  function conversationPhrase(value){return clean(value).replace(/\bokay\b/g,"ok").replace(/\bthanks\b/g,"thank you").replace(/\bthankyou\b/g,"thank you").replace(/\s+/g," ").trim()}
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
  let wakeFallbackStream=null,wakeFallbackContext=null,wakeFallbackAnalyser=null,wakeFallbackRecorder=null,wakeFallbackTimer=null,wakeFallbackCaptureTimer=null,wakeFallbackCalibratingUntil=0,wakeFallbackPeak=0;
  let wakeFallbackChunks=[],wakeFallbackSpeechStart=0,wakeFallbackLastVoice=0,wakeFallbackVoiceFrames=0,wakeFallbackBusy=false,wakeFallbackFinalizing=false,wakeFallbackLastSampleAt=0;
  let wakeShadowSocket=null,wakeShadowProcessor=null,wakeShadowMute=null,wakeShadowPcm=[],wakeShadowAbove=0,wakeShadowLatched=false,wakeShadowSaveTimer=null;
  let wakeShadowHistory=[],wakeShadowLastCandidate=null,wakeCalibrationCapture=null,wakeCalibrationBusy=false,wakeShadowInputRms=0,wakeShadowInputPeak=0,wakeShadowAttempt=null,wakeShadowAttemptTimer=null,wakeShadowAttemptNumber=0;
  let wakeFallbackMode="wake",wakeFallbackGeneration=0,wakeFallbackCommandTimer=null,wakeNativeMatchAt=0,wakeFallbackStarting=false,wakeFallbackStartToken=0,wakeNoiseFloor=.008;
  const wakeLevelBars=[...wakeOverlay.querySelectorAll(".wake-levels i")];
  const wakeFallbackAttempts=[];
  const WAKE_FALLBACK_LIMIT=20;
  const wakeShadowEnabled=document.getElementById("wake-shadow-enabled"),wakeShadowThreshold=document.getElementById("wake-shadow-threshold");
  const wakeLocalActivate=document.getElementById("wake-local-activate"),wakeConversationEnabled=document.getElementById("wake-conversation-enabled"),wakeConversationStop=document.getElementById("wake-conversation-stop");
  const wakeShadowThresholdValue=document.getElementById("wake-shadow-threshold-value"),wakeShadowHealth=document.getElementById("wake-shadow-health");
  const wakeShadowScore=document.getElementById("wake-shadow-score"),wakeShadowPeak=document.getElementById("wake-shadow-peak"),wakeShadowDetections=document.getElementById("wake-shadow-detections");
  const wakeShadowFalse=document.getElementById("wake-shadow-false"),wakeShadowRuntime=document.getElementById("wake-shadow-runtime"),wakeShadowMessage=document.getElementById("wake-shadow-message");
  const wakeMicRms=document.getElementById("wake-mic-rms"),wakeMicPeak=document.getElementById("wake-mic-peak"),wakeAttemptResults=document.getElementById("wake-attempt-results"),wakeTestPhrase=document.getElementById("wake-test-phrase");
  const WAKE_SHADOW_KEY="zbrano_wake_shadow_v1";
  let wakeLocalActivationAt=0,wakeConversationArmed=false,wakeConversationListening=false,wakeConversationWaitTimer=null,wakeConversationHealthTimer=null;
  const wakePositiveCount=document.getElementById("wake-positive-count"),wakeNegativeCount=document.getElementById("wake-negative-count"),wakeVerifierState=document.getElementById("wake-verifier-state"),wakeCalibrationMessage=document.getElementById("wake-calibration-message"),wakeTrainVerifier=document.getElementById("wake-train-verifier"),wakeUseVerifier=document.getElementById("wake-use-verifier"),wakeDeleteVerifier=document.getElementById("wake-delete-verifier");
  let wakeShadowStats={peak:0,detections:0,falseDetections:0,frames:0,runtimeMs:0,startedAt:0};
  try{wakeShadowStats={...wakeShadowStats,...JSON.parse(localStorage.getItem(WAKE_SHADOW_KEY)||"{}")}}catch{}

  function renderWakeShadow(score=0){
    const activeMs=Number(wakeShadowStats.runtimeMs||0)+(wakeShadowStats.startedAt?Date.now()-wakeShadowStats.startedAt:0);
    wakeShadowScore.textContent=Number(score||0).toFixed(3);wakeShadowPeak.textContent=Number(wakeShadowStats.peak||0).toFixed(3);
    wakeShadowDetections.textContent=String(wakeShadowStats.detections||0);wakeShadowFalse.textContent=String(wakeShadowStats.falseDetections||0);
    wakeShadowRuntime.textContent=activeMs<3600000?`${Math.floor(activeMs/60000)}m`:`${(activeMs/3600000).toFixed(1)}h`;wakeMicRms.textContent=Number(wakeShadowInputRms||0).toFixed(3);wakeMicPeak.textContent=Number(wakeShadowInputPeak||0).toFixed(3);
  }
  function saveWakeShadow(){
    const snapshot={...wakeShadowStats};if(snapshot.startedAt){snapshot.runtimeMs=Number(snapshot.runtimeMs||0)+Date.now()-snapshot.startedAt;snapshot.startedAt=Date.now();wakeShadowStats.startedAt=snapshot.startedAt}
    localStorage.setItem(WAKE_SHADOW_KEY,JSON.stringify(snapshot));wakeShadowStats={...snapshot};renderWakeShadow(Number(wakeShadowScore.textContent)||0);
  }
  function stopWakeShadow(){
    if(wakeShadowSaveTimer)clearInterval(wakeShadowSaveTimer);wakeShadowSaveTimer=null;if(wakeShadowAttemptTimer)clearTimeout(wakeShadowAttemptTimer);wakeShadowAttemptTimer=null;wakeShadowAttempt=null;wakeShadowInputRms=0;wakeShadowInputPeak=0;if(wakeTestPhrase)wakeTestPhrase.disabled=false;
    if(wakeShadowProcessor){wakeShadowProcessor.onaudioprocess=null;try{wakeShadowProcessor.disconnect()}catch{}}wakeShadowProcessor=null;
    if(wakeShadowMute){try{wakeShadowMute.disconnect()}catch{}}wakeShadowMute=null;wakeShadowPcm=[];wakeShadowHistory=[];wakeShadowLastCandidate=null;wakeCalibrationCapture=null;wakeShadowAbove=0;wakeShadowLatched=false;
    if(wakeShadowSocket){try{wakeShadowSocket.close()}catch{}}wakeShadowSocket=null;
    if(wakeShadowStats.startedAt){wakeShadowStats.runtimeMs=Number(wakeShadowStats.runtimeMs||0)+Date.now()-wakeShadowStats.startedAt;wakeShadowStats.startedAt=0;localStorage.setItem(WAKE_SHADOW_KEY,JSON.stringify(wakeShadowStats))}
    wakeShadowHealth.textContent=wakeShadowEnabled.checked?"PAUSED":"OFF";wakeShadowHealth.dataset.state="off";renderWakeShadow(0);
  }
  function resampleWakeShadow(input,inputRate){
    const ratio=inputRate/16000,length=Math.max(1,Math.floor(input.length/ratio)),output=new Int16Array(length);
    for(let index=0;index<length;index++){const start=Math.floor(index*ratio),end=Math.min(input.length,Math.floor((index+1)*ratio));let sum=0;for(let sample=start;sample<end;sample++)sum+=input[sample];const value=sum/Math.max(1,end-start);output[index]=Math.max(-32768,Math.min(32767,Math.round(value*32767)))}return output;
  }
  function encodeWakeCalibrationWav(samples){
    const buffer=new ArrayBuffer(44+samples.length*2),view=new DataView(buffer);const text=(offset,value)=>{for(let i=0;i<value.length;i++)view.setUint8(offset+i,value.charCodeAt(i))};
    text(0,"RIFF");view.setUint32(4,36+samples.length*2,true);text(8,"WAVE");text(12,"fmt ");view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,16000,true);view.setUint32(28,32000,true);view.setUint16(32,2,true);view.setUint16(34,16,true);text(36,"data");view.setUint32(40,samples.length*2,true);for(let i=0;i<samples.length;i++)view.setInt16(44+i*2,samples[i],true);return new Blob([buffer],{type:"audio/wav"});
  }
  function wakeCalibrationError(data,status){
    const detail=data?.detail;if(typeof detail==="string")return detail;if(Array.isArray(detail))return detail.map(item=>item?.msg||JSON.stringify(item)).join("; ");if(detail&&typeof detail==="object")return JSON.stringify(detail);return `HTTP ${status}`;
  }
  async function loadWakeCalibration(){
    try{const response=await fetch("api/voice/wake-calibration",{cache:"no-store"}),data=await response.json();if(!response.ok)throw new Error(wakeCalibrationError(data,response.status));wakePositiveCount.textContent=`${data.positive} / ${data.required_each} valid${data.positive_invalid?` · ${data.positive_invalid} invalid`:""}`;wakeNegativeCount.textContent=`${data.negative} / ${data.required_each} valid${data.negative_invalid?` · ${data.negative_invalid} invalid`:""}`;wakeVerifierState.textContent=data.verifier_trained?(data.verifier_enabled?"Trained · enabled":"Trained · off"):"Not trained";wakeUseVerifier.checked=data.verifier_enabled===true;wakeUseVerifier.disabled=!data.verifier_trained||wakeCalibrationBusy;wakeDeleteVerifier.disabled=!data.verifier_trained||wakeCalibrationBusy;wakeTrainVerifier.disabled=!data.ready_to_train||wakeCalibrationBusy;return data}catch(error){wakeCalibrationMessage.textContent=`Calibration status unavailable: ${error.message||error}`;return null}
  }
  async function uploadWakeCalibration(label,samples,message){
    if(!samples||samples.length<16000)return;wakeCalibrationBusy=true;wakeCalibrationMessage.textContent="Saving calibration clip locally...";
    try{const body=new FormData();body.append("audio",encodeWakeCalibrationWav(samples),`${label}.wav`);const response=await fetch(`api/voice/wake-calibration/samples/${label}`,{method:"POST",body}),data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(wakeCalibrationError(data,response.status));const quality=data.quality||{};wakeCalibrationMessage.textContent=`${message} RMS ${Number(quality.rms||0).toFixed(3)}, peak ${Number(quality.peak||0).toFixed(3)}.`}catch(error){wakeCalibrationMessage.textContent=`Calibration clip failed: ${error.message||error}`}finally{wakeCalibrationBusy=false;await loadWakeCalibration()}
  }
  function recordWakeCalibration(label){
    if(wakeCalibrationBusy||wakeCalibrationCapture)return;if(!wakeShadowSocket||wakeShadowSocket.readyState!==WebSocket.OPEN){wakeCalibrationMessage.textContent="Enable wake listening and Local Wake Shadow Test first.";return}
    wakeCalibrationCapture={label,samples:[],started:false,armedAt:performance.now(),lastVoiceAt:0};wakeCalibrationMessage.textContent=label==="positive"?'Armed - say "Hey ZBRANO" once. Recording begins when speech is detected.':"Armed - speak one normal sentence. Recording begins when speech is detected.";
  }
  function finishWakeCalibrationCapture(){
    const capture=wakeCalibrationCapture;wakeCalibrationCapture=null;if(!capture)return;uploadWakeCalibration(capture.label,new Int16Array(capture.samples),capture.label==="positive"?'Wake-phrase sample saved. Record another with a natural variation.':"Other-speech sample saved. Use a different normal sentence next.");
  }
  function finishWakeShadowAttempt(){
    if(wakeShadowAttemptTimer)clearTimeout(wakeShadowAttemptTimer);wakeShadowAttemptTimer=null;const attempt=wakeShadowAttempt;wakeShadowAttempt=null;wakeTestPhrase.disabled=false;if(!attempt)return;
    const detected=attempt.detected===true,item=document.createElement("li");wakeShadowAttemptNumber++;item.dataset.result=detected?"detected":"missed";item.textContent=`Test ${wakeShadowAttemptNumber}: ${detected?"DETECTED":"MISSED"} · model ${attempt.score.toFixed(3)} · RMS ${attempt.rms.toFixed(3)} · mic peak ${attempt.peak.toFixed(3)}`;wakeAttemptResults.prepend(item);while(wakeAttemptResults.children.length>10)wakeAttemptResults.lastElementChild.remove();wakeShadowMessage.textContent=detected?"Phrase detected. Compare microphone level with missed tests.":"Phrase missed. The input measurements show whether audio reached the model.";
  }
  function startWakeShadowAttempt(){
    if(!wakeShadowSocket||wakeShadowSocket.readyState!==WebSocket.OPEN){wakeShadowMessage.textContent="Enable wake listening and Local Wake Shadow Test first.";return}if(wakeShadowAttempt)finishWakeShadowAttempt();wakeShadowAttempt={score:0,rms:0,peak:0,above:0,detected:false};wakeTestPhrase.disabled=true;wakeShadowMessage.textContent='Say “Hey ZBRANO” once now. Measuring for four seconds...';wakeShadowAttemptTimer=setTimeout(finishWakeShadowAttempt,4000);
  }
  function handleWakeShadowScore(score){
    score=Math.max(0,Math.min(1,Number(score)||0));wakeShadowStats.frames++;wakeShadowStats.peak=Math.max(Number(wakeShadowStats.peak||0),score);if(wakeShadowAttempt){wakeShadowAttempt.score=Math.max(wakeShadowAttempt.score,score);wakeShadowAttempt.above=score>=Number(wakeShadowThreshold.value||.5)?wakeShadowAttempt.above+1:0;if(wakeShadowAttempt.above>=2)wakeShadowAttempt.detected=true}
    const threshold=Number(wakeShadowThreshold.value||.5),playbackActive=Boolean(activeAudio||speechQueueRunning),activationThreshold=playbackActive?Math.max(.68,threshold+.12):threshold,requiredFrames=playbackActive?3:2;wakeShadowAbove=score>=activationThreshold?wakeShadowAbove+1:0;
    if(wakeShadowAbove>=requiredFrames&&!wakeShadowLatched){
      wakeShadowLatched=true;wakeShadowStats.detections++;wakeShadowLastCandidate=new Int16Array(wakeShadowHistory.slice(-64000));
      const playbackContainsWake=wakeCandidates().some(candidate=>conversationPhrase(activeSpeechText).includes(candidate)),activationReady=wakeLocalActivate.checked&&wakeFallbackMode==="wake"&&!wakeShadowAttempt&&!wakeCalibrationCapture&&!pendingSuggestion&&Date.now()-wakeLocalActivationAt>=8000,canBargeIn=activationReady&&playbackActive&&!playbackContainsWake,canActivate=activationReady&&!playbackActive&&!activeRequest;
      if(canBargeIn){wakeLocalActivationAt=Date.now();startPlaybackWakeBargeIn(score)}
      else if(canActivate){wakeLocalActivationAt=Date.now();wakeShadowMessage.textContent=`Local wake activation ${wakeShadowStats.detections} at ${score.toFixed(3)}.`;stopRecognition(wakeRecognition);wakeRecognition=null;if(wakeFallbackStream&&startFallbackCommandWindow())showWakeOverlay("LOCAL WAKE PHRASE HEARD","Speak your command...");else{stopWake();setTimeout(startCommandWindow,180)}}
      else wakeShadowMessage.textContent=`Silent detection ${wakeShadowStats.detections} at ${score.toFixed(3)}.${wakeLocalActivate.checked?" Activation was busy or cooling down.":" Chat was not activated."}`;
    }
    if(score<activationThreshold*.55)wakeShadowLatched=false;renderWakeShadow(score);
  }
  function startWakeShadow(context,source){
    stopWakeShadow();if(!wakeShadowEnabled.checked)return;
    const endpoint=new URL("api/voice/wake-shadow",document.baseURI);endpoint.protocol=endpoint.protocol==="https:"?"wss:":"ws:";
    const socket=new WebSocket(endpoint);wakeShadowSocket=socket;socket.binaryType="arraybuffer";wakeShadowHealth.textContent="STARTING";wakeShadowHealth.dataset.state="starting";
    const processor=context.createScriptProcessor(4096,1,1),mute=context.createGain();mute.gain.value=0;wakeShadowProcessor=processor;wakeShadowMute=mute;source.connect(processor);processor.connect(mute);mute.connect(context.destination);
    processor.onaudioprocess=event=>{if(socket.readyState!==WebSocket.OPEN)return;const converted=resampleWakeShadow(event.inputBuffer.getChannelData(0),context.sampleRate);let energy=0,inputPeak=0;for(const sample of converted){const normalized=sample/32768;energy+=normalized*normalized;inputPeak=Math.max(inputPeak,Math.abs(normalized));wakeShadowPcm.push(sample);wakeShadowHistory.push(sample)}wakeShadowInputRms=Math.sqrt(energy/Math.max(1,converted.length));wakeShadowInputPeak=inputPeak;if(wakeShadowAttempt){wakeShadowAttempt.rms=Math.max(wakeShadowAttempt.rms,wakeShadowInputRms);wakeShadowAttempt.peak=Math.max(wakeShadowAttempt.peak,wakeShadowInputPeak)}if(wakeShadowHistory.length>80000)wakeShadowHistory.splice(0,wakeShadowHistory.length-80000);if(wakeCalibrationCapture){const capture=wakeCalibrationCapture,now=performance.now();let startedNow=false;if(!capture.started&&wakeShadowInputRms>=.012){capture.started=true;startedNow=true;capture.samples=Array.from(wakeShadowHistory.slice(-8000));capture.lastVoiceAt=now;wakeCalibrationMessage.textContent="Speech detected â€” recording this utterance..."}if(capture.started){if(!startedNow)for(const sample of converted)capture.samples.push(sample);if(wakeShadowInputRms>=.008)capture.lastVoiceAt=now;if((capture.samples.length>=16000&&now-capture.lastVoiceAt>=650)||capture.samples.length>=64000)finishWakeCalibrationCapture()}else if(now-capture.armedAt>=8000){wakeCalibrationCapture=null;wakeCalibrationMessage.textContent="No speech detected in eight seconds. Check the live microphone level and try again."}}while(wakeShadowPcm.length>=1280&&socket.bufferedAmount<65536){const frame=new Int16Array(wakeShadowPcm.splice(0,1280));socket.send(frame.buffer)}};
    socket.addEventListener("message",event=>{let data;try{data=JSON.parse(event.data)}catch{return}if(data.type==="ready"){wakeShadowStats.startedAt=Date.now();wakeShadowHealth.textContent="SHADOW";wakeShadowHealth.dataset.state="active";wakeShadowMessage.textContent=data.verifier?"Personal verifier ready in silent shadow mode.":"Local base model ready. Scores are silent and cannot activate chat.";wakeShadowSaveTimer=setInterval(saveWakeShadow,5000);loadWakeCalibration()}else if(data.type==="score")handleWakeShadowScore(data.score);else if(data.type==="error"){wakeShadowHealth.textContent="ERROR";wakeShadowHealth.dataset.state="error";wakeShadowMessage.textContent=`Local model unavailable: ${data.message||"unknown error"}`}});
    socket.addEventListener("error",()=>{wakeShadowHealth.textContent="ERROR";wakeShadowHealth.dataset.state="error";wakeShadowMessage.textContent="Local shadow detector could not connect."});
    socket.addEventListener("close",()=>{if(wakeShadowSocket===socket){wakeShadowSocket=null;if(wakeShadowEnabled.checked){wakeShadowHealth.textContent="PAUSED";wakeShadowHealth.dataset.state="off"}}});
  }
  wakeShadowEnabled.checked=localStorage.getItem("zbrano_wake_shadow_enabled")==="true";wakeShadowThreshold.value=localStorage.getItem("zbrano_wake_shadow_threshold")||"0.50";wakeShadowThresholdValue.textContent=Number(wakeShadowThreshold.value).toFixed(2);wakeLocalActivate.checked=localStorage.getItem("zbrano_wake_local_activate")==="true";wakeConversationEnabled.checked=localStorage.getItem("zbrano_wake_conversation")==="true";wakeConversationStop.value=localStorage.getItem("zbrano_wake_conversation_stop")||"ok thank you";renderWakeShadow();

  function stopRecognition(instance){if(!instance)return;instance.onend=null;try{instance.abort()}catch{}}
  function updateWakeListeningLevel(rms=0,peak=0){
    const floor=Math.max(.006,Number(wakeNoiseFloor)||.008),level=Math.max(0,Math.min(1,Math.max((Number(rms)-floor)/Math.max(.045,floor*5),Number(peak)/.32))),now=performance.now();
    const shape=[.28,.44,.64,.84,1,.84,.64,.44,.28];
    wakeLevelBars.forEach((bar,index)=>{const pulse=.72+.28*Math.sin(now/90+index*1.17),energy=Math.max(.06,level*shape[index]*pulse);bar.style.height=`${(3+energy*23).toFixed(1)}px`;bar.style.opacity=String((.28+energy*.72).toFixed(2))});
  }
  function clearWakeFallbackCommandTimer(){if(wakeFallbackCommandTimer)clearTimeout(wakeFallbackCommandTimer);wakeFallbackCommandTimer=null}
  function clearWakeConversationHealth(){if(wakeConversationHealthTimer)clearTimeout(wakeConversationHealthTimer);wakeConversationHealthTimer=null}
  function discardWakeFallbackRecorder(){
    const recorder=wakeFallbackRecorder;wakeFallbackRecorder=null;wakeFallbackChunks=[];wakeFallbackSpeechStart=0;wakeFallbackLastVoice=0;wakeFallbackVoiceFrames=0;wakeFallbackFinalizing=false;
    if(wakeFallbackCaptureTimer)clearTimeout(wakeFallbackCaptureTimer);wakeFallbackCaptureTimer=null;
    if(recorder){recorder.ondataavailable=null;recorder.onstop=null;try{if(recorder.state!=="inactive")recorder.stop()}catch{}}
  }
  function beginWakeFallbackRecorder(){
    if(wakeFallbackRecorder?.state==="recording")return true;if(wakeFallbackRecorder)discardWakeFallbackRecorder();
    const liveTrack=wakeFallbackStream?.getAudioTracks().some(track=>track.readyState==="live"&&track.enabled&&!track.muted);if(!liveTrack)return false;
    try{const mimeType=recordingMimeType(),recorder=new MediaRecorder(wakeFallbackStream,mimeType?{mimeType}:undefined),chunks=[];recorder.ondataavailable=event=>{if(event.data.size)chunks.push(event.data)};recorder.start(100);wakeFallbackRecorder=recorder;wakeFallbackChunks=chunks;return true}
    catch(error){status(`Reliable wake audio capture failed: ${error.message||error}`,"error");return false}
  }
  function wakeFallbackCaptureHealthy(requireRecorder=false){
    const liveTrack=wakeFallbackStream?.getAudioTracks().some(track=>track.readyState==="live"&&track.enabled&&!track.muted),samplesFresh=performance.now()-wakeFallbackLastSampleAt<400;
    return Boolean(liveTrack&&wakeFallbackContext?.state==="running"&&wakeFallbackAnalyser&&wakeFallbackTimer&&samplesFresh&&(!requireRecorder||wakeFallbackRecorder?.state==="recording"));
  }
  function stopWakeFallback(){
    wakeFallbackGeneration++;wakeFallbackStartToken++;clearWakeFallbackCommandTimer();clearWakeConversationHealth();
    if(wakeFallbackTimer)clearInterval(wakeFallbackTimer);wakeFallbackTimer=null;
    discardWakeFallbackRecorder();
    if(wakeFallbackStream)wakeFallbackStream.getTracks().forEach(track=>track.stop());
    stopWakeShadow();
    if(wakeFallbackContext)wakeFallbackContext.close().catch(()=>{});
    wakeFallbackStream=null;wakeFallbackContext=null;wakeFallbackAnalyser=null;wakeFallbackBusy=false;wakeFallbackMode="wake";wakeFallbackStarting=false;wakeFallbackLastSampleAt=0;updateWakeListeningLevel();
  }
  function stopWake(preserveFallback=false){if(wakeRestart)clearTimeout(wakeRestart);wakeRestart=null;stopRecognition(wakeRecognition);wakeRecognition=null;if(!preserveFallback)stopWakeFallback()}

  function startFallbackCommandWindow(){
    wakeFallbackGeneration++;wakeFallbackMode="command";discardWakeFallbackRecorder();wakeNoiseFloor=Math.min(wakeNoiseFloor,.012);wakeFallbackCalibratingUntil=Math.min(wakeFallbackCalibratingUntil,performance.now()+160);
    if(!beginWakeFallbackRecorder()){wakeFallbackMode="wake";return false}
    clearWakeFallbackCommandTimer();const generation=wakeFallbackGeneration;
    wakeFallbackCommandTimer=setTimeout(()=>{if(generation!==wakeFallbackGeneration)return;wakeConversationListening=false;discardWakeFallbackRecorder();wakeFallbackMode="wake";hideWakeOverlay(250);status(`No command heard - listening for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");scheduleWake()},wakeConversationListening?15000:9000);
    status("Wake phrase heard - reliable listener is waiting for your command","listening");
    return true;
  }

  function startPlaybackWakeBargeIn(score){
    wakeShadowMessage.textContent=`Playback wake interruption detected at ${score.toFixed(3)}.`;stopRecognition(wakeRecognition);wakeRecognition=null;wakeConversationArmed=false;wakeConversationListening=false;interruptActiveResponseForVoice();status("Wake phrase heard - clearing speaker audio...","listening");
    const stream=wakeFallbackStream;setTimeout(()=>{if(!wakeEnabled.checked||document.hidden||wakeFallbackStream!==stream)return;if(startFallbackCommandWindow())showWakeOverlay("WAKE PHRASE HEARD","Speak your new command...");else{hideWakeOverlay();stopWake();scheduleWake(350)}},240);
  }

  function fallbackRateAllowed(mode){
    const now=Date.now();const cutoff=now-3600000;while(wakeFallbackAttempts.length&&wakeFallbackAttempts[0]<cutoff)wakeFallbackAttempts.shift();
    if(mode==="wake"&&now-Number(fallbackRateAllowed.lastWakeAt||0)<6000){status(`Reliable wake listening active for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");return false}
    if(wakeFallbackAttempts.length>=WAKE_FALLBACK_LIMIT){wakeEnabled.checked=false;status("Reliable wake listening reached its 20-transcription hourly safety limit. Turn it on again later.","error");stopWake();return false}
    if(mode==="wake")fallbackRateAllowed.lastWakeAt=now;wakeFallbackAttempts.push(now);return true;
  }

  async function transcribeWakeFallback(blob,mode,generation){
    if(wakeFallbackBusy||generation!==wakeFallbackGeneration||!wakeEnabled.checked||!fallbackRateAllowed(mode))return;
    wakeFallbackFinalizing=false;wakeFallbackBusy=true;status(mode==="command"?"Transcribing your command...":"Checking detected speech for the wake phrase...","listening");
    try{
      const extension=blob.type.includes("mp4")?"m4a":"webm";const body=new FormData();body.append("audio",blob,`zbrano-wake.${extension}`);
      const response=await fetch("api/voice/wake-transcribe",{method:"POST",body});const data=await response.json().catch(()=>({}));
      if(generation!==wakeFallbackGeneration)return;
      if(!response.ok){if(response.status!==422)throw new Error(data.detail||`HTTP ${response.status}`);status(mode==="command"?"No speech recognized - still listening...":`Reliable wake listening active for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");return}
      const transcript=String(data.text||"").trim();if(!transcript){if(mode==="command")status("No speech recognized - still listening...","listening");return}
      if(mode==="command"){
        clearWakeFallbackCommandTimer();stopWake();updateWakeOverlay(transcript);submitVoiceCommand(transcript);return;
      }
      const match=matchWakePhrase(transcript);
      if(!match){status(`Reliable listener heard "${transcript}" - waiting for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");return}
      stopRecognition(wakeRecognition);wakeRecognition=null;
      if(match.command){showWakeOverlay("WAKE PHRASE HEARD",match.command);stopWake();submitVoiceCommand(match.command)}else if(startFallbackCommandWindow())showWakeOverlay("WAKE PHRASE HEARD","Speak your command...");else{stopWake();hideWakeOverlay();scheduleWake(350)}
    }catch(error){if(generation===wakeFallbackGeneration)status(`Reliable wake transcription unavailable: ${error.message||error}`,"error")}
    finally{wakeFallbackBusy=false;wakeFallbackFinalizing=false;if(mode==="command"&&generation===wakeFallbackGeneration&&wakeFallbackMode==="command"&&!wakeFallbackRecorder)beginWakeFallbackRecorder()}
  }

  function finishWakeFallbackUtterance(now){
    const started=wakeFallbackSpeechStart;const ended=Math.max(wakeFallbackLastVoice,now);const mode=wakeFallbackMode;const generation=wakeFallbackGeneration;
    const recorder=wakeFallbackRecorder;const chunks=wakeFallbackChunks;wakeFallbackRecorder=null;wakeFallbackChunks=[];
    if(wakeFallbackCaptureTimer)clearTimeout(wakeFallbackCaptureTimer);wakeFallbackCaptureTimer=null;
    wakeFallbackSpeechStart=0;wakeFallbackLastVoice=0;wakeFallbackVoiceFrames=0;
    if(!recorder||recorder.state==="inactive"){status(`Reliable wake listening active for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");if(mode==="command"&&generation===wakeFallbackGeneration)beginWakeFallbackRecorder();return}
    const validDuration=ended-started>=550;wakeFallbackFinalizing=true;status("Finalizing wake audio...","listening");
    recorder.onstop=()=>{
      if(generation!==wakeFallbackGeneration){wakeFallbackFinalizing=false;return}
      if(!validDuration||!chunks.length){wakeFallbackFinalizing=false;status(`Reliable wake listening active for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");if(mode==="command")beginWakeFallbackRecorder();return}
      const blob=new Blob(chunks,{type:recorder.mimeType||"audio/webm"});
      setTimeout(()=>{if(generation!==wakeFallbackGeneration)return;if(mode==="wake"&&wakeNativeMatchAt>=started)return;transcribeWakeFallback(blob,mode,generation)},250);
    };
    recorder.onerror=event=>{wakeFallbackFinalizing=false;if(generation===wakeFallbackGeneration){status(`Reliable wake audio failed: ${event.error?.message||"recorder error"}`,"error");if(mode==="command")beginWakeFallbackRecorder()}};
    try{recorder.requestData();recorder.stop()}catch(error){wakeFallbackFinalizing=false;status(`Reliable wake audio finalization failed: ${error.message||error}`,"error");if(mode==="command"&&generation===wakeFallbackGeneration)beginWakeFallbackRecorder()}
  }

  function sampleWakeFallback(){
    if(!wakeFallbackAnalyser||(wakeShadowEnabled.checked&&wakeFallbackMode==="wake"))return;
    const samples=new Uint8Array(wakeFallbackAnalyser.fftSize);wakeFallbackAnalyser.getByteTimeDomainData(samples);
    let energy=0,peak=0;for(const sample of samples){const value=(sample-128)/128;energy+=value*value;peak=Math.max(peak,Math.abs(value))}const rms=Math.sqrt(energy/samples.length);const now=performance.now();wakeFallbackLastSampleAt=now;updateWakeListeningLevel(rms,peak);if(wakeFallbackBusy||wakeFallbackFinalizing)return;
    if(now<wakeFallbackCalibratingUntil){wakeNoiseFloor=Math.min(.08,wakeNoiseFloor*.9+rms*.1);wakeFallbackVoiceFrames=0;return}
    const threshold=Math.max(.032,wakeNoiseFloor*2.8);const strongVoice=rms>threshold&&peak>Math.max(.085,wakeNoiseFloor*4.2);
    if(!wakeFallbackSpeechStart){
      if(!strongVoice)wakeNoiseFloor=Math.min(.08,wakeNoiseFloor*.98+rms*.02);
      wakeFallbackVoiceFrames=strongVoice?wakeFallbackVoiceFrames+1:0;
      if(wakeFallbackVoiceFrames>=3){
        try{
          if(!beginWakeFallbackRecorder())return;const recorder=wakeFallbackRecorder;
          wakeFallbackSpeechStart=now;wakeFallbackLastVoice=now;
          if(wakeFallbackCaptureTimer)clearTimeout(wakeFallbackCaptureTimer);
          wakeFallbackCaptureTimer=setTimeout(()=>{if(wakeFallbackRecorder===recorder&&wakeFallbackSpeechStart)finishWakeFallbackUtterance(performance.now())},8500);
          status("Speech detected - recording wake utterance...","listening");
        }catch(error){wakeFallbackVoiceFrames=0;status(`Reliable wake audio capture failed: ${error.message||error}`,"error")}
      }
      return;
    }
    const continuingVoice=rms>threshold*.82&&peak>Math.max(.065,wakeNoiseFloor*3.4);
    if(continuingVoice)wakeFallbackLastVoice=now;
    if(now-wakeFallbackSpeechStart>=8000||now-wakeFallbackLastVoice>=720)finishWakeFallbackUtterance(now);
  }

  async function startWakeFallback(){
    if(wakeFallbackStarting||!wakeEnabled.checked||document.hidden)return false;
    if(wakeFallbackStream){
      const liveTrack=wakeFallbackStream.getAudioTracks().some(track=>track.readyState==="live"&&track.enabled&&!track.muted);
      if(liveTrack&&wakeFallbackContext&&wakeFallbackAnalyser){try{if(wakeFallbackContext.state==="suspended")await wakeFallbackContext.resume();if(wakeFallbackContext.state==="running")return true}catch{}}
      stopWakeFallback();
    }
    const startToken=++wakeFallbackStartToken;wakeFallbackStarting=true;
    try{
      const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}});
      if(startToken!==wakeFallbackStartToken||!wakeEnabled.checked||document.hidden){stream.getTracks().forEach(track=>track.stop());return false}
      const AudioContextClass=window.AudioContext||window.webkitAudioContext;if(!AudioContextClass||!window.MediaRecorder)throw new Error("browser audio monitoring is unavailable");
      const context=new AudioContextClass();await context.resume();const analyser=context.createAnalyser();analyser.fftSize=512;const source=context.createMediaStreamSource(stream);source.connect(analyser);
      if(startToken!==wakeFallbackStartToken||!wakeEnabled.checked||document.hidden){stream.getTracks().forEach(track=>track.stop());context.close().catch(()=>{});return false}
      wakeFallbackStream=stream;wakeFallbackContext=context;wakeFallbackAnalyser=analyser;wakeFallbackRecorder=null;wakeFallbackMode="wake";wakeFallbackChunks=[];
      wakeNoiseFloor=.008;wakeFallbackCalibratingUntil=performance.now()+2500;wakeFallbackPeak=0;
      startWakeShadow(context,source);
      wakeFallbackTimer=setInterval(sampleWakeFallback,80);status("Calibrating reliable wake microphone...","listening");
      setTimeout(()=>{if(wakeFallbackStream&&wakeEnabled.checked)status(`Reliable wake listening active for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening")},2600);
      return true;
    }catch(error){status(`Reliable wake listener unavailable: ${error.message||error}. Trying Chrome speech recognition...`,"error");stopWakeFallback();return false}
    finally{if(startToken===wakeFallbackStartToken)wakeFallbackStarting=false}
  }
  function recognitionLanguage(){const preferred=String(jarvisPreferences?.preferred_language||"").trim();return preferred&&preferred!=="auto"?preferred:document.documentElement.lang||navigator.language||"en-US"}
  function wakeCanRun(){return Boolean(wakeEnabled.checked&&Recognition&&!braveBrowser&&!document.hidden&&!pendingSuggestion&&!activeAudio&&!speechQueueRunning&&!mediaRecorder&&!activeRequest)}
  function showWakeCompatibility(){
    if(braveBrowser){wakeEnabled.checked=false;stopWake();status("Browser wake phrase is unavailable in Brave. Use Chrome or Edge, or connect a local Home Assistant voice satellite. Push-to-talk still works.","error");return false}
    if(!Recognition){wakeEnabled.checked=false;stopWake();status("Wake phrase is unavailable in this browser. Use current Chrome or Edge, or connect a local Home Assistant voice satellite.","error");return false}
    return true;
  }

  let wakeOverlayTimer=null;
  function showWakeOverlay(title="ZBRANO IS LISTENING",transcript="Speak your command…"){
    if(wakeOverlayTimer)clearTimeout(wakeOverlayTimer);wakeOverlayTimer=null;
    wakeOverlayTitle.textContent=title;wakeOverlayTranscript.textContent=transcript;
    updateWakeListeningLevel();wakeOverlay.hidden=false;requestAnimationFrame(()=>wakeOverlay.classList.add("active"));
  }
  function updateWakeOverlay(transcript){wakeOverlayTranscript.textContent=String(transcript||"Speak your command…")}
  function hideWakeOverlay(delay=0){
    if(wakeOverlayTimer)clearTimeout(wakeOverlayTimer);
    wakeOverlayTimer=setTimeout(()=>{wakeOverlay.classList.remove("active");updateWakeListeningLevel();setTimeout(()=>{wakeOverlay.hidden=true},180)},Math.max(0,delay));
  }
  function submitVoiceCommand(command){
    const value=String(command||"").trim();if(!value)return false;
    const normalized=conversationPhrase(value),preferredStop=conversationPhrase(wakeConversationStop.value||"ok thank you");
    const builtInStop=/^(?:please )?(?:stop|end|exit|cancel)(?: the)? conversation(?: mode)?(?: please)?$/.test(normalized);
    if(wakeConversationListening&&(normalized===preferredStop||builtInStop)){
      wakeConversationListening=false;wakeConversationArmed=false;clearWakeFallbackCommandTimer();wakeFallbackMode="wake";hideWakeOverlay(250);status("Conversation mode ended");scheduleWake();return true;
    }
    wakeConversationListening=false;wakeConversationArmed=true;updateWakeOverlay(value);input.value=value;input.dispatchEvent(new Event("input",{bubbles:true}));form.requestSubmit();hideWakeOverlay(420);return true;
  }

  function startCommandWindow(){
    stopWake();stopRecognition(commandRecognition);showWakeOverlay();
    if(!Recognition){status("Wake phrase is unavailable in this browser.","error");hideWakeOverlay();return}
    const recognition=new Recognition();commandRecognition=recognition;recognition.lang=recognitionLanguage();recognition.continuous=false;recognition.interimResults=false;
    let handled=false;const timer=setTimeout(()=>{try{recognition.stop()}catch{}},9000);
    recognition.onresult=event=>{const transcript=event.results?.[event.results.length-1]?.[0]?.transcript||"";updateWakeOverlay(transcript||"Listening…");handled=submitVoiceCommand(transcript);if(handled)status(`Heard: ${transcript}`)};
    recognition.onerror=event=>{if(event.error!=="aborted")status(`Voice command unavailable: ${event.error}`,"error");updateWakeOverlay(event.error==="no-speech"?"No command heard":`Microphone error: ${event.error}`);hideWakeOverlay(650)};
    recognition.onend=()=>{clearTimeout(timer);if(commandRecognition===recognition)commandRecognition=null;if(!handled){updateWakeOverlay("No command heard");hideWakeOverlay(650)}if(!handled&&wakeEnabled.checked)status(`Listening for “${wakePhrase.value.trim()||"hey zbrano"}”`,"listening");scheduleWake()};
    status("Wake phrase heard. Listening for your command…","listening");
    try{recognition.start()}catch(error){clearTimeout(timer);status(`Voice command unavailable: ${error.message||error}`,"error")}
  }

  async function startWake(){
    if(!wakeCanRun())return;
    stopWake(true);await startWakeFallback();
    if(wakeFallbackStream||wakeFallbackStarting){status(wakeFallbackStream?`Reliable wake listening active for "${wakePhrase.value.trim()||"hey zbrano"}"`:"Starting reliable wake listener...","listening");return}
    const recognition=new Recognition();wakeRecognition=recognition;recognition.lang=recognitionLanguage();recognition.continuous=true;recognition.interimResults=true;
    recognition.onstart=()=>status(`Microphone active - listening for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");
    recognition.onresult=event=>{
      for(let index=event.resultIndex;index<event.results.length;index++){
        const rawTranscript=event.results[index][0]?.transcript||"";const match=matchWakePhrase(rawTranscript);if(match)wakeNativeMatchAt=performance.now();
        if(!match){if(event.results[index].isFinal&&clean(rawTranscript))status(`Heard "${rawTranscript.trim()}" - waiting for "${wakePhrase.value.trim()||"hey zbrano"}"`,"listening");continue}
        if(match.command){stopWake();showWakeOverlay("WAKE PHRASE HEARD",match.command);submitVoiceCommand(match.command)}
        else if(wakeFallbackStream){stopRecognition(wakeRecognition);wakeRecognition=null;if(startFallbackCommandWindow())showWakeOverlay("WAKE PHRASE HEARD","Speak your command...");else{stopWake();hideWakeOverlay();scheduleWake(350)}}
        else{stopWake();showWakeOverlay("WAKE PHRASE HEARD","Speak your command...");setTimeout(startCommandWindow,180)}break;
      }
    };
    recognition.onerror=event=>{if(event.error==="not-allowed"||event.error==="service-not-allowed"){wakeEnabled.checked=false;status("Microphone permission was denied. Enable it in the browser, then turn wake listening on again.","error")}else if(event.error!=="aborted")status(`Wake listening paused: ${event.error}`,"error")};
    recognition.onend=()=>{if(wakeRecognition===recognition)wakeRecognition=null;scheduleWake()};
    try{recognition.start();status(`Listening for “${wakePhrase.value.trim()||"hey zbrano"}”`,"listening")}catch(error){status(`Wake listening unavailable: ${error.message||error}`,"error")}
  }
  function scheduleWake(delay=1200){if(wakeRestart)clearTimeout(wakeRestart);wakeRestart=setTimeout(()=>{wakeRestart=null;startWake()},Math.max(250,delay))}

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
    pendingSuggestion=item;stopWake();const prompt=String(item.detail||"").trim();
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

  wakeOverlayCancel.addEventListener("click",()=>{stopRecognition(commandRecognition);commandRecognition=null;pendingSuggestion=null;wakeConversationArmed=false;wakeConversationListening=false;if(wakeConversationWaitTimer)clearTimeout(wakeConversationWaitTimer);clearWakeConversationHealth();clearWakeFallbackCommandTimer();wakeFallbackMode="wake";wakeFallbackGeneration++;discardWakeFallbackRecorder();hideWakeOverlay();status("Listening cancelled");scheduleWake()});
  wakeTestPhrase.addEventListener("click",startWakeShadowAttempt);
  document.getElementById("wake-remove-invalid").addEventListener("click",async()=>{if(!confirm("Remove recordings that are silent, too quiet, or materially clipped? Valid recordings will be preserved."))return;wakeCalibrationBusy=true;try{const response=await fetch("api/voice/wake-calibration/invalid",{method:"DELETE"}),data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(wakeCalibrationError(data,response.status));wakeCalibrationMessage.textContent=`Removed ${data.removed||0} invalid recording(s). Valid clips were preserved.`}catch(error){wakeCalibrationMessage.textContent=`Invalid-recording cleanup failed: ${error.message||error}`}finally{wakeCalibrationBusy=false;await loadWakeCalibration()}});
  document.getElementById("wake-export-calibration").addEventListener("click",()=>{const link=document.createElement("a");link.href=new URL("api/voice/wake-calibration/export",document.baseURI).toString();link.download="zbrano-wake-calibration.zip";document.body.appendChild(link);link.click();link.remove()});
  wakeLocalActivate.addEventListener("change",()=>{if(wakeLocalActivate.checked&&!wakeShadowEnabled.checked){wakeShadowEnabled.checked=true;localStorage.setItem("zbrano_wake_shadow_enabled","true")}localStorage.setItem("zbrano_wake_local_activate",String(wakeLocalActivate.checked));stopWake();if(wakeEnabled.checked)scheduleWake();else renderWakeShadow()});
  wakeConversationEnabled.addEventListener("change",()=>{localStorage.setItem("zbrano_wake_conversation",String(wakeConversationEnabled.checked));if(!wakeConversationEnabled.checked){wakeConversationArmed=false;wakeConversationListening=false;if(wakeConversationWaitTimer)clearTimeout(wakeConversationWaitTimer)}});
  wakeConversationStop.addEventListener("change",()=>{wakeConversationStop.value=clean(wakeConversationStop.value)||"ok thank you";localStorage.setItem("zbrano_wake_conversation_stop",wakeConversationStop.value)});
  wakeShadowEnabled.addEventListener("change",()=>{if(!wakeShadowEnabled.checked){wakeLocalActivate.checked=false;localStorage.setItem("zbrano_wake_local_activate","false")}localStorage.setItem("zbrano_wake_shadow_enabled",String(wakeShadowEnabled.checked));stopWake();if(wakeEnabled.checked)scheduleWake();else renderWakeShadow()});
  wakeShadowThreshold.addEventListener("input",()=>{wakeShadowThresholdValue.textContent=Number(wakeShadowThreshold.value).toFixed(2);localStorage.setItem("zbrano_wake_shadow_threshold",wakeShadowThreshold.value);wakeShadowAbove=0;wakeShadowLatched=false});
  document.getElementById("wake-shadow-mark-false").addEventListener("click",async()=>{if(wakeShadowStats.detections>wakeShadowStats.falseDetections){wakeShadowStats.falseDetections++;saveWakeShadow();if(wakeShadowLastCandidate){const candidate=wakeShadowLastCandidate;wakeShadowLastCandidate=null;await uploadWakeCalibration("negative",candidate,"False-trigger clip saved as personal-verifier negative evidence.")}else wakeShadowMessage.textContent="False detection counted; no transient candidate audio remained."}});
  document.getElementById("wake-shadow-reset").addEventListener("click",()=>{wakeShadowStats={peak:0,detections:0,falseDetections:0,frames:0,runtimeMs:0,startedAt:wakeShadowSocket?Date.now():0};wakeShadowAbove=0;wakeShadowLatched=false;saveWakeShadow();wakeShadowMessage.textContent="Shadow statistics reset."});

  document.getElementById("wake-record-positive").addEventListener("click",()=>recordWakeCalibration("positive"));
  document.getElementById("wake-record-negative").addEventListener("click",()=>recordWakeCalibration("negative"));
  wakeTrainVerifier.addEventListener("click",async()=>{if(wakeCalibrationBusy)return;wakeCalibrationBusy=true;wakeTrainVerifier.disabled=true;wakeCalibrationMessage.textContent="Training the personal verifier locally. Keep this page open...";try{const response=await fetch("api/voice/wake-calibration/train",{method:"POST"}),data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(wakeCalibrationError(data,response.status));wakeCalibrationMessage.textContent="Personal verifier trained and saved. The broader base model remains active until you enable the verifier.";await loadWakeCalibration()}catch(error){wakeCalibrationMessage.textContent=`Verifier training failed: ${error.message||error}`}finally{wakeCalibrationBusy=false;await loadWakeCalibration()}});
  wakeUseVerifier.addEventListener("change",async()=>{if(wakeCalibrationBusy)return;wakeCalibrationBusy=true;wakeUseVerifier.disabled=true;try{const enabled=wakeUseVerifier.checked,response=await fetch(`api/voice/wake-calibration/verifier?enabled=${enabled}`,{method:"PUT"}),data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(wakeCalibrationError(data,response.status));wakeCalibrationMessage.textContent=enabled?"Personal verifier enabled. Restarting shadow evaluation...":"Personal verifier disabled. Broader base-model recognition restored.";stopWake();if(wakeEnabled.checked)scheduleWake()}catch(error){wakeCalibrationMessage.textContent=`Verifier setting failed: ${error.message||error}`}finally{wakeCalibrationBusy=false;await loadWakeCalibration()}});
  wakeDeleteVerifier.addEventListener("click",async()=>{if(!confirm("Delete only the trained verifier? Your positive and negative recordings will be preserved."))return;wakeCalibrationBusy=true;try{const response=await fetch("api/voice/wake-calibration/verifier",{method:"DELETE"}),data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(wakeCalibrationError(data,response.status));wakeCalibrationMessage.textContent="Personal verifier deleted. All calibration recordings were preserved.";stopWake();if(wakeEnabled.checked)scheduleWake()}catch(error){wakeCalibrationMessage.textContent=`Verifier deletion failed: ${error.message||error}`}finally{wakeCalibrationBusy=false;await loadWakeCalibration()}});
  document.getElementById("wake-reset-calibration").addEventListener("click",async()=>{if(!confirm("Delete all personal wake clips and the trained verifier?"))return;wakeCalibrationBusy=true;try{const response=await fetch("api/voice/wake-calibration",{method:"DELETE"}),data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(wakeCalibrationError(data,response.status));wakeCalibrationMessage.textContent="Personal wake calibration deleted.";await loadWakeCalibration();stopWake();if(wakeEnabled.checked)scheduleWake()}catch(error){wakeCalibrationMessage.textContent=`Calibration reset failed: ${error.message||error}`}finally{wakeCalibrationBusy=false}});
  loadWakeCalibration();

  wakeEnabled.addEventListener("change",()=>{if(wakeEnabled.checked){if(showWakeCompatibility())startWake()}else{stopWake();hideWakeOverlay();status(braveBrowser?"Browser wake phrase is unavailable in Brave. Use Chrome or Edge, or connect a local Home Assistant voice satellite. Push-to-talk still works.":"Wake listening is off. It works only while this page is open and microphone permission is granted.",braveBrowser?"error":"")}});
  wakePhrase.addEventListener("change",()=>{wakePhrase.value=clean(wakePhrase.value)||"hey zbrano";if(wakeEnabled.checked){stopWake();scheduleWake()}});
  document.addEventListener("visibilitychange",()=>{if(document.hidden)stopWake();else{pollSuggestions();scheduleWake()}});
  window.addEventListener("zbrano-voice-preferences-loaded",()=>{if(wakeEnabled.checked){if(showWakeCompatibility())startWake()}else if(braveBrowser)showWakeCompatibility();else status("Wake listening is off. It works only while this page is open and microphone permission is granted.")});
  async function maintainPlaybackWake(){
    if(!wakeEnabled.checked||!wakeShadowEnabled.checked||!wakeLocalActivate.checked||document.hidden){stopWake();return}
    stopRecognition(wakeRecognition);wakeRecognition=null;stopWake(true);const ready=await startWakeFallback();if(ready&&(activeAudio||speechQueueRunning))status('Local "Hey ZBRANO" interruption ready during playback',"listening");
  }
  const voiceObserver=new MutationObserver(()=>{if(activeAudio||speechQueueRunning)maintainPlaybackWake();else if(!pendingSuggestion)scheduleWake()});voiceObserver.observe(document.getElementById("voice-state"),{childList:true,subtree:true});

  function startConversationFollowup(){
    if(wakeConversationWaitTimer)clearTimeout(wakeConversationWaitTimer);clearWakeConversationHealth();const expires=Date.now()+45000;
    const attempt=async()=>{
      if(!wakeConversationEnabled.checked||!wakeEnabled.checked||document.hidden)return;
      if(Date.now()>=expires){status("Conversation follow-up expired");scheduleWake();return}
      if(activeRequest||activeAudio||speechQueueRunning||mediaRecorder||pendingSuggestion){wakeConversationWaitTimer=setTimeout(attempt,300);return}
      const microphoneReady=await startWakeFallback();if(!microphoneReady||!wakeFallbackStream){status("Conversation microphone unavailable - retrying","error");wakeConversationWaitTimer=setTimeout(attempt,500);return}
      stopRecognition(wakeRecognition);wakeRecognition=null;wakeConversationListening=true;
      if(!startFallbackCommandWindow()){wakeConversationListening=false;stopWake();hideWakeOverlay();status("Conversation microphone capture did not arm - retrying","error");wakeConversationWaitTimer=setTimeout(attempt,500);return}
      const generation=wakeFallbackGeneration;
      const verifyCapture=()=>{
        if(generation!==wakeFallbackGeneration||wakeFallbackMode!=="command"||!wakeConversationListening)return;
        if(wakeFallbackBusy||wakeFallbackFinalizing||wakeFallbackSpeechStart){wakeConversationHealthTimer=setTimeout(verifyCapture,350);return}
        if(wakeFallbackCaptureHealthy(true)){wakeConversationHealthTimer=setTimeout(verifyCapture,500);return}
        wakeConversationListening=false;hideWakeOverlay();status("Conversation microphone stopped responding - reconnecting","error");stopWake();wakeConversationWaitTimer=setTimeout(attempt,500);
      };
      wakeConversationHealthTimer=setTimeout(verifyCapture,650);showWakeOverlay("CONVERSATION MODE","Listening for your follow-up...");status("Conversation mode - listening for a follow-up","listening");
    };
    attempt();
  }
  window.addEventListener("zbrano-response-finished",()=>{if(!wakeConversationArmed)return;wakeConversationArmed=false;if(wakeConversationEnabled.checked)startConversationFollowup()});
  pollSuggestions();setInterval(pollSuggestions,5000);
  window.zbranoHandsFreeVoice={poll:pollSuggestions,startWake,stopWake};
})();
