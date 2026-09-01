(() => {
  const tab=document.getElementById("automations-tab");
  const panel=document.getElementById("automations-panel");
  if(!tab||!panel)return;
  const $=id=>document.getElementById(id);
  const esc=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"})[char]);
  let state={settings:{},automations:[],suggestions:[],timeline:[],entity_memory:[],area_context:{areas:[],entities:[]},patterns:[],discoveries:[],engine:{}};
  let entityMap=new Map();
  let notificationState={channels:[]};
  let selectedStudioNode="trigger";
  let selectedFlowCard={kind:"trigger",index:0};
  let workflowDraft={triggers:[],trigger_mode:"any",conditions:[],condition_mode:"all",actions:[],branches:[]};
  let draggedStudioNode="";
  let draggedFlowCard=null;
  let editorHistory=[],editorHistoryIndex=-1,editorHistoryTimer=0,restoringEditorHistory=false;
  let editorHistoryBaseline="";
  const localDraftKey="zbrano.automation-studio.unsaved.v1",localDraftMaxAge=7*24*60*60*1000,localDraftMaxBytes=100000;
  const libraryPrefsKey="zbrano.automation-studio.library.v1";
  const entityPickerFieldIds=new Set(["automation-trigger-entity"]);
  const studioPanels={
    details:{title:"Automation",help:"Name the behavior and decide whether live evaluation starts after saving.",fields:[["automation-name","Name"],["automation-objective","Objective"],["automation-enabled","Enable after saving"]]},
    trigger:{title:"Trigger",help:"Start from an entity event, local time, sunrise or sunset, repeating interval, or one-time schedule.",fields:[["automation-trigger-kind","Trigger type"],["automation-trigger-entity","Trigger entity"],["automation-trigger-operator","Condition"],["automation-trigger-value","Value"],["automation-trigger-for","Sustain for seconds"],["automation-trigger-at","Local time"],["automation-trigger-weekdays","Selected weekdays"],["automation-trigger-sun-event","Sun event"],["automation-trigger-sun-offset","Sun offset minutes"],["automation-trigger-interval","Repeat every minutes"],["automation-trigger-one-time","One-time local date and time"]]},
    context:{title:"Context",help:"Add presence and supporting evidence before ZBRANO proposes anything.",fields:[["automation-presence","Presence entity"],["automation-signals","Signal entities"],["automation-context-notes","Context strategy"]]},
    decision:{title:"Decision",help:"Choose this automation's operating mode, response window, episode sensitivity, and delivery. Zero uses ZBRANO's safe automatic margin.",fields:[["automation-proposal","Suggestion wording"],["automation-confidence","Minimum confidence"],["automation-cooldown","Cooldown minutes"],["automation-suggestion-timeout","Suggestion response window"],["automation-reoffer-delta","Reconsider after worsening by"],["automation-reset-delta","Reset margin"],["automation-risk","Risk class"],["automation-execution-policy","Operating mode"],["automation-delivery-voice","Speak suggestions"],["automation-delivery-center","Show in Studio inbox"],["automation-delivery-push","Send Home Assistant notification"]]},
    action:{title:"Action",help:"Choose the Home Assistant service and bounded failure circuit used under existing authority limits.",fields:[["automation-action-entity","Action entity"],["automation-action-service","HA service"],["automation-action-data","Service data"],["automation-max-actions","Maximum actions per hour"],["automation-failure-limit","Failure limit"],["automation-failure-window","Failure window minutes"],["automation-notify-action","Notify after action"],["automation-reversible-only","Require reversible actions"]]},
  };

  async function api(path,options={}){
    const response=await fetch(path,{cache:"no-store",...options});
    const data=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error(data.detail||`HTTP ${response.status}`);
    return data;
  }

  function activate(){
    for(const id of ["chat-panel","entities-panel","settings-panel","plugins-panel","files-panel","calendar-panel","developer-panel","automations-panel"]){document.getElementById(id)?.classList.toggle("hidden",id!=="automations-panel")}
    for(const id of ["chat-tab","entities-tab","settings-tab","plugins-tab","files-tab","calendar-tab","developer-tab","automations-tab"]){document.getElementById(id)?.classList.toggle("active",id==="automations-tab")}
  }

  function showView(name){
    for(const button of panel.querySelectorAll("[data-auto-view]")){const active=button.dataset.autoView===name;button.classList.toggle("active",active);button.setAttribute("aria-selected",String(active))}
    for(const view of panel.querySelectorAll("[data-auto-panel]")){view.classList.toggle("hidden",view.dataset.autoPanel!==name)}
    panel.classList.toggle("studio-active",name==="studio");
  }

  function readLibraryPrefs(){
    try{const value=JSON.parse(localStorage.getItem(libraryPrefsKey)||"{}");return {view:["create","saved"].includes(value.view)?value.view:"create",filter:["all","active","attention","disabled","autonomous","watch"].includes(value.filter)?value.filter:"all",sort:["recent","name_asc","name_desc","active","attention"].includes(value.sort)?value.sort:"recent",layout:["detailed","compact"].includes(value.layout)?value.layout:"detailed"}}catch(_error){return {view:"create",filter:"all",sort:"recent",layout:"detailed"}}
  }
  function persistLibraryPrefs(){
    try{const active=panel.querySelector('[data-automation-library-view].active')?.dataset.automationLibraryView||"create";localStorage.setItem(libraryPrefsKey,JSON.stringify({view:active,filter:$("automation-library-filter").value,sort:$("automation-library-sort").value,layout:$("automation-library-layout").value}))}catch(_error){}
  }
  function showLibraryView(name,persist=true){
    for(const button of panel.querySelectorAll("[data-automation-library-view]")){const active=button.dataset.automationLibraryView===name;button.classList.toggle("active",active);button.setAttribute("aria-selected",String(active))}
    for(const view of panel.querySelectorAll("[data-automation-library-panel]")){view.classList.toggle("hidden",view.dataset.automationLibraryPanel!==name)}
    if(persist)persistLibraryPrefs();
  }

  function openOverviewShortcut(target){
    let destination=null;
    if(target==="drafts"){
      showView("studio");showLibraryView("saved");
      $("automation-library-search").value="";$("automation-library-filter").value="disabled";
      persistLibraryPrefs();renderLibrary();destination=$("automation-library-filter");
    }else if(target==="suggestions"){
      showView("overview");destination=$("autonomy-suggestion-inbox");
    }
    if(destination)requestAnimationFrame(()=>{destination.scrollIntoView({behavior:"smooth",block:"center"});destination.focus({preventScroll:true})});
  }

  function modeLabel(value){return ({observe_only:"Observe only",suggest_only:"Suggest only",approval_gated:"Approval-gated",selective_autonomy:"Selective autonomy"})[value]||"Suggest only"}
  function authorityLabel(value){return ({inherit:"Use global default",observe:"Observe only",suggest:"Suggest only",approval_required:"Ask for approval",autonomous:"Automatic"})[value]||"Use global default"}
  function entityLabel(id){const entity=entityMap.get(id);return entity?.friendly_name||id}
  function flowElement(item){return window.zbranoAutomationFlow?.create(item,entityLabel)||null}
  function cloneEditorValue(value){return JSON.parse(JSON.stringify(value))}
  function editorHistoryState(){
    const controls={};
    for(const control of $("automation-draft-form").querySelectorAll("input[id],select[id],textarea[id]"))controls[control.id]=control.type==="checkbox"?control.checked:control.value;
    return {controls,workflowDraft:cloneEditorValue(workflowDraft),selectedStudioNode};
  }
  function updateEditorHistoryControls(){
    $("automation-studio-undo").disabled=editorHistoryIndex<=0;
    $("automation-studio-redo").disabled=editorHistoryIndex<0||editorHistoryIndex>=editorHistory.length-1;
  }
  function editorHasUnsavedChanges(){return Boolean(editorHistoryBaseline)&&JSON.stringify(editorHistoryState())!==editorHistoryBaseline}
  function updateEditorDirtyState(){$("automation-studio-dirty").hidden=!editorHasUnsavedChanges()}
  function confirmEditorReplacement(action){commitEditorHistory();return !editorHasUnsavedChanges()||confirm(`Discard unsaved automation changes and ${action}?`)}
  function markEditorAsUnsaved(){editorHistoryBaseline="__unsaved__";const current=editorHistoryState();persistLocalEditorDraft(current);updateEditorDirtyState()}
  function removeLocalEditorDraft(){try{localStorage.removeItem(localDraftKey)}catch(_error){}}
  function persistLocalEditorDraft(state,serialized=JSON.stringify(state)){
    if(serialized===editorHistoryBaseline){removeLocalEditorDraft();return}
    const payload=JSON.stringify({schema:1,saved_at:Date.now(),state});
    if(payload.length>localDraftMaxBytes)return;
    try{localStorage.setItem(localDraftKey,payload)}catch(_error){}
  }
  function readLocalEditorDraft(){
    try{
      const raw=localStorage.getItem(localDraftKey);if(!raw)return null;if(raw.length>localDraftMaxBytes){removeLocalEditorDraft();return null}
      const payload=JSON.parse(raw);
      if(!payload||payload.schema!==1||!payload.state||Date.now()-Number(payload.saved_at||0)>localDraftMaxAge){removeLocalEditorDraft();return null}
      return payload;
    }catch(_error){removeLocalEditorDraft();return null}
  }
  function applyEditorHistoryState(snapshot){
    for(const [id,value] of Object.entries(snapshot.controls||{})){const control=$(id);if(!control)continue;if(control.type==="checkbox")control.checked=Boolean(value);else control.value=String(value??"")}
    workflowDraft=cloneEditorValue(snapshot.workflowDraft||{triggers:[],trigger_mode:"any",conditions:[],condition_mode:"all",actions:[],branches:[]});workflowDraft.trigger_mode=workflowDraft.trigger_mode==="all"?"all":"any";selectedStudioNode=studioPanels[snapshot.selectedStudioNode]?snapshot.selectedStudioNode:"trigger";
    renderEditorFlow();renderStudioInspector();
  }
  function commitEditorHistory(){
    if(restoringEditorHistory)return;
    clearTimeout(editorHistoryTimer);editorHistoryTimer=0;
    const next=editorHistoryState(),serialized=JSON.stringify(next),current=editorHistory[editorHistoryIndex];
    if(current&&JSON.stringify(current)===serialized)return;
    editorHistory=editorHistory.slice(0,editorHistoryIndex+1);editorHistory.push(next);
    if(editorHistory.length>50)editorHistory.shift();
    editorHistoryIndex=editorHistory.length-1;updateEditorHistoryControls();persistLocalEditorDraft(next,serialized);updateEditorDirtyState();
  }
  function scheduleEditorHistory(){
    if(restoringEditorHistory)return;
    clearTimeout(editorHistoryTimer);editorHistoryTimer=setTimeout(commitEditorHistory,220);
  }
  function resetEditorHistory(){clearTimeout(editorHistoryTimer);editorHistoryTimer=0;editorHistory=[];editorHistoryIndex=-1;commitEditorHistory();editorHistoryBaseline=JSON.stringify(editorHistory[0]);removeLocalEditorDraft();updateEditorDirtyState()}
  function restoreEditorHistory(index){
    if(index<0||index>=editorHistory.length||index===editorHistoryIndex)return;
    clearTimeout(editorHistoryTimer);editorHistoryTimer=0;restoringEditorHistory=true;
    const snapshot=editorHistory[index];applyEditorHistoryState(snapshot);editorHistoryIndex=index;
    restoringEditorHistory=false;updateEditorHistoryControls();persistLocalEditorDraft(snapshot);updateEditorDirtyState();
    $("automation-studio-state").textContent=index<editorHistory.length-1?"Edit undone.":"Edit restored.";
  }
  function undoEditor(){commitEditorHistory();restoreEditorHistory(editorHistoryIndex-1)}
  function redoEditor(){restoreEditorHistory(editorHistoryIndex+1)}
  function recoverLocalEditorDraft(payload){
    restoringEditorHistory=true;applyEditorHistoryState(payload.state);restoringEditorHistory=false;commitEditorHistory();
    const saved=new Date(Number(payload.saved_at||0));$("automation-studio-state").textContent=`Recovered unsaved flow from ${saved.toLocaleString()}. New flow discards it.`;
  }
  function renderStudioInspector(){
    window.zbranoEntitySearch?.close();
    const panelConfig=studioPanels[selectedStudioNode]||studioPanels.trigger;
    $("automation-studio-inspector-title").textContent=panelConfig.title;
    $("automation-studio-inspector-help").textContent=panelConfig.help;
    const root=$("automation-studio-inspector-fields");root.replaceChildren();
    if(selectedStudioNode==="action")renderActionTaskPalette(root);
    for(const [id,labelText] of panelConfig.fields){
      const source=$(id);if(!source)continue;
      const label=document.createElement("label"),control=source.cloneNode(true);
      control.id=`studio-${id}`;control.removeAttribute("required");
      if(entityPickerFieldIds.has(id))control.dataset.entityPicker="true";
      if(source.type==="checkbox"){control.checked=source.checked;label.className="is-check";label.append(control,document.createTextNode(labelText))}
      else{control.value=source.value;const caption=document.createElement("span");caption.textContent=labelText;label.append(caption,control)}
      const synchronize=()=>{if(source.type==="checkbox")source.checked=control.checked;else source.value=control.value;source.dispatchEvent(new Event("input",{bubbles:true}))};
      control.addEventListener("input",synchronize);control.addEventListener("change",synchronize);root.append(label);
    }
    renderWorkflowInspector(root);
    for(const input of root.querySelectorAll('input[data-entity-picker="true"]'))window.zbranoEntitySearch?.attach(input);
  }

  function workflowOperatorOptions(selected,trigger=false){return (trigger?["any_change","changes_to","equals","not_equals","above","below"]:["equals","not_equals","above","below"]).map(value=>`<option value="${value}"${value===selected?" selected":""}>${value.replaceAll("_"," ")}</option>`).join("")}
  const weekdayNames=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
  function parseWeekdays(value){return [...new Set(String(value||"").split(/[,\s]+/).map(part=>weekdayNames.findIndex(day=>day.toLowerCase()===part.slice(0,3).toLowerCase())).filter(index=>index>=0))]}
  function formatWeekdays(values){return (values||[]).map(value=>weekdayNames[Number(value)]).filter(Boolean).join(", ")}
  function triggerStepHtml(item,attributes){const kind=item.kind||"entity",attr=field=>`${attributes} data-trigger-field="${field}"`;return `<select ${attr("kind")}><option value="entity"${kind==="entity"?" selected":""}>Entity state</option><option value="time"${kind==="time"?" selected":""}>Specific time</option><option value="sun"${kind==="sun"?" selected":""}>Sunrise / sunset</option><option value="interval"${kind==="interval"?" selected":""}>Interval</option><option value="one_time"${kind==="one_time"?" selected":""}>One time</option></select>${kind==="entity"?`<input ${attr("entity_id")} list="automation-entity-options" value="${esc(item.entity_id||"")}" placeholder="sensor.entity"><select ${attr("operator")}>${workflowOperatorOptions(item.operator,true)}</select><input ${attr("value")} value="${esc(item.value||"")}" placeholder="value"><input ${attr("for_seconds")} type="number" min="0" max="86400" value="${Number(item.for_seconds||0)}">`:kind==="time"?`<input ${attr("at")} type="time" value="${esc(item.at||"")}"><input ${attr("weekdays")} value="${esc(formatWeekdays(item.weekdays))}" placeholder="Mon, Tue">`:kind==="sun"?`<select ${attr("sun_event")}><option value="sunrise"${item.sun_event!=="sunset"?" selected":""}>Sunrise</option><option value="sunset"${item.sun_event==="sunset"?" selected":""}>Sunset</option></select><input ${attr("offset_minutes")} type="number" min="-180" max="180" value="${Number(item.offset_minutes||0)}"><input ${attr("weekdays")} value="${esc(formatWeekdays(item.weekdays))}" placeholder="Mon, Tue">`:kind==="interval"?`<input ${attr("interval_minutes")} type="number" min="1" max="10080" value="${Number(item.interval_minutes||5)}">`:`<input ${attr("one_time_at")} type="datetime-local" value="${esc(item.one_time_at||"")}">`}`}
  function conditionStepHtml(item,attributes){const kind=item.kind||"entity",attr=field=>`${attributes} data-condition-field="${field}"`;return `<select ${attr("kind")}><option value="entity"${kind==="entity"?" selected":""}>Entity state</option><option value="time_window"${kind==="time_window"?" selected":""}>Time window</option><option value="weekday"${kind==="weekday"?" selected":""}>Weekdays</option><option value="sun"${kind==="sun"?" selected":""}>Sun state</option></select>${kind==="entity"?`<input ${attr("entity_id")} list="automation-entity-options" value="${esc(item.entity_id||"")}" placeholder="sensor.entity"><select ${attr("operator")}>${workflowOperatorOptions(item.operator)}</select><input ${attr("value")} value="${esc(item.value||"")}" placeholder="value"><input ${attr("for_seconds")} type="number" min="0" max="86400" value="${Number(item.for_seconds||0)}" aria-label="Condition duration seconds">`:kind==="time_window"?`<input ${attr("start_time")} type="time" value="${esc(item.start_time||"")}"><input ${attr("end_time")} type="time" value="${esc(item.end_time||"")}">`:kind==="weekday"?`<input ${attr("weekdays")} value="${esc(formatWeekdays(item.weekdays))}" placeholder="Mon, Tue, Wed">`:`<select ${attr("sun_state")}><option value="below_horizon"${item.sun_state!=="above_horizon"?" selected":""}>After sunset</option><option value="above_horizon"${item.sun_state==="above_horizon"?" selected":""}>After sunrise</option></select>`}`}
  function actionTaskKey(item){const preferred=String(item.task_template||"");if(["turn_on","turn_off","toggle","set_temperature","set_brightness","notification","delay","wait","service"].includes(preferred))return preferred;const kind=item.kind||"service",service=String(item.service||"");if(kind==="notification")return "notification";if(kind==="delay")return "delay";if(kind==="wait_state")return "wait";if(service==="climate.set_temperature")return "set_temperature";if(service==="light.turn_on"&&item.service_data?.brightness_pct!=null)return "set_brightness";if(service.endsWith(".turn_on"))return "turn_on";if(service.endsWith(".turn_off"))return "turn_off";if(service.endsWith(".toggle"))return "toggle";return "service"}
  function newActionTask(template="service"){
    const base={kind:"service",entity_id:"",service:"",service_data:{},delay_seconds:0,wait_operator:"equals",wait_value:"",timeout_seconds:30,notification_title:"ZBRANO automation",notification_message:"",notification_severity:"suggestion",task_template:template};
    if(template==="notification")return {...base,kind:"notification",entity_id:notificationState.channels.find(item=>item.available!==false)?.entity_id||""};
    if(template==="delay")return {...base,kind:"delay",delay_seconds:5};
    if(template==="wait")return {...base,kind:"wait_state"};
    if(template==="set_temperature")return {...base,service:"climate.set_temperature",service_data:{temperature:22}};
    if(template==="set_brightness")return {...base,service:"light.turn_on",service_data:{brightness_pct:70}};
    return base;
  }
  function renderActionTaskPalette(root){
    const section=document.createElement("section");section.className="automation-task-palette";
    const notificationReady=(notificationState.channels||[]).some(item=>item.available!==false);
    const hasDomain=domain=>[...entityMap.values()].some(item=>(item.domain||String(item.entity_id||"").split(".",1)[0])===domain&&item.available!==false);
    const templates=[
      ["turn_on","Power on","Turn on a device","âš¡"],["turn_off","Power off","Turn off a device","â—‹"],["toggle","Toggle","Change current power state","â‡„"],
      ["notification","Notification",notificationReady?"Send through Home Assistant":"No notify channel connected","âœ‰",!notificationReady],
      ["delay","Delay","Pause before the next task","â±"],["wait","Wait until","Continue after a state matches","â—·"],["service","Custom service","Advanced Home Assistant action","âš™"],
    ];
    templates.splice(3,0,["set_temperature","Set temperature",hasDomain("climate")?"Choose a thermostat and target":"No climate entity available","&#8451;",!hasDomain("climate")],["set_brightness","Set brightness",hasDomain("light")?"Choose a light and brightness":"No light entity available","&#9728;",!hasDomain("light")]);
    const iconCodes={turn_on:"&#9889;",turn_off:"&#9675;",toggle:"&#8644;",set_temperature:"&#8451;",set_brightness:"&#9728;",notification:"&#9993;",delay:"&#9201;",wait:"&#9655;",service:"&#9881;"};
    section.innerHTML=`<div class="automation-task-palette-head"><strong>Add a task</strong><small>Choose a ready-made building block</small></div><div class="automation-task-palette-grid">${templates.map(([key,title,detail,_icon,disabled])=>`<button type="button" data-action-template="${key}"${disabled?' disabled aria-disabled="true"':""}><span aria-hidden="true">${iconCodes[key]}</span><strong>${title}</strong><small>${detail}</small></button>`).join("")}</div>`;
    section.addEventListener("click",event=>{const button=event.target.closest("[data-action-template]");if(!button||button.disabled)return;if(workflowDraft.actions.length>=19){$("automation-studio-state").textContent="A flow supports up to 20 actions including the primary action.";return}workflowDraft.actions.push(newActionTask(button.dataset.actionTemplate));renderStudioInspector();renderEditorFlow();commitEditorHistory();$("automation-studio-state").textContent=`${button.querySelector("strong").textContent} task added. Complete its settings.`});
    root.append(section);
  }
  function actionStepValid(item){const kind=item.kind||"service";return kind==="delay"?Number(item.delay_seconds)>0:kind==="wait_state"?Boolean(item.entity_id):kind==="notification"?Boolean(item.entity_id&&item.notification_message):Boolean(item.entity_id&&item.service)}
  function actionStepHtml(item,attributes){
    const kind=item.kind||"service",template=actionTaskKey(item),attr=field=>`${attributes} data-action-field="${field}"`;
    const labels={turn_on:"Power on",turn_off:"Power off",toggle:"Toggle",set_temperature:"Set temperature",set_brightness:"Set brightness",notification:"Notification",delay:"Delay",wait:"Wait until",service:"Custom service"};
    const type=template!=="service"?`<span class="automation-task-kind">${labels[template]}</span>`:`<select ${attr("kind")}><option value="service"${kind==="service"?" selected":""}>Service action</option><option value="notification"${kind==="notification"?" selected":""}>Notification</option><option value="delay"${kind==="delay"?" selected":""}>Delay</option><option value="wait_state"${kind==="wait_state"?" selected":""}>Wait until</option></select>`;
    if(kind==="delay")return `${type}<input ${attr("delay_seconds")} type="number" min="1" max="300" value="${Number(item.delay_seconds||1)}" aria-label="Delay seconds" placeholder="Seconds">`;
    if(kind==="wait_state")return `${type}<input ${attr("entity_id")} list="automation-entity-options" value="${esc(item.entity_id||"")}" placeholder="sensor.entity"><select ${attr("wait_operator")}>${workflowOperatorOptions(item.wait_operator)}</select><input ${attr("wait_value")} value="${esc(item.wait_value||"")}" placeholder="target value"><input ${attr("timeout_seconds")} type="number" min="1" max="300" value="${Number(item.timeout_seconds||30)}" aria-label="Timeout seconds">`;
    if(kind==="notification"){
      const channels=[...(notificationState.channels||[])];if(item.entity_id&&!channels.some(channel=>channel.entity_id===item.entity_id))channels.unshift({entity_id:item.entity_id,friendly_name:item.entity_id,available:false});
      return `${type}<select ${attr("entity_id")} aria-label="Notification channel"><option value="">Choose notification channel</option>${channels.map(channel=>`<option value="${esc(channel.entity_id)}"${channel.entity_id===item.entity_id?" selected":""}>${esc(channel.friendly_name||channel.entity_id)}${channel.available===false?" (unavailable)":""}</option>`).join("")}</select><input ${attr("notification_title")} value="${esc(item.notification_title||"ZBRANO automation")}" placeholder="Notification title"><textarea ${attr("notification_message")} maxlength="1000" placeholder="Message to send">${esc(item.notification_message||"")}</textarea><select ${attr("notification_severity")}><option value="information"${item.notification_severity==="information"?" selected":""}>Information</option><option value="suggestion"${item.notification_severity!=="information"&&item.notification_severity!=="warning"&&item.notification_severity!=="critical"?" selected":""}>Suggestion</option><option value="warning"${item.notification_severity==="warning"?" selected":""}>Warning</option><option value="critical"${item.notification_severity==="critical"?" selected":""}>Critical</option></select>`;
    }
    if(template==="set_temperature")return `${type}<input ${attr("entity_id")} list="automation-entity-options" value="${esc(item.entity_id||"")}" placeholder="climate.thermostat"><label>Target temperature<input ${attributes} data-action-data-field="temperature" type="number" min="5" max="35" step="0.5" value="${Number(item.service_data?.temperature??22)}"></label><small class="automation-task-derived">Service: climate.set_temperature</small>`;
    if(template==="set_brightness")return `${type}<input ${attr("entity_id")} list="automation-entity-options" value="${esc(item.entity_id||"")}" placeholder="light.room"><label>Brightness %<input ${attributes} data-action-data-field="brightness_pct" type="number" min="1" max="100" value="${Number(item.service_data?.brightness_pct??70)}"></label><small class="automation-task-derived">Service: light.turn_on</small>`;
    if(["turn_on","turn_off","toggle"].includes(template))return `${type}<input ${attr("entity_id")} list="automation-entity-options" value="${esc(item.entity_id||"")}" placeholder="Choose a device entity"><small class="automation-task-derived">Service: ${esc(item.service||`device.${template}`)}</small><input ${attr("delay_seconds")} type="number" min="0" max="300" value="${Number(item.delay_seconds||0)}" aria-label="Delay before action" placeholder="Delay before action">`;
    return `${type}<input ${attr("entity_id")} list="automation-entity-options" value="${esc(item.entity_id||"")}" placeholder="light.room"><input ${attr("service")} value="${esc(item.service||"")}" placeholder="light.turn_on"><input ${attr("delay_seconds")} type="number" min="0" max="300" value="${Number(item.delay_seconds||0)}" aria-label="Delay before action">`;
  }
  function renderWorkflowInspector(root){
    if(selectedStudioNode==="decision"){renderBranchInspector(root);return}
    const specs=selectedStudioNode==="trigger"?["triggers","Additional triggers"]:selectedStudioNode==="context"?["conditions","State conditions"]:selectedStudioNode==="action"?["actions","Following actions"]:null;
    if(!specs)return;
    const [collection,title]=specs,items=workflowDraft[collection];
    const section=document.createElement("section");section.className="automation-workflow-steps";
    const mode=collection==="triggers"?`<label>Trigger relationship<select data-trigger-mode><option value="any"${workflowDraft.trigger_mode!=="all"?" selected":""}>OR — any trigger</option><option value="all"${workflowDraft.trigger_mode==="all"?" selected":""}>AND — all trigger states</option></select></label>`:collection==="conditions"?`<label>Match conditions<select data-workflow-mode><option value="all"${workflowDraft.condition_mode==="all"?" selected":""}>All conditions</option><option value="any"${workflowDraft.condition_mode==="any"?" selected":""}>Any condition</option></select></label>`:"";
    const rows=items.map((item,index)=>{
      if(collection==="actions")return `<div class="automation-workflow-step">${actionStepHtml(item,`data-workflow-index="${index}"`)}<button type="button" data-workflow-remove="${index}">Remove</button></div>`;
      return `<div class="automation-workflow-step">${collection==="triggers"?triggerStepHtml(item,`data-workflow-index="${index}"`):conditionStepHtml(item,`data-workflow-index="${index}"`)}<button type="button" data-workflow-remove="${index}">Remove</button></div>`;
    }).join("");
    section.innerHTML=`<div class="automation-workflow-head"><strong>${title}</strong><button type="button" data-workflow-add="${collection}">+ Add</button></div>${mode}${rows||'<small class="automation-workflow-empty">None added. The primary block above remains active.</small>'}`;root.append(section);
    section.addEventListener("input",event=>{const field=event.target.dataset.actionField||event.target.dataset.triggerField||event.target.dataset.conditionField,dataField=event.target.dataset.actionDataField,index=Number(event.target.dataset.workflowIndex);if((!field&&!dataField)||!items[index])return;if(dataField){items[index].service_data={...(items[index].service_data||{}),[dataField]:Number(event.target.value)}}else items[index][field]=field==="weekdays"?parseWeekdays(event.target.value):field.endsWith("seconds")||field.endsWith("minutes")?Number(event.target.value||0):event.target.value;if(collection==="actions"&&field==="entity_id"&&["turn_on","turn_off","toggle"].includes(items[index].task_template)){const domain=String(event.target.value||"").split(".",1)[0];items[index].service=domain?`${domain}.${items[index].task_template}`:""}if(field==="kind")renderStudioInspector();renderEditorFlow();scheduleEditorHistory()});
    section.addEventListener("change",event=>{if(event.target.hasAttribute("data-trigger-mode")){workflowDraft.trigger_mode=event.target.value;renderEditorFlow();scheduleEditorHistory()}else if(event.target.hasAttribute("data-workflow-mode")){workflowDraft.condition_mode=event.target.value;renderEditorFlow();scheduleEditorHistory()}});
    section.addEventListener("click",event=>{const add=event.target.closest("[data-workflow-add]"),remove=event.target.closest("[data-workflow-remove]");if(add){items.push(collection==="actions"?newActionTask():collection==="triggers"?{kind:"entity",entity_id:"",operator:"changes_to",value:"",for_seconds:0,weekdays:[],at:"",sun_event:"sunrise",offset_minutes:0,interval_minutes:5,one_time_at:""}:{kind:"entity",entity_id:"",operator:"equals",value:"",weekdays:[],start_time:"",end_time:"",sun_state:"below_horizon"});renderStudioInspector();renderEditorFlow();commitEditorHistory()}else if(remove){items.splice(Number(remove.dataset.workflowRemove),1);renderStudioInspector();renderEditorFlow();commitEditorHistory()}});
  }

  function renderBranchInspector(root){
    const section=document.createElement("section");section.className="automation-workflow-steps automation-branch-editor";
    const cards=workflowDraft.branches.map((branch,branchIndex)=>{
      const conditions=(branch.conditions||[]).map((item,index)=>`<div class="automation-workflow-step">${conditionStepHtml(item,`data-branch-collection="conditions" data-branch-index="${branchIndex}" data-item-index="${index}"`)}<button type="button" data-branch-remove-item="conditions" data-branch-index="${branchIndex}" data-item-index="${index}">Remove</button></div>`).join("");
      const actions=(branch.actions||[]).map((item,index)=>`<div class="automation-workflow-step">${actionStepHtml(item,`data-branch-collection="actions" data-branch-index="${branchIndex}" data-item-index="${index}"`)}<button type="button" data-branch-remove-item="actions" data-branch-index="${branchIndex}" data-item-index="${index}">Remove</button></div>`).join("");
      return `<article class="automation-branch-card"><div class="automation-workflow-head"><input data-branch-name="${branchIndex}" value="${esc(branch.name||`Branch ${branchIndex+1}`)}" aria-label="Branch name"><button type="button" data-branch-remove="${branchIndex}">Remove branch</button></div><label>Condition logic<select data-branch-mode="${branchIndex}"><option value="all"${branch.condition_mode!=="any"?" selected":""}>All conditions</option><option value="any"${branch.condition_mode==="any"?" selected":""}>Any condition</option></select></label><small>Conditions are checked top to bottom. Leave this list empty to make an ELSE fallback.</small>${conditions}<button type="button" data-branch-add-item="conditions" data-branch-index="${branchIndex}">+ Condition</button><strong>Branch actions</strong>${actions}<button type="button" data-branch-add-item="actions" data-branch-index="${branchIndex}">+ Action</button></article>`;
    }).join("");
    section.innerHTML=`<div class="automation-workflow-head"><strong>Choose branches</strong><button type="button" data-branch-add>+ Branch</button></div><small>The first matching branch runs. Put an empty-condition ELSE branch last.</small>${cards||'<small class="automation-workflow-empty">No branches. The linear action path remains active.</small>'}`;root.append(section);
    section.addEventListener("input",event=>{const branchIndex=Number(event.target.dataset.branchIndex),branch=workflowDraft.branches[branchIndex];if(event.target.hasAttribute("data-branch-name")){workflowDraft.branches[Number(event.target.dataset.branchName)].name=event.target.value;renderEditorFlow();scheduleEditorHistory();return}const collection=event.target.dataset.branchCollection,itemIndex=Number(event.target.dataset.itemIndex),field=event.target.dataset.actionField||event.target.dataset.conditionField,dataField=event.target.dataset.actionDataField;if(!branch||!collection||(!field&&!dataField))return;const item=branch[collection][itemIndex];if(dataField)item.service_data={...(item.service_data||{}),[dataField]:Number(event.target.value)};else item[field]=field==="weekdays"?parseWeekdays(event.target.value):field.endsWith("seconds")||field.endsWith("minutes")?Number(event.target.value||0):event.target.value;if(field==="kind")renderStudioInspector();renderEditorFlow();scheduleEditorHistory()});
    section.addEventListener("change",event=>{if(event.target.hasAttribute("data-branch-mode")){workflowDraft.branches[Number(event.target.dataset.branchMode)].condition_mode=event.target.value;renderEditorFlow();scheduleEditorHistory()}});
    section.addEventListener("click",event=>{const add=event.target.closest("[data-branch-add]"),remove=event.target.closest("[data-branch-remove]"),addItem=event.target.closest("[data-branch-add-item]"),removeItem=event.target.closest("[data-branch-remove-item]");if(add){workflowDraft.branches.push({name:`Branch ${workflowDraft.branches.length+1}`,condition_mode:"all",conditions:[],actions:[]})}else if(remove){workflowDraft.branches.splice(Number(remove.dataset.branchRemove),1)}else if(addItem){const branch=workflowDraft.branches[Number(addItem.dataset.branchIndex)],collection=addItem.dataset.branchAddItem;branch[collection].push(collection==="actions"?{kind:"service",entity_id:"",service:"",service_data:{},delay_seconds:0,wait_operator:"equals",wait_value:"",timeout_seconds:30}:{kind:"entity",entity_id:"",operator:"equals",value:"",weekdays:[],start_time:"",end_time:"",sun_state:"below_horizon"})}else if(removeItem){workflowDraft.branches[Number(removeItem.dataset.branchIndex)][removeItem.dataset.branchRemoveItem].splice(Number(removeItem.dataset.itemIndex),1)}else return;renderStudioInspector();renderEditorFlow();commitEditorHistory()});
  }

  function selectStudioNode(kind,index=null,branchIndex=null){
    const inspectorKind=["branch-action","branch-condition"].includes(kind)?"decision":kind;if(!studioPanels[inspectorKind])return;
    selectedStudioNode=inspectorKind;if(Number.isInteger(index))selectedFlowCard={kind,index,branchIndex:Number.isInteger(branchIndex)?branchIndex:null};else if(selectedFlowCard.kind!==kind)selectedFlowCard={kind,index:0,branchIndex:null};renderEditorFlow();renderStudioInspector();
    if(Number.isInteger(index))requestAnimationFrame(()=>focusSelectedFlowEditor(kind,index,branchIndex));
  }
  function focusSelectedFlowEditor(kind,index,branchIndex=null){
    const root=$("automation-studio-inspector-fields");if(!root)return;
    let target=null;
    if(kind==="trigger")target=index===0?$("studio-automation-trigger-entity"):root.querySelector(`[data-workflow-index="${index-1}"]`);
    else if(kind==="context"){const hasPresence=Boolean($("automation-presence").value.trim()),signalCount=$("automation-signals").value.split(/[,\n]/).map(value=>value.trim()).filter(Boolean).length,offset=(hasPresence?1:0)+signalCount;if(hasPresence&&index===0)target=$("studio-automation-presence");else if(index<offset)target=$("studio-automation-signals");else target=root.querySelector(`[data-workflow-index="${index-offset}"]`)}
    else if(kind==="action"){const primary=Boolean($("automation-action-entity").value.trim()||$("automation-action-service").value.trim());target=primary&&index===0?$("studio-automation-action-entity"):root.querySelector(`[data-workflow-index="${index-(primary?1:0)}"]`)}
    else if(kind==="decision")target=root.querySelector(`[data-branch-name="${index}"]`);
    else if(kind==="branch-action")target=root.querySelector(`[data-branch-collection="actions"][data-branch-index="${branchIndex}"][data-item-index="${index}"]`);
    else if(kind==="branch-condition")target=root.querySelector(`[data-branch-collection="conditions"][data-branch-index="${branchIndex}"][data-item-index="${index}"]`);
    if(target){target.closest(".automation-workflow-step,.automation-branch-card")?.scrollIntoView({behavior:"smooth",block:"nearest"});target.focus({preventScroll:true})}
  }
  function clearPrimaryTrigger(){
    $("automation-trigger-kind").value="entity";$("automation-trigger-entity").value="";$("automation-trigger-operator").value="changes_to";$("automation-trigger-value").value="";$("automation-trigger-for").value="0";$("automation-trigger-at").value="";$("automation-trigger-weekdays").value="";$("automation-trigger-sun-event").value="sunrise";$("automation-trigger-sun-offset").value="0";$("automation-trigger-interval").value="5";$("automation-trigger-one-time").value="";
  }
  function primaryTriggerValue(){return {kind:$("automation-trigger-kind").value,entity_id:$("automation-trigger-entity").value.trim(),operator:$("automation-trigger-operator").value,value:$("automation-trigger-value").value.trim(),for_seconds:Number($("automation-trigger-for").value||0),at:$("automation-trigger-at").value,weekdays:parseWeekdays($("automation-trigger-weekdays").value),sun_event:$("automation-trigger-sun-event").value,offset_minutes:Number($("automation-trigger-sun-offset").value||0),interval_minutes:Number($("automation-trigger-interval").value||5),one_time_at:$("automation-trigger-one-time").value}}
  function writePrimaryTrigger(item={}){$("automation-trigger-kind").value=item.kind||"entity";$("automation-trigger-entity").value=item.entity_id||"";$("automation-trigger-operator").value=item.operator||"changes_to";$("automation-trigger-value").value=item.value||"";$("automation-trigger-for").value=String(item.for_seconds||0);$("automation-trigger-at").value=item.at||"";$("automation-trigger-weekdays").value=formatWeekdays(item.weekdays);$("automation-trigger-sun-event").value=item.sun_event||"sunrise";$("automation-trigger-sun-offset").value=String(item.offset_minutes||0);$("automation-trigger-interval").value=String(item.interval_minutes||5);$("automation-trigger-one-time").value=item.one_time_at||""}
  function primaryActionValue(){let serviceData={};try{serviceData=JSON.parse($("automation-action-data").value||"{}")||{}}catch(_error){}return {kind:"service",entity_id:$("automation-action-entity").value.trim(),service:$("automation-action-service").value.trim(),service_data:serviceData,delay_seconds:0,wait_operator:"equals",wait_value:"",timeout_seconds:30}}
  function clearPrimaryAction(){$("automation-action-entity").value="";$("automation-action-service").value="";$("automation-action-data").value="{}"}
  function visualFlowItems(kind){
    if(kind==="trigger")return [primaryTriggerValue(),...cloneEditorValue(workflowDraft.triggers)];
    if(kind==="decision")return cloneEditorValue(workflowDraft.branches);
    if(kind==="action"){const primary=primaryActionValue();return [...(primary.entity_id||primary.service?[primary]:[]),...cloneEditorValue(workflowDraft.actions)]}
    return [];
  }
  function writeFlowSequence(kind,items){
    const next=cloneEditorValue(items);
    if(kind==="trigger"){writePrimaryTrigger(next.shift()||{});workflowDraft.triggers=next}
    else if(kind==="decision")workflowDraft.branches=next;
    else if(kind==="action"){
      const first=next[0],canBePrimary=(first?.kind||"service")==="service"&&(!first?.task_template||first.task_template==="service")&&Boolean(first?.entity_id||first?.service);
      if(canBePrimary){$("automation-action-entity").value=first.entity_id||"";$("automation-action-service").value=first.service||"";$("automation-action-data").value=JSON.stringify(first.service_data||{});next.shift()}else clearPrimaryAction();
      workflowDraft.actions=next;
    }
  }
  function contextFlowSource(index){
    const presence=$("automation-presence").value.trim(),signals=$("automation-signals").value.split(/[,\n]/).map(value=>value.trim()).filter(Boolean);
    if(presence&&index===0)return {type:"presence",item:presence,index:0,signals};
    const offset=presence?1:0,signalIndex=index-offset;
    if(signalIndex>=0&&signalIndex<signals.length)return {type:"signal",item:signals[signalIndex],index:signalIndex,signals};
    return {type:"condition",item:workflowDraft.conditions[signalIndex-signals.length],index:signalIndex-signals.length,signals};
  }
  function deleteFlowCard(kind,index,branchIndex=null){
    if(kind==="decision")return deleteBranchPath(index);
    if(kind==="trigger"){if(index===0)clearPrimaryTrigger();else workflowDraft.triggers.splice(index-1,1)}
    else if(kind==="context"){
      const hasPresence=Boolean($("automation-presence").value.trim()),signals=$("automation-signals").value.split(/[,\n]/).map(value=>value.trim()).filter(Boolean);
      if(hasPresence&&index===0)$("automation-presence").value="";
      else{const signalIndex=index-(hasPresence?1:0);if(signalIndex<signals.length){signals.splice(signalIndex,1);$("automation-signals").value=signals.join(", ")}else workflowDraft.conditions.splice(signalIndex-signals.length,1)}
    }else if(kind==="branch-action"){const branch=workflowDraft.branches[branchIndex];if(!branch?.actions?.[index])return;branch.actions.splice(index,1)}
    else if(kind==="branch-condition"){const branch=workflowDraft.branches[branchIndex];if(!branch?.conditions?.[index])return;branch.conditions.splice(index,1)}
    else if(kind==="action"){
      const primary=Boolean($("automation-action-entity").value.trim()||$("automation-action-service").value.trim());
      if(primary&&index===0){$("automation-action-entity").value="";$("automation-action-service").value="";$("automation-action-data").value="{}"}else workflowDraft.actions.splice(index-(primary?1:0),1);
    }else return;
    selectedFlowCard={kind,index:Math.max(0,index-1),branchIndex};renderStudioInspector();renderEditorFlow();commitEditorHistory();$("automation-studio-state").textContent="Flow card removed. Use Undo to restore it.";
  }
  function duplicateFlowCard(kind,index,branchIndex=null){
    if(kind==="decision")return duplicateBranchPath(index);
    if(kind==="branch-action"){const actions=workflowDraft.branches[branchIndex]?.actions;if(!actions?.[index])return;if(actions.length>=20){$("automation-studio-state").textContent="This branch already has its maximum of 20 tasks.";return}actions.splice(index+1,0,cloneEditorValue(actions[index]));selectedFlowCard={kind,index:index+1,branchIndex};renderStudioInspector();renderEditorFlow();commitEditorHistory();$("automation-studio-state").textContent="Branch task duplicated. Use Undo to restore the previous flow.";return}
    if(kind==="branch-condition"){const conditions=workflowDraft.branches[branchIndex]?.conditions;if(!conditions?.[index])return;if(conditions.length>=20){$("automation-studio-state").textContent="This branch already has its maximum of 20 conditions.";return}conditions.splice(index+1,0,cloneEditorValue(conditions[index]));selectedFlowCard={kind,index:index+1,branchIndex};renderStudioInspector();renderEditorFlow();commitEditorHistory();$("automation-studio-state").textContent="Branch condition duplicated. Use Undo to restore the previous flow.";return}
    const limits={trigger:10,decision:10,action:20},items=kind==="context"?null:visualFlowItems(kind);
    if(items&&items.length>=limits[kind]){$("automation-studio-state").textContent=`This stage already has its maximum of ${limits[kind]} cards.`;return}
    if(kind==="context"){
      const source=contextFlowSource(index);
      if(source.type==="presence"){$("automation-studio-state").textContent="Presence is a unique context rule and cannot be duplicated.";return}
      if(source.type==="condition"&&workflowDraft.conditions.length>=20){$("automation-studio-state").textContent="This stage already has its maximum of 20 conditions.";return}
      if(source.type==="signal"){source.signals.splice(source.index+1,0,source.item);$("automation-signals").value=source.signals.join(", ")}
      else if(source.item)workflowDraft.conditions.splice(source.index+1,0,cloneEditorValue(source.item));else return;
    }else{const item=items[index];if(!item)return;items.splice(index+1,0,cloneEditorValue(item));writeFlowSequence(kind,items)}
    selectedFlowCard={kind,index:index+1};renderStudioInspector();renderEditorFlow();commitEditorHistory();$("automation-studio-state").textContent="Flow card duplicated. Use Undo to restore the previous flow.";
  }
  function moveFlowCard(kind,fromIndex,insertionIndex){
    if(kind==="decision")return moveBranchPathTo(fromIndex,insertionIndex>fromIndex?insertionIndex-1:insertionIndex);
    if(kind==="context"){
      const source=contextFlowSource(fromIndex),presence=$("automation-presence").value.trim()?1:0;
      if(source.type==="presence"){$("automation-studio-state").textContent="Presence stays first because it is the flow's unique occupancy gate.";return false}
      const items=source.type==="signal"?source.signals:workflowDraft.conditions,prefix=source.type==="signal"?presence:presence+source.signals.length;
      if(!source.item||insertionIndex<prefix||insertionIndex>prefix+items.length){$("automation-studio-state").textContent="Signals and conditions keep their own order so their meaning remains clear.";return false}
      const boundary=insertionIndex-prefix,moved=items.splice(source.index,1)[0],adjusted=boundary>source.index?boundary-1:boundary;items.splice(Math.max(0,Math.min(adjusted,items.length)),0,moved);if(source.type==="signal")$("automation-signals").value=items.join(", ");
    }else{
      const items=visualFlowItems(kind);if(fromIndex<0||fromIndex>=items.length)return false;const moved=items.splice(fromIndex,1)[0],adjusted=insertionIndex>fromIndex?insertionIndex-1:insertionIndex;items.splice(Math.max(0,Math.min(adjusted,items.length)),0,moved);writeFlowSequence(kind,items);
    }
    selectedFlowCard={kind,index:Math.max(0,insertionIndex-(insertionIndex>fromIndex?1:0))};renderStudioInspector();renderEditorFlow();commitEditorHistory();$("automation-studio-state").textContent="Flow card moved. Use Undo to restore the previous order.";return true;
  }
  function moveActionToBranch(source,target){
    const targetActions=workflowDraft.branches[target.branchIndex]?.actions,sameBranch=source.kind==="branch-action"&&source.branchIndex===target.branchIndex;if(!targetActions||targetActions.length>=20&&!sameBranch){$("automation-studio-state").textContent="That branch cannot accept another task.";return false}
    let item=null,insertion=target.index;
    if(source.kind==="action"){const items=visualFlowItems("action");if(!items[source.index]){$("automation-studio-state").textContent=`Unable to locate action card ${source.index+1} for this move.`;return false}item=items.splice(source.index,1)[0];writeFlowSequence("action",items)}
    else if(source.kind==="branch-action"){
      const sourceActions=workflowDraft.branches[source.branchIndex]?.actions;if(!sourceActions?.[source.index])return false;item=sourceActions.splice(source.index,1)[0];if(source.branchIndex===target.branchIndex&&insertion>source.index)insertion-=1;
    }else return false;
    targetActions.splice(Math.max(0,Math.min(insertion,targetActions.length)),0,item);selectedStudioNode="decision";selectedFlowCard={kind:"branch-action",index:Math.max(0,Math.min(insertion,targetActions.length-1)),branchIndex:target.branchIndex};renderStudioInspector();renderEditorFlow();commitEditorHistory();$("automation-studio-state").textContent="Task moved into the selected branch. Use Undo to restore the previous flow.";return true;
  }
  function moveBranchCondition(source,target){
    const targetConditions=workflowDraft.branches[target.branchIndex]?.conditions,sameBranch=source.branchIndex===target.branchIndex;if(!targetConditions||targetConditions.length>=20&&!sameBranch){$("automation-studio-state").textContent="That branch cannot accept another condition.";return false}
    const sourceConditions=workflowDraft.branches[source.branchIndex]?.conditions;if(!sourceConditions?.[source.index])return false;let insertion=target.index;const item=sourceConditions.splice(source.index,1)[0];if(sameBranch&&insertion>source.index)insertion-=1;
    targetConditions.splice(Math.max(0,Math.min(insertion,targetConditions.length)),0,item);selectedStudioNode="decision";selectedFlowCard={kind:"branch-condition",index:Math.max(0,Math.min(insertion,targetConditions.length-1)),branchIndex:target.branchIndex};renderStudioInspector();renderEditorFlow();commitEditorHistory();$("automation-studio-state").textContent="Condition moved into the selected branch. Use Undo to restore the previous flow.";return true;
  }
  function newBranchCondition(template="entity"){return {kind:["entity","time_window","weekday","sun"].includes(template)?template:"entity",entity_id:"",operator:"equals",value:"",for_seconds:0,weekdays:[],start_time:"",end_time:"",sun_state:"below_horizon"}}
  function addBranchCondition(branchIndex,insertionIndex,template="entity"){
    const conditions=workflowDraft.branches[branchIndex]?.conditions;if(!conditions)return false;if(conditions.length>=20){$("automation-studio-state").textContent="This branch already has its maximum of 20 conditions.";return false}const target=Math.max(0,Math.min(insertionIndex,conditions.length));conditions.splice(target,0,newBranchCondition(template));selectedStudioNode="decision";selectedFlowCard={kind:"branch-condition",index:target,branchIndex};renderStudioInspector();renderEditorFlow();commitEditorHistory();requestAnimationFrame(()=>focusSelectedFlowEditor("branch-condition",target,branchIndex));$("automation-studio-state").textContent=`${({entity:"Entity state",time_window:"Time window",weekday:"Weekdays",sun:"Sun state"})[template]||"IF"} condition added to the selected branch. Complete its settings before saving.`;return true;
  }
  function branchQuickInsertion(kind,branchIndex){return selectedFlowCard.kind===kind&&selectedFlowCard.branchIndex===branchIndex?selectedFlowCard.index+1:(kind==="branch-condition"?workflowDraft.branches[branchIndex]?.conditions?.length:workflowDraft.branches[branchIndex]?.actions?.length)||0}
  function addBranchActionTemplate(branchIndex,template,insertionIndex){
    const actions=workflowDraft.branches[branchIndex]?.actions;if(!actions)return false;if(actions.length>=20){$("automation-studio-state").textContent="This branch already has its maximum of 20 tasks.";return false}const target=Math.max(0,Math.min(insertionIndex,actions.length));actions.splice(target,0,newActionTask(template));selectedStudioNode="decision";selectedFlowCard={kind:"branch-action",index:target,branchIndex};renderStudioInspector();renderEditorFlow();commitEditorHistory();requestAnimationFrame(()=>focusSelectedFlowEditor("branch-action",target,branchIndex));$("automation-studio-state").textContent=`${({turn_on:"Power on",turn_off:"Power off",toggle:"Toggle",set_temperature:"Set temperature",set_brightness:"Set brightness",notification:"Notification",delay:"Delay",wait:"Wait until",service:"Custom service"})[template]||"Action"} task added to the selected branch. Complete its settings.`;return true;
  }
  function addBranchAction(branchIndex,insertionIndex){
    return addBranchActionTemplate(branchIndex,"service",insertionIndex)
  }
  function addBranchPath(){
    if(workflowDraft.branches.length>=10){$("automation-studio-state").textContent="A flow supports up to 10 decision paths.";return false}const fallbackIndex=workflowDraft.branches.findIndex((branch,index)=>index===workflowDraft.branches.length-1&&!(branch.conditions||[]).length),selectedAfter=selectedFlowCard.kind==="decision"?selectedFlowCard.index+1:workflowDraft.branches.length,target=Math.max(0,Math.min(fallbackIndex>=0?Math.min(selectedAfter,fallbackIndex):selectedAfter,workflowDraft.branches.length));workflowDraft.branches.splice(target,0,{name:`Path ${target+1}`,condition_mode:"all",conditions:[newBranchCondition()],actions:[]});selectedStudioNode="decision";selectedFlowCard={kind:"decision",index:target,branchIndex:null};renderStudioInspector();renderEditorFlow();commitEditorHistory();requestAnimationFrame(()=>focusSelectedFlowEditor("decision",target));$("automation-studio-state").textContent="Decision path added before the ELSE fallback. Complete its IF condition and tasks.";return true;
  }
  function moveBranchPathTo(fromIndex,targetIndex){
    const branches=workflowDraft.branches;if(!branches[fromIndex])return false;const fallbackIndex=branches.length&&!(branches.at(-1)?.conditions||[]).length?branches.length-1:-1;if(fromIndex===fallbackIndex){$("automation-studio-state").textContent="The ELSE fallback stays last so path evaluation remains safe.";return false}const maxTarget=fallbackIndex>=0?fallbackIndex-1:branches.length-1,target=Math.max(0,Math.min(Number(targetIndex),maxTarget));if(target===fromIndex)return false;const moved=branches.splice(fromIndex,1)[0];branches.splice(target,0,moved);selectedStudioNode="decision";selectedFlowCard={kind:"decision",index:target,branchIndex:null};renderStudioInspector();renderEditorFlow();commitEditorHistory();requestAnimationFrame(()=>focusSelectedFlowEditor("decision",target));$("automation-studio-state").textContent="Decision path moved. The ELSE fallback remains last. Use Undo to restore the previous order.";return true;
  }
  function duplicateBranchPath(index){
    const branches=workflowDraft.branches,source=branches[index];if(!source)return false;if(branches.length>=10){$("automation-studio-state").textContent="A flow supports up to 10 decision paths.";return false}const copy=cloneEditorValue(source),sourceIsFallback=index===branches.length-1&&!(source.conditions||[]).length;copy.name=`${source.name||`Path ${index+1}`} copy`;if(sourceIsFallback)copy.conditions=[newBranchCondition()];const fallbackIndex=branches.length&&!(branches.at(-1)?.conditions||[]).length?branches.length-1:-1,target=sourceIsFallback?index:Math.min(index+1,fallbackIndex>=0?fallbackIndex:branches.length);branches.splice(target,0,copy);selectedStudioNode="decision";selectedFlowCard={kind:"decision",index:target,branchIndex:null};renderStudioInspector();renderEditorFlow();commitEditorHistory();requestAnimationFrame(()=>focusSelectedFlowEditor("decision",target));$("automation-studio-state").textContent=sourceIsFallback?"ELSE copied as a conditional path so only one fallback remains.":"Decision path duplicated with its IF conditions and tasks. Use Undo to restore the previous flow.";return true;
  }
  function deleteBranchPath(index){
    const branches=workflowDraft.branches;if(!branches[index])return false;if(branches.length===1){$("automation-studio-state").textContent="Keep at least one decision path, or remove branching from Advanced settings.";return false}const removed=branches.splice(index,1)[0],target=Math.max(0,Math.min(index,branches.length-1));selectedStudioNode="decision";selectedFlowCard={kind:"decision",index:target,branchIndex:null};renderStudioInspector();renderEditorFlow();commitEditorHistory();requestAnimationFrame(()=>focusSelectedFlowEditor("decision",target));$("automation-studio-state").textContent=`${removed.name||"Decision path"} removed. Use Undo to restore it.`;return true;
  }
  function addStudioBlock(kind,insertionIndex=null){
    const trigger=()=>({kind:"entity",entity_id:"",operator:"changes_to",value:"",for_seconds:0,weekdays:[],at:"",sun_event:"sunrise",offset_minutes:0,interval_minutes:5,one_time_at:""});
    const condition=()=>({kind:"entity",entity_id:"",operator:"equals",value:"",for_seconds:0,weekdays:[],start_time:"",end_time:"",sun_state:"below_horizon"});
    const action=()=>({kind:"service",entity_id:"",service:"",service_data:{},delay_seconds:0,wait_operator:"equals",wait_value:"",timeout_seconds:30});
    if(kind==="trigger"){
      if(workflowDraft.triggers.length>=9){$("automation-studio-state").textContent="A flow supports up to 10 triggers including the primary trigger.";return}
      const items=visualFlowItems("trigger"),target=insertionIndex==null?items.length:Math.max(0,Math.min(insertionIndex,items.length));items.splice(target,0,trigger());writeFlowSequence("trigger",items);selectedFlowCard={kind,index:target};
    }else if(kind==="context"){
      if(workflowDraft.conditions.length>=20){$("automation-studio-state").textContent="A flow supports up to 20 context conditions.";return}
      const presence=$("automation-presence").value.trim()?1:0,signals=$("automation-signals").value.split(/[,\n]/).map(value=>value.trim()).filter(Boolean).length,target=insertionIndex==null?workflowDraft.conditions.length:Math.max(0,Math.min(insertionIndex-presence-signals,workflowDraft.conditions.length));workflowDraft.conditions.splice(target,0,condition());selectedFlowCard={kind,index:presence+signals+target};
    }else if(kind==="decision"){
      if(workflowDraft.branches.length>=10){$("automation-studio-state").textContent="A flow supports up to 10 decision branches.";return}
      const target=insertionIndex==null?workflowDraft.branches.length:Math.max(0,Math.min(insertionIndex,workflowDraft.branches.length));workflowDraft.branches.splice(target,0,{name:`Branch ${workflowDraft.branches.length+1}`,condition_mode:"all",conditions:[condition()],actions:[action()]});selectedFlowCard={kind,index:target};
    }else if(kind==="action"){
      if(workflowDraft.actions.length>=19){$("automation-studio-state").textContent="A flow supports up to 20 actions including the primary action.";return}
      const items=visualFlowItems("action"),target=insertionIndex==null?items.length:Math.max(0,Math.min(insertionIndex,items.length));items.splice(target,0,action());writeFlowSequence("action",items);selectedFlowCard={kind,index:target};
    }else{
      selectStudioNode("details");$("automation-studio-state").textContent="Automation details are already part of this flow.";return
    }
    selectedStudioNode=kind;renderStudioInspector();renderEditorFlow();commitEditorHistory();
    $("automation-studio-state").textContent=`${studioPanels[kind].title} block added. Complete its settings before saving.`;
  }
  function renderSummary(){
    $("autonomy-engine-status").textContent=state.engine?.status==="active"?"Live":state.engine?.status==="waiting_for_home_assistant"?"Waiting for HA":"Unavailable";
    $("autonomy-mode-summary").textContent=modeLabel(state.settings?.operating_mode);
    $("autonomy-mode-detail").textContent=state.settings?.operating_mode==="selective_autonomy"?`Autonomous up to ${state.settings?.autonomous_risk_ceiling||"low"} risk`:"Per-automation authority limited by global policy";
    const draftCount=(state.automations||[]).filter(item=>!item.enabled).length;
    const suggestionCount=(state.suggestions||[]).filter(item=>["pending","approval_required"].includes(item.status)&&item.delivery_notification_center!==false).length;
    $("autonomy-draft-count").textContent=String(draftCount);
    $("autonomy-suggestion-count").textContent=String(suggestionCount);
    panel.querySelector('[data-automation-overview-target="drafts"]')?.setAttribute("aria-label",`View ${draftCount} automation draft${draftCount===1?"":"s"}`);
    panel.querySelector('[data-automation-overview-target="suggestions"]')?.setAttribute("aria-label",`View ${suggestionCount} pending suggestion${suggestionCount===1?"":"s"}`);
  }

  function renderSuggestions(){
    const root=$("autonomy-suggestions");root.replaceChildren();
    const visible=(state.suggestions||[]).filter(item=>!["dismissed","expired"].includes(item.status)&&item.delivery_notification_center!==false).slice(0,30);
    if(!visible.length){root.innerHTML='<div class="autonomy-empty">No live automation suggestions yet.</div>';return}
    for(const item of visible){const row=document.createElement("div");row.className="autonomy-draft";const brain=item.source==="automation_brain";const actionable=(brain&&item.status==="pending"||item.status==="approval_required")&&item.action_service&&item.action_entity;const dismissible=["pending","approval_required"].includes(item.status);const actions=actionable||dismissible?`<div class="autonomy-draft-actions">${actionable?`<button type="button" data-suggestion-approve="${esc(item.id)}">Approve action</button>`:""}${dismissible?`<button type="button" data-suggestion-dismiss="${esc(item.id)}">Not now</button>`:""}${brain?`<button type="button" data-discovery-feedback="never_suggest" data-discovery-id="${esc(item.discovery_id)}">Never suggest</button>`:""}</div>`:"";row.innerHTML=`<div class="autonomy-draft-head"><strong>${esc(item.title||"Suggestion")}</strong><span class="automation-state" data-state="${esc(item.status||"pending")}">${brain?"Brain discovery · ":""}${esc(item.status||"pending")}</span></div><span>${esc(item.detail||"")}</span>${item.evidence?`<small>Evidence: ${esc(item.evidence)}</small>`:""}${actions}`;root.appendChild(row)}
  }

  function referencedEntities(){
    const ids=new Set();
    if(state.settings?.presence_entity)ids.add(state.settings.presence_entity);
    for(const item of state.automations){if(item.presence_entity)ids.add(item.presence_entity);for(const id of item.signal_entities||[])ids.add(id);if(item.action_entity)ids.add(item.action_entity);for(const part of [...(item.triggers||[]),...(item.conditions||[]),...(item.actions||[])])if(part.entity_id)ids.add(part.entity_id);for(const branch of item.branches||[])for(const part of [...(branch.conditions||[]),...(branch.actions||[])])if(part.entity_id)ids.add(part.entity_id)}
    return [...ids];
  }

  function renderContext(){
    const root=$("autonomy-context");root.replaceChildren();const ids=referencedEntities();
    if(!ids.length){root.innerHTML='<div class="autonomy-empty">No entities referenced yet. Add a draft or set the default presence entity.</div>';return}
    for(const id of ids){const entity=entityMap.get(id);const row=document.createElement("div");row.className="autonomy-context-row";row.innerHTML=`<div class="autonomy-draft-head"><strong>${esc(entity?.friendly_name||id)}</strong><span>${esc(entity?.state??"not loaded")}</span></div><small>${esc(id)}${entity?.unit?` · ${esc(entity.unit)}`:""}</small>`;root.appendChild(row)}
  }

  function renderLibrary(){
    const root=$("automation-library"),all=state.automations||[],query=$("automation-library-search").value.trim().toLowerCase(),filter=$("automation-library-filter").value,sort=$("automation-library-sort").value,layout=$("automation-library-layout").value;root.replaceChildren();root.classList.toggle("is-compact",layout==="compact");
    const searchable=item=>[item.name,item.objective,item.trigger_entity,item.action_entity,item.action_service,item.proposal_template,...(item.signal_entities||[]),...(item.triggers||[]).flatMap(part=>[part.entity_id,part.kind]),...(item.conditions||[]).flatMap(part=>[part.entity_id,part.kind]),...(item.actions||[]).flatMap(part=>[part.entity_id,part.service,part.kind]),...(item.branches||[]).flatMap(branch=>[branch.name,...(branch.conditions||[]).map(part=>part.entity_id),...(branch.actions||[]).flatMap(part=>[part.entity_id,part.service])])].filter(Boolean).join(" ").toLowerCase();
    const isAttention=item=>{const recovery=item.recovery_state||{},readiness=item.readiness||{};return Boolean(item.review_required||recovery.circuit_open||readiness.ready===false||["blocked_permission","paused_failure","deferred"].includes(item.status))};
    const matchesFilter=item=>{if(filter==="active")return Boolean(item.enabled);if(filter==="attention")return isAttention(item);if(filter==="disabled")return !item.enabled;if(filter==="autonomous")return item.execution_policy==="autonomous";if(filter==="watch")return item.kind==="notification_watch";return true};
    const attentionScore=item=>Number(isAttention(item));
    const summary={all:all.length,active:all.filter(item=>item.enabled).length,attention:all.filter(isAttention).length,disabled:all.filter(item=>!item.enabled).length,autonomous:all.filter(item=>item.execution_policy==="autonomous").length};
    for(const [name,count] of Object.entries(summary)){$(`automation-library-${name}-count`).textContent=String(count)}
    for(const button of $("automation-library-summary").querySelectorAll("[data-library-quick-filter]"))button.setAttribute("aria-pressed",String(button.dataset.libraryQuickFilter===filter));
    const visible=all.filter(item=>(!query||searchable(item).includes(query))&&matchesFilter(item)).slice();
    visible.sort((left,right)=>{if(sort==="name_asc")return String(left.name||"").localeCompare(String(right.name||""));if(sort==="name_desc")return String(right.name||"").localeCompare(String(left.name||""));if(sort==="active")return Number(Boolean(right.enabled))-Number(Boolean(left.enabled))||String(left.name||"").localeCompare(String(right.name||""));if(sort==="attention")return attentionScore(right)-attentionScore(left)||String(left.name||"").localeCompare(String(right.name||""));return Number(right.updated_at||right.created_at||0)-Number(left.updated_at||left.created_at||0)||String(left.name||"").localeCompare(String(right.name||""))});
    $("automation-library-count").textContent=query||filter!=="all"?`${visible.length} of ${all.length}`:`${all.length} automation${all.length===1?"":"s"}`;
    if(!all.length){root.innerHTML='<div class="autonomy-empty">No automation drafts. Start with a quick design or create your own.</div>';return}
    if(!visible.length){root.innerHTML='<div class="autonomy-empty">No automations match this search and state filter.</div>';return}
    for(const item of visible){
      const row=document.createElement("div");row.className="autonomy-draft";
      const isWatch=item.kind==="notification_watch";
      const tags=[item.source==="chat"?"Chat prepared":null,isWatch?(item.status||"armed"):(item.enabled?(item.status||"armed"):item.review_required?"Review required":"Disabled"),authorityLabel(item.execution_policy),`${Math.round(Number(item.confidence_threshold||0)*100)}% confidence`,`${item.cooldown_minutes} min cooldown`,item.risk_level].filter(Boolean);
      const feedback=item.feedback_memory||{},feedbackTotal=Number(feedback.dismissals||0)+Number(feedback.approvals||0)+Number(feedback.manual_resolutions||0)+Number(feedback.expired_suggestions||0)+Number(feedback.action_failures||0)+Number(feedback.autonomous_successes||0),resetLearning=feedbackTotal?`<button type="button" data-auto-reset-learning="${esc(item.id)}">Reset learning</button>`:"";
      const recovery=item.recovery_state||{},recoverAction=recovery.circuit_open?`<button type="button" data-auto-recover="${esc(item.id)}">Reset recovery</button>`:"";
      const primaryAction=isWatch?`<button type="button" data-auto-watch="${esc(item.id)}">Notifications</button>`:item.review_required?`<button type="button" data-auto-edit="${esc(item.id)}">Review</button><button type="button" data-auto-activate="${esc(item.id)}">Enable</button>`:`<button type="button" data-auto-edit="${esc(item.id)}">Edit</button>${item.enabled?`<button type="button" data-auto-pause="${esc(item.id)}">Pause</button>`:`<button type="button" data-auto-activate="${esc(item.id)}" data-auto-activation-label="Resume">Resume</button>`}`;
      const triggerSummary=`${item.trigger_entity||"no trigger"} ${(item.trigger_operator||"").replaceAll("_"," ")}${item.trigger_value?` ${item.trigger_value}`:""}${item.trigger_for_seconds?` for ${item.trigger_for_seconds}s`:""}`;
      const actionSummary=item.action_service&&item.action_entity?`${item.action_service} → ${item.action_entity}`:"No device action";
      row.innerHTML=`<div class="autonomy-draft-head"><div><strong>${esc(item.name)}</strong><div>${esc(item.objective)}</div></div><div class="autonomy-draft-actions">${primaryAction}<button type="button" data-auto-duplicate="${esc(item.id)}">Duplicate</button>${recoverAction}${resetLearning}<button type="button" data-auto-delete="${esc(item.id)}">Delete</button></div></div><div class="autonomy-tags">${tags.map(tag=>`<span>${esc(tag)}</span>`).join("")}</div>`;
      const flow=flowElement(item);
      if(flow)row.append(flow);else row.insertAdjacentHTML("beforeend",`<small><strong>When:</strong> ${esc(triggerSummary)}<br><strong>Then:</strong> ${esc(item.proposal_template||"Record the match")}<br><strong>Action:</strong> ${esc(actionSummary)}<br><strong>Presence:</strong> ${esc(item.presence_entity||"not required by this rule")}</small>`);
      const reasoning=["deferred","paused_failure","blocked_permission"].includes(item.status)?item.last_deferred_reason:item.status==="satisfied"?item.last_satisfied_reason:"";if(reasoning)row.insertAdjacentHTML("beforeend",`<small><strong>Why ${esc(item.status)}:</strong> ${esc(reasoning)}</small>`);
      const readiness=item.readiness||{};if(readiness.summary)row.insertAdjacentHTML("beforeend",`<small><strong>Live readiness:</strong> ${esc(readiness.ready?"Ready":readiness.summary)}${!readiness.ready?" · Fix entity permissions or HA safety labels before execution.":""}</small>`);
      const episode=item.active_episode;if(episode)row.insertAdjacentHTML("beforeend",`<small><strong>Active episode:</strong> ${esc(episode.trend||"tracking")} · current ${esc(episode.current_value)} · worst ${esc(episode.worst_value)} · ${Number(episode.sample_count||0)} samples</small>`);
      if(feedbackTotal)row.insertAdjacentHTML("beforeend",`<small><strong>Learned feedback:</strong> ${Number(feedback.approvals||0)} approved · ${Number(feedback.dismissals||0)} Not now · ${Number(feedback.manual_resolutions||0)} completed manually${Number(feedback.consecutive_dismissals||0)?` · suggestion threshold raised gradually (${Number(feedback.consecutive_dismissals)}×)`:""}</small>`);
      if(feedbackTotal)row.insertAdjacentHTML("beforeend",`<small><strong>Outcome health:</strong> ${Number(feedback.autonomous_successes||0)} automatic success · ${Number(feedback.action_failures||0)} action failure · ${Number(feedback.expired_suggestions||0)} unanswered expired · ${item.suggestion_timeout_minutes||30} min response window</small>`);
      if(recovery.detail)row.insertAdjacentHTML("beforeend",`<small><strong>Failure circuit:</strong> ${esc(recovery.detail)}${recovery.circuit_open?" · execution paused until Reset recovery":""}</small>`);
      const decisions=(item.decision_history||[]).slice(0,5);if(decisions.length)row.insertAdjacentHTML("beforeend",`<details class="automation-decision-journal"><summary>Decision journal · ${item.decision_history.length} recent evaluation${item.decision_history.length===1?"":"s"}</summary>${decisions.map(entry=>`<div class="autonomy-event"><strong>${esc(String(entry.outcome||"decision").replaceAll("_"," "))}</strong><span>${esc(entry.detail||"")}</span>${entry.evidence?`<small>${esc(entry.evidence)}</small>`:""}<time>${new Date(Number(entry.created_at||0)*1000).toLocaleString()}</time></div>`).join("")}</details>`);
      root.appendChild(row);
    }
  }

  function renderAutomationMemory(){
    const root=$("automation-memory-list"),records=state.entity_memory||[];root.replaceChildren();$("automation-memory-count").textContent=`${records.length} mapping${records.length===1?"":"s"}`;
    if(!records.length){root.innerHTML='<div class="autonomy-empty">No confirmed mappings yet. Create an automation in Chat and ZBRANO will remember your entity choices.</div>';return}
    for(const item of records){const row=document.createElement("div");row.className="automation-memory-row";row.innerHTML=`<div><strong>${esc(item.alias)}</strong> <span class="automation-state">${esc(item.role||"entity")}</span></div><button type="button" data-automation-memory-forget="${esc(item.id)}">Forget</button><small>${esc(item.friendly_name||item.entity_id)} Â· ${esc(item.entity_id)}</small>`;root.appendChild(row)}
  }

  function renderAutomationBrain(){
    const root=$("automation-brain-list"),patterns=state.patterns||[],discoveries=state.discoveries||[],context=state.area_context||{},areas=context.areas||[],zones=context.zones||[];root.replaceChildren();
    $("automation-brain-count").textContent=`${patterns.filter(item=>item.status==="learned").length} learned · ${areas.length} rooms · ${zones.length} zones`;
    if(!areas.length){root.innerHTML='<div class="autonomy-empty">No Home Assistant Areas were found. Assign devices to Areas so ZBRANO can reason room by room.</div>';return}
    for(const area of areas.slice(0,30)){const row=document.createElement("div");row.className="automation-brain-row";const linked=Boolean(area.zone_entity_id);row.innerHTML=`<div><strong>${esc(area.name||area.area_id)}</strong><div>${esc(area.site_name||"No site label")}</div></div><span class="automation-state">${linked?"zone linked":"area only"}</span><small>${linked?`${esc(area.site_label||area.site_name)} → ${esc(area.zone_entity_id)}`:"Add a site-* label matching a Zone to make presence location-aware."}</small>`;root.appendChild(row)}
    const visible=[...discoveries.slice(0,8),...patterns.filter(item=>item.status==="learned").slice(0,8)];
    for(const item of visible){const discovery=Boolean(item.kind==="dark_occupied_light"),row=document.createElement("div");row.className="automation-brain-row";const confidence=Math.round(Number(item.confidence||0)*100);const actions=discovery&&item.preference!=="never_suggest"?`<div class="autonomy-draft-actions"><button type="button" data-discovery-feedback="always_suggest" data-discovery-id="${esc(item.id)}">Keep suggesting</button><button type="button" data-discovery-feedback="never_suggest" data-discovery-id="${esc(item.id)}">Never suggest</button></div>`:"";row.innerHTML=`<div><strong>${esc(item.title||`${item.area_name||"Room"}: occupancy then lighting`)}</strong><div>${item.site_name?`${esc(item.site_name)} · `:""}${discovery?"Common-sense opportunity":`${Number(item.occurrences||0)} repeated sequence${Number(item.occurrences||0)===1?"":"s"}`}</div></div><span class="automation-state">${confidence}% · ${esc(item.status||"learning")}</span><small>${esc(item.evidence||`${item.presence_entity||"Presence"} followed by ${item.action_entity||"an action"}`)}</small>${actions}`;root.appendChild(row)}
  }

  function renderTimeline(){
    const root=$("autonomy-timeline");root.replaceChildren();
    if(!state.timeline.length){root.innerHTML='<div class="autonomy-empty">No activity yet. Configuration changes and future decisions will appear here.</div>';return}
    for(const item of state.timeline){const row=document.createElement("div");row.className="autonomy-event";row.innerHTML=`<strong>${esc(item.title)}</strong>${item.detail?`<span>${esc(item.detail)}</span>`:""}<time>${new Date(Number(item.created_at||0)*1000).toLocaleString()}</time>`;root.appendChild(row)}
  }

  function renderSettings(){
    const settings=state.settings||{};
    const radio=panel.querySelector(`input[name="autonomy-mode"][value="${settings.operating_mode||"suggest_only"}"]`);if(radio)radio.checked=true;
    $("autonomy-presence-entity").value=settings.presence_entity||"";
    $("autonomy-min-confidence").value=String(settings.minimum_confidence??0.75);
    $("autonomy-default-cooldown").value=String(settings.default_cooldown_minutes??30);
    $("autonomy-risk-ceiling").value=settings.autonomous_risk_ceiling||"low";
    $("autonomy-require-presence").checked=settings.require_presence!==false;
    $("autonomy-respect-quiet").checked=settings.respect_quiet_hours!==false;
    $("autonomy-notify-autonomous").checked=settings.notify_after_autonomous_action!==false;
    $("autonomy-passive-learning").checked=settings.passive_learning_enabled!==false;
  }

  function renderAll(){renderSummary();renderSuggestions();renderContext();renderLibrary();renderAutomationMemory();renderAutomationBrain();renderTimeline();renderSettings()}

  async function loadEntityContext(){
    const root=$("autonomy-context");root.innerHTML='<div class="autonomy-empty">Loading Home Assistant context…</div>';
    try{
      const data=await api("api/ha/entities");entityMap=new Map((data.entities||[]).map(item=>[item.entity_id,item]));
      const options=$("automation-entity-options");options.replaceChildren();
      for(const entity of data.entities||[]){const option=document.createElement("option");option.value=entity.entity_id;option.label=entity.friendly_name||entity.entity_id;options.appendChild(option)}
      renderContext();renderLibrary();renderEditorFlow();
    }catch(error){root.innerHTML=`<div class="autonomy-empty">Context unavailable: ${esc(error.message||error)}</div>`}
  }

  async function loadWorkspace(){state=await api("api/automations");try{notificationState=await api("api/notifications")}catch(_error){notificationState={channels:[]}}renderAll();await loadEntityContext()}

  function editorSnapshot(){
    const trigger={kind:$("automation-trigger-kind").value,entity_id:$("automation-trigger-entity").value.trim(),operator:$("automation-trigger-operator").value,value:$("automation-trigger-value").value.trim(),for_seconds:Number($("automation-trigger-for").value||0),at:$("automation-trigger-at").value,weekdays:parseWeekdays($("automation-trigger-weekdays").value),sun_event:$("automation-trigger-sun-event").value,offset_minutes:Number($("automation-trigger-sun-offset").value||0),interval_minutes:Number($("automation-trigger-interval").value||5),one_time_at:$("automation-trigger-one-time").value};
    const action={kind:"service",entity_id:$("automation-action-entity").value.trim(),service:$("automation-action-service").value.trim(),service_data:{},delay_seconds:0,wait_operator:"equals",wait_value:"",timeout_seconds:30};
    return {
      name:$("automation-name").value.trim()||"New automation",
      objective:$("automation-objective").value.trim(),
      presence_entity:$("automation-presence").value.trim(),
      signal_entities:$("automation-signals").value.split(/[,\n]/).map(value=>value.trim()).filter(Boolean),
      trigger_entity:$("automation-trigger-entity").value.trim(),
      trigger_operator:$("automation-trigger-operator").value,
      trigger_value:$("automation-trigger-value").value.trim(),
      trigger_for_seconds:Number($("automation-trigger-for").value||0),
      proposal_template:$("automation-proposal").value.trim(),
      action_entity:$("automation-action-entity").value.trim(),
      action_service:$("automation-action-service").value.trim(),
      cooldown_minutes:Number($("automation-cooldown").value||30),
      suggestion_timeout_minutes:Number($("automation-suggestion-timeout").value||30),
      failure_limit:Number($("automation-failure-limit").value||3),
      failure_window_minutes:Number($("automation-failure-window").value||60),
      reoffer_delta:Number($("automation-reoffer-delta").value||0),
      reset_delta:Number($("automation-reset-delta").value||0),
      confidence_threshold:Number($("automation-confidence").value||0.75),
      execution_policy:$("automation-execution-policy").value,
      triggers:[...((trigger.kind!=="entity"||trigger.entity_id)?[trigger]:[]),...workflowDraft.triggers].filter(item=>(item.kind||"entity")!=="entity"||item.entity_id),
      trigger_mode:workflowDraft.trigger_mode,
      conditions:workflowDraft.conditions.filter(item=>(item.kind||"entity")!=="entity"||item.entity_id),
      condition_mode:workflowDraft.condition_mode,
      actions:[...(action.entity_id&&action.service?[action]:[]),...workflowDraft.actions].filter(actionStepValid),
      branches:workflowDraft.branches.map(branch=>({...branch,name:(branch.name||"Branch").trim(),conditions:(branch.conditions||[]).filter(item=>(item.kind||"entity")!=="entity"||item.entity_id),actions:(branch.actions||[]).filter(actionStepValid)})),
    };
  }

  function editorValidationIssues(){
    const issues=[],add=(kind,message,field)=>issues.push({kind,message,field});
    if(!$("automation-name").value.trim())add("details","Add an automation name","automation-name");
    if(!$("automation-objective").value.trim())add("details","Describe the objective","automation-objective");
    const validateTrigger=(item,primary=false)=>{const kind=item.kind||"entity",prefix=primary?"Trigger":"Additional trigger";if(kind==="entity"&&!item.entity_id)add("trigger",`${prefix}: choose an entity`,primary?"automation-trigger-entity":null);else if(kind==="time"&&!item.at)add("trigger",`${prefix}: choose a local time`,primary?"automation-trigger-at":null);else if(kind==="interval"&&Number(item.interval_minutes)<1)add("trigger",`${prefix}: enter an interval`,primary?"automation-trigger-interval":null);else if(kind==="one_time"&&!item.one_time_at)add("trigger",`${prefix}: choose a date and time`,primary?"automation-trigger-one-time":null)};
    validateTrigger({kind:$("automation-trigger-kind").value,entity_id:$("automation-trigger-entity").value.trim(),at:$("automation-trigger-at").value,interval_minutes:Number($("automation-trigger-interval").value||0),one_time_at:$("automation-trigger-one-time").value},true);
    for(const trigger of workflowDraft.triggers)validateTrigger(trigger);
    if(workflowDraft.trigger_mode==="all"){
      const allTriggers=[{kind:$("automation-trigger-kind").value,operator:$("automation-trigger-operator").value},...workflowDraft.triggers];
      if(allTriggers.some(item=>(item.kind||"entity")!=="entity"))add("trigger","AND requires entity-state events; use OR for schedules");
      if(allTriggers.some(item=>(item.operator||"changes_to")==="any_change"))add("trigger","AND requires a target state, threshold, or comparison");
    }
    for(const condition of workflowDraft.conditions){const kind=condition.kind||"entity";if(kind==="entity"&&!condition.entity_id)add("context","Condition: choose an entity");else if(kind==="time_window"&&(!condition.start_time||!condition.end_time))add("context","Condition: complete the time window");else if(kind==="weekday"&&!(condition.weekdays||[]).length)add("context","Condition: select at least one weekday")}
    const primaryEntity=$("automation-action-entity").value.trim(),primaryService=$("automation-action-service").value.trim();if(Boolean(primaryEntity)!==Boolean(primaryService))add("action","Complete both action entity and service",primaryEntity?"automation-action-service":"automation-action-entity");
    try{const data=JSON.parse($("automation-action-data").value||"{}");if(!data||Array.isArray(data)||typeof data!=="object")throw new Error()}catch(_error){add("action","Action service data must be a JSON object","automation-action-data")}
    const validateAction=(item,issueKind="action",prefix="Action step")=>{const kind=item.kind||"service";if(kind==="service"&&(!item.entity_id||!item.service))add(issueKind,`${prefix}: complete entity and service`);else if(kind==="notification"&&(!item.entity_id||!item.notification_message))add(issueKind,`${prefix}: choose a channel and enter a message`);else if(kind==="delay"&&Number(item.delay_seconds)<1)add(issueKind,`${prefix}: enter at least one delay second`);else if(kind==="wait_state"&&!item.entity_id)add(issueKind,`${prefix}: choose a wait entity`)};
    for(const action of workflowDraft.actions)validateAction(action);
    for(const branch of workflowDraft.branches){for(const condition of branch.conditions||[]){if((condition.kind||"entity")==="entity"&&!condition.entity_id)add("decision",`${branch.name||"Branch"}: complete its condition`)}for(const action of branch.actions||[])validateAction(action,"decision",`${branch.name||"Branch"} action`)}
    return issues;
  }
  function renderEditorValidation(){
    const issues=editorValidationIssues(),root=$("automation-studio-validation");root.hidden=!issues.length;root.replaceChildren();
    if(issues.length){const title=document.createElement("strong");title.textContent=`${issues.length} item${issues.length===1?"":"s"} to review`;root.append(title);for(const issue of issues){const button=document.createElement("button");button.type="button";button.dataset.validationKind=issue.kind;button.dataset.validationField=issue.field||"";button.textContent=issue.message;root.append(button)}}
    const kinds=new Set(issues.map(issue=>issue.kind));for(const node of $("automation-flow-preview").querySelectorAll("[data-flow-kind]")){const kind=["branch-action","branch-condition"].includes(node.dataset.flowKind)?"decision":node.dataset.flowKind,invalid=kinds.has(kind);node.classList.toggle("has-validation-error",invalid);node.setAttribute("aria-invalid",String(invalid))}
    return issues;
  }
  function focusEditorIssue(issue){selectStudioNode(issue.kind);const field=issue.field?$("studio-"+issue.field):null;(field||$("automation-studio-inspector-fields").querySelector("input,select,textarea"))?.focus()}

  function renderEditorFlow(){
    const snapshot=editorSnapshot(),root=$("automation-flow-preview");
    const primaryTrigger={kind:$("automation-trigger-kind").value,entity_id:$("automation-trigger-entity").value.trim(),operator:$("automation-trigger-operator").value,value:$("automation-trigger-value").value.trim(),for_seconds:Number($("automation-trigger-for").value||0),at:$("automation-trigger-at").value,weekdays:parseWeekdays($("automation-trigger-weekdays").value),sun_event:$("automation-trigger-sun-event").value,offset_minutes:Number($("automation-trigger-sun-offset").value||0),interval_minutes:Number($("automation-trigger-interval").value||5),one_time_at:$("automation-trigger-one-time").value};
    const primaryAction={kind:"service",entity_id:$("automation-action-entity").value.trim(),service:$("automation-action-service").value.trim(),service_data:{}};
    const visualSnapshot={...snapshot,studio_visual_draft:true,trigger_mode:workflowDraft.trigger_mode,triggers:[primaryTrigger,...cloneEditorValue(workflowDraft.triggers)],conditions:cloneEditorValue(workflowDraft.conditions),actions:[...(primaryAction.entity_id||primaryAction.service?[primaryAction]:[]),...cloneEditorValue(workflowDraft.actions)],branches:cloneEditorValue(workflowDraft.branches)};
    window.zbranoAutomationFlow?.render(root,visualSnapshot,entityLabel);
    const actualContextCount=(snapshot.presence_entity?1:0)+(snapshot.signal_entities||[]).length+(visualSnapshot.conditions||[]).length,actualDecisionCount=(visualSnapshot.branches||[]).length,actualActionCount=(visualSnapshot.actions||[]).length;
    for(const card of root?.querySelectorAll("[data-flow-kind]")||[]){
      const kind=card.dataset.flowKind,index=Number(card.dataset.flowIndex),branchIndex=card.hasAttribute("data-flow-branch-index")?Number(card.dataset.flowBranchIndex):null,deletable=kind==="trigger"?(index>0||primaryTrigger.kind!=="entity"||Boolean(primaryTrigger.entity_id)):kind==="context"?index<actualContextCount:kind==="decision"?index<actualDecisionCount:kind==="action"?index<actualActionCount:kind==="branch-action"?Boolean(visualSnapshot.branches?.[branchIndex]?.actions?.[index]):kind==="branch-condition"?Boolean(visualSnapshot.branches?.[branchIndex]?.conditions?.[index]):false;
      if(deletable&&kind!=="decision"){
        card.draggable=true;card.setAttribute("aria-grabbed","false");
        const controls=document.createElement("span");controls.className="automation-flow-card-actions";
        const duplicate=document.createElement("button");duplicate.type="button";duplicate.className="automation-flow-card-duplicate";duplicate.dataset.flowDuplicateKind=kind;duplicate.dataset.flowDuplicateIndex=String(index);if(branchIndex!=null)duplicate.dataset.flowBranchIndex=String(branchIndex);duplicate.setAttribute("aria-label",`Duplicate ${kind} card ${index+1}`);duplicate.title=kind==="context"&&contextFlowSource(index).type==="presence"?"Presence is unique":"Duplicate card";duplicate.textContent="⧉";if(kind==="context"&&contextFlowSource(index).type==="presence")duplicate.disabled=true;
        const remove=document.createElement("button");remove.type="button";remove.className="automation-flow-card-delete";remove.dataset.flowDeleteKind=kind;remove.dataset.flowDeleteIndex=String(index);if(branchIndex!=null)remove.dataset.flowBranchIndex=String(branchIndex);remove.setAttribute("aria-label",`Delete ${kind} card ${index+1}`);remove.title="Delete card";remove.textContent="×";controls.append(duplicate,remove);card.append(controls);
      }
      if(kind===selectedFlowCard.kind&&index===selectedFlowCard.index&&(!["branch-action","branch-condition"].includes(kind)||branchIndex===selectedFlowCard.branchIndex))card.classList.add("is-selected");
    }
    $("automation-studio-flow-name").textContent=snapshot.name;
    for(const button of panel.querySelectorAll("[data-studio-node]"))button.classList.toggle("active",button.dataset.studioNode===selectedStudioNode);
    renderEditorValidation();
    updateEditorDirtyState();
  }

  function clearEditor(){
    $("automation-studio-test-results").hidden=true;
    $("automation-draft-form").reset();$("automation-edit-id").value="";$("automation-editor-title").textContent="New automation draft";$("automation-cancel-edit").hidden=true;$("automation-cooldown").value=String(state.settings?.default_cooldown_minutes||30);$("automation-confidence").value=String(state.settings?.minimum_confidence||0.75);$("automation-risk").value="controlled";$("automation-execution-policy").value="inherit";$("automation-max-actions").value="2";$("automation-trigger-operator").value="changes_to";$("automation-trigger-for").value="0";$("automation-action-data").value="{}";$("automation-enabled").checked=false;$("automation-notify-action").checked=true;$("automation-reversible-only").checked=true;$("automation-delivery-voice").checked=true;$("automation-delivery-center").checked=true;$("automation-delivery-push").checked=true;$("automation-draft-state").textContent="";
    $("automation-suggestion-timeout").value="30";
    $("automation-failure-limit").value="3";$("automation-failure-window").value="60";
    $("automation-reoffer-delta").value="0";$("automation-reset-delta").value="0";
    $("automation-trigger-kind").value="entity";$("automation-trigger-at").value="";$("automation-trigger-weekdays").value="";$("automation-trigger-sun-event").value="sunrise";$("automation-trigger-sun-offset").value="0";$("automation-trigger-interval").value="5";$("automation-trigger-one-time").value="";
    workflowDraft={triggers:[],trigger_mode:"any",conditions:[],condition_mode:"all",actions:[],branches:[]};selectedStudioNode="trigger";selectedFlowCard={kind:"trigger",index:0};renderEditorFlow();renderStudioInspector();resetEditorHistory();
  }

  function fillEditor(item){
    $("automation-suggestion-timeout").value=String(item.suggestion_timeout_minutes||30);
    $("automation-failure-limit").value=String(item.failure_limit||3);$("automation-failure-window").value=String(item.failure_window_minutes||60);
    $("automation-reoffer-delta").value=String(item.reoffer_delta||0);$("automation-reset-delta").value=String(item.reset_delta||0);
    $("automation-edit-id").value=item.id||"";$("automation-name").value=item.name||"";$("automation-objective").value=item.objective||"";$("automation-presence").value=item.presence_entity||"";$("automation-signals").value=(item.signal_entities||[]).join(", ");$("automation-trigger-entity").value=item.trigger_entity||(item.signal_entities||[])[0]||"";$("automation-trigger-operator").value=item.trigger_operator||"changes_to";$("automation-trigger-value").value=item.trigger_value||"";$("automation-trigger-for").value=String(item.trigger_for_seconds||0);$("automation-enabled").checked=Boolean(item.enabled);$("automation-context-notes").value=item.context_notes||"";$("automation-proposal").value=item.proposal_template||"";$("automation-action-entity").value=item.action_entity||"";$("automation-action-service").value=item.action_service||"";$("automation-action-data").value=JSON.stringify(item.action_service_data||{},null,2);$("automation-cooldown").value=String(item.cooldown_minutes||30);$("automation-confidence").value=String(item.confidence_threshold||0.75);$("automation-risk").value=item.risk_level||"controlled";$("automation-execution-policy").value=item.execution_policy||"inherit";$("automation-max-actions").value=String(item.max_actions_per_hour||2);$("automation-notify-action").checked=item.notify_on_action!==false;$("automation-reversible-only").checked=item.reversible_only!==false;$("automation-delivery-voice").checked=item.delivery_voice!==false;$("automation-delivery-center").checked=item.delivery_notification_center!==false;$("automation-delivery-push").checked=item.delivery_ha_push!==false;$("automation-editor-title").textContent=item.id?"Edit automation":"New automation";$("automation-cancel-edit").hidden=!item.id;showView("studio");showLibraryView("create");document.querySelector(".automation-advanced")?.removeAttribute("open");selectedStudioNode="details";
    const triggers=Array.isArray(item.triggers)&&item.triggers.length?item.triggers:[{kind:"entity",entity_id:item.trigger_entity||"",operator:item.trigger_operator||"changes_to",value:item.trigger_value||"",for_seconds:item.trigger_for_seconds||0}],primary=triggers[0]||{};$("automation-trigger-kind").value=primary.kind||"entity";$("automation-trigger-entity").value=primary.entity_id||"";$("automation-trigger-operator").value=primary.operator||"changes_to";$("automation-trigger-value").value=primary.value||"";$("automation-trigger-for").value=String(primary.for_seconds||0);$("automation-trigger-at").value=primary.at||"";$("automation-trigger-weekdays").value=formatWeekdays(primary.weekdays);$("automation-trigger-sun-event").value=primary.sun_event||"sunrise";$("automation-trigger-sun-offset").value=String(primary.offset_minutes||0);$("automation-trigger-interval").value=String(primary.interval_minutes||5);$("automation-trigger-one-time").value=primary.one_time_at||"";const actions=Array.isArray(item.actions)?item.actions:[],legacyPrimary=actions[0]&&(actions[0].kind||"service")==="service";if(!legacyPrimary){$("automation-action-entity").value="";$("automation-action-service").value="";$("automation-action-data").value="{}"}workflowDraft={triggers:triggers.slice(1),trigger_mode:item.trigger_mode==="all"?"all":"any",conditions:Array.isArray(item.conditions)?item.conditions:[],condition_mode:item.condition_mode||"all",actions:legacyPrimary?actions.slice(1):actions,branches:Array.isArray(item.branches)?item.branches:[]};
    renderEditorFlow();renderStudioInspector();resetEditorHistory();
  }

  function inventoryMatches({domains=[],deviceClasses=[],keywords=[],limit=3}){
    const normalizedKeywords=keywords.map(value=>String(value).toLowerCase());
    return [...entityMap.values()].map(entity=>{
      const domain=String(entity.domain||entity.entity_id?.split(".",1)[0]||"").toLowerCase();
      const deviceClass=String(entity.device_class||"").toLowerCase();
      const text=`${entity.entity_id||""} ${entity.friendly_name||""}`.toLowerCase().replaceAll("_"," ");
      if(domains.length&&!domains.includes(domain))return null;
      const classScore=deviceClasses.includes(deviceClass)?20:0;
      const keywordScore=normalizedKeywords.reduce((score,keyword)=>score+(text.includes(keyword)?4:0),0);
      if((deviceClasses.length||normalizedKeywords.length)&&!classScore&&!keywordScore)return null;
      return {entity,score:classScore+keywordScore+1};
    }).filter(Boolean).sort((left,right)=>right.score-left.score||String(left.entity.friendly_name||left.entity.entity_id).localeCompare(String(right.entity.friendly_name||right.entity.entity_id))).slice(0,limit).map(item=>item.entity.entity_id);
  }

  function template(name){
    const presence=state.settings?.presence_entity||"";
    const temperatures=inventoryMatches({domains:["sensor"],deviceClasses:["temperature"],keywords:["temperature","temp"],limit:2});
    const humidity=inventoryMatches({domains:["sensor"],deviceClasses:["humidity"],keywords:["humidity"],limit:1});
    const climate=inventoryMatches({domains:["climate"],limit:1})[0]||"";
    const airSignals=inventoryMatches({domains:["sensor","binary_sensor"],deviceClasses:["carbon_dioxide","volatile_organic_compounds","pm25"],keywords:["co2","carbon dioxide","voc","pm2.5","pm25","air quality"],limit:4});
    const ventilation=inventoryMatches({domains:["fan"],keywords:["ventilation","extractor","exhaust","air"],limit:1})[0]||inventoryMatches({domains:["fan"],limit:1})[0]||"";
    const openings=inventoryMatches({domains:["binary_sensor"],deviceClasses:["door","window","opening","garage_door"],keywords:["door","window","opening"],limit:4});
    const illuminance=inventoryMatches({domains:["sensor"],deviceClasses:["illuminance"],keywords:["illuminance","lux","light level"],limit:1})[0]||"";
    const light=inventoryMatches({domains:["light"],limit:1})[0]||"";
    const templates={
      comfort:{name:"Comfort advisor",objective:"Notice uncomfortable temperature while presence is confirmed and propose an appropriate comfort action",presence_entity:presence,signal_entities:[...new Set([...temperatures,...humidity])],context_notes:"Review the installation-derived candidates. Compare indoor temperature and trend with available outdoor conditions, season, time of day, humidity, recent occupancy, and current HVAC state. Avoid reacting to brief sensor spikes.",proposal_template:"The room is becoming uncomfortable. Would you like me to adjust the climate system?",action_entity:climate,action_service:climate?"climate.set_hvac_mode":"",cooldown_minutes:30,confidence_threshold:0.8,risk_level:"controlled",execution_policy:"approval_required",notify_on_action:true,reversible_only:true,max_actions_per_hour:2},
      air:{name:"Air quality advisor",objective:"Notice sustained worsening air quality while occupied and suggest ventilation",presence_entity:presence,signal_entities:airSignals,context_notes:"Review the installation-derived candidates. Use sustained readings and trends rather than one sample, and consider active extraction and outdoor air quality.",proposal_template:"Air quality is getting worse. Would you like me to start ventilation?",action_entity:ventilation,action_service:ventilation?"fan.turn_on":"",cooldown_minutes:20,confidence_threshold:0.82,risk_level:"controlled",execution_policy:"approval_required",notify_on_action:true,reversible_only:true,max_actions_per_hour:2},
      security:{name:"Departure safety check",objective:"Notice sustained absence while an opening remains active",presence_entity:presence,signal_entities:openings,context_notes:"Review the installation-derived candidates. Require sustained absence and do not infer that arbitrary equipment should be switched off.",proposal_template:"It looks like the area is empty, but an opening may have been left active. Would you like a safety check?",action_entity:"",action_service:"",cooldown_minutes:30,confidence_threshold:0.9,risk_level:"high",execution_policy:"suggest",notify_on_action:true,reversible_only:true,max_actions_per_hour:1},
      lighting:{name:"Presence lighting",objective:"Suggest lighting when presence is confirmed and available light is low",presence_entity:presence,signal_entities:[...new Set([illuminance,light].filter(Boolean))],context_notes:"Review the installation-derived candidates. Require stable presence and low illuminance. Do nothing when daylight is sufficient or lighting is already on.",proposal_template:"Presence and low light were confirmed. Would you like me to turn on the light?",action_entity:light,action_service:light?"light.turn_on":"",cooldown_minutes:10,confidence_threshold:0.9,risk_level:"low",execution_policy:"approval_required",notify_on_action:true,reversible_only:true,max_actions_per_hour:4}
    };fillEditor(templates[name]);markEditorAsUnsaved()
  }

  panel.querySelector(".autonomy-tabs")?.addEventListener("click",event=>{const button=event.target.closest("[data-auto-view]");if(button)showView(button.dataset.autoView)});
  panel.querySelector(".autonomy-metrics")?.addEventListener("click",event=>{const button=event.target.closest("[data-automation-overview-target]");if(button)openOverviewShortcut(button.dataset.automationOverviewTarget)});
  panel.querySelector(".automation-library-tabs")?.addEventListener("click",event=>{const button=event.target.closest("[data-automation-library-view]");if(button)showLibraryView(button.dataset.automationLibraryView)});
  $("automation-library-search").addEventListener("input",renderLibrary);
  $("automation-library-filter").addEventListener("change",()=>{persistLibraryPrefs();renderLibrary()});
  $("automation-library-sort").addEventListener("change",()=>{persistLibraryPrefs();renderLibrary()});
  $("automation-library-layout").addEventListener("change",()=>{persistLibraryPrefs();renderLibrary()});
  $("automation-library-summary").addEventListener("click",event=>{const button=event.target.closest("[data-library-quick-filter]");if(!button)return;$("automation-library-filter").value=button.dataset.libraryQuickFilter;persistLibraryPrefs();renderLibrary()});
  panel.addEventListener("pointerdown",event=>{if(event.target.closest(".automation-flow-card-actions"))return;const block=event.target.closest(".automation-studio-preview [data-flow-kind]");if(block&&!block.draggable)selectStudioNode(block.dataset.flowKind,Number(block.dataset.flowIndex),block.hasAttribute("data-flow-branch-index")?Number(block.dataset.flowBranchIndex):null)},{capture:true});
  panel.addEventListener("click",async event=>{
    const addBranchPathButton=event.target.closest("[data-flow-add-branch]");if(addBranchPathButton){event.preventDefault();event.stopPropagation();addBranchPath();return}
    const branchPathAction=event.target.closest("[data-flow-branch-action]");if(branchPathAction){event.preventDefault();event.stopPropagation();const branchIndex=Number(branchPathAction.dataset.flowBranchIndex),action=branchPathAction.dataset.flowBranchAction;if(action==="previous")moveBranchPathTo(branchIndex,branchIndex-1);else if(action==="next")moveBranchPathTo(branchIndex,branchIndex+1);else if(action==="duplicate")duplicateBranchPath(branchIndex);else if(action==="delete")deleteBranchPath(branchIndex);return}
    const branchConditionTemplate=event.target.closest("[data-flow-branch-condition-template]");if(branchConditionTemplate){event.preventDefault();event.stopPropagation();const branchIndex=Number(branchConditionTemplate.dataset.flowBranchIndex);addBranchCondition(branchIndex,branchQuickInsertion("branch-condition",branchIndex),branchConditionTemplate.dataset.flowBranchConditionTemplate);return}
    const addBranchConditionButton=event.target.closest("[data-flow-branch-add-condition]");if(addBranchConditionButton){event.preventDefault();event.stopPropagation();const branchIndex=Number(addBranchConditionButton.dataset.flowBranchAddCondition);addBranchCondition(branchIndex,branchQuickInsertion("branch-condition",branchIndex));return}
    const branchTaskTemplate=event.target.closest("[data-flow-branch-task-template]");if(branchTaskTemplate){event.preventDefault();event.stopPropagation();const branchIndex=Number(branchTaskTemplate.dataset.flowBranchIndex);addBranchActionTemplate(branchIndex,branchTaskTemplate.dataset.flowBranchTaskTemplate,branchQuickInsertion("branch-action",branchIndex));return}
    const deleteCard=event.target.closest("[data-flow-delete-kind]");if(deleteCard){event.preventDefault();event.stopPropagation();deleteFlowCard(deleteCard.dataset.flowDeleteKind,Number(deleteCard.dataset.flowDeleteIndex),deleteCard.hasAttribute("data-flow-branch-index")?Number(deleteCard.dataset.flowBranchIndex):null);return}
    const duplicateCard=event.target.closest("[data-flow-duplicate-kind]");if(duplicateCard){event.preventDefault();event.stopPropagation();duplicateFlowCard(duplicateCard.dataset.flowDuplicateKind,Number(duplicateCard.dataset.flowDuplicateIndex),duplicateCard.hasAttribute("data-flow-branch-index")?Number(duplicateCard.dataset.flowBranchIndex):null);return}
    const validationIssue=event.target.closest("[data-validation-kind]");if(validationIssue){focusEditorIssue({kind:validationIssue.dataset.validationKind,field:validationIssue.dataset.validationField});return}
    const studioBlock=event.target.closest(".automation-studio-preview [data-studio-node],.automation-studio-preview [data-flow-kind]");if(studioBlock){selectStudioNode(studioBlock.dataset.studioNode||studioBlock.dataset.flowKind,studioBlock.hasAttribute("data-flow-index")?Number(studioBlock.dataset.flowIndex):null,studioBlock.hasAttribute("data-flow-branch-index")?Number(studioBlock.dataset.flowBranchIndex):null);return}
    const templateButton=event.target.closest("[data-auto-template]");if(templateButton){if(confirmEditorReplacement("load this template"))template(templateButton.dataset.autoTemplate);return}
    const notificationWatch=event.target.closest("[data-auto-watch]");if(notificationWatch){showView("notifications");window.zbranoNotificationCenter?.showView("watchlist");window.zbranoNotificationCenter?.load();return}
    const approve=event.target.closest("[data-suggestion-approve]");if(approve){approve.disabled=true;try{await api(`api/automations/suggestions/${encodeURIComponent(approve.dataset.suggestionApprove)}/approve`,{method:"POST"});await loadWorkspace()}catch(error){alert(`Action failed: ${error.message||error}`);approve.disabled=false}return}
    const dismiss=event.target.closest("[data-suggestion-dismiss]");if(dismiss){dismiss.disabled=true;try{await api(`api/automations/suggestions/${encodeURIComponent(dismiss.dataset.suggestionDismiss)}/dismiss`,{method:"POST"});await loadWorkspace()}catch(error){alert(`Dismiss failed: ${error.message||error}`);dismiss.disabled=false}return}
    const discoveryFeedback=event.target.closest("[data-discovery-feedback]");if(discoveryFeedback){discoveryFeedback.disabled=true;try{await api(`api/automations/discoveries/${encodeURIComponent(discoveryFeedback.dataset.discoveryId)}/feedback`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({feedback:discoveryFeedback.dataset.discoveryFeedback})});await loadWorkspace()}catch(error){alert(`Learning feedback failed: ${error.message||error}`);discoveryFeedback.disabled=false}return}
    const edit=event.target.closest("[data-auto-edit]");if(edit){const item=state.automations.find(value=>value.id===edit.dataset.autoEdit);if(item&&confirmEditorReplacement("open another automation"))fillEditor(item);return}
    const duplicate=event.target.closest("[data-auto-duplicate]");if(duplicate){const item=state.automations.find(value=>value.id===duplicate.dataset.autoDuplicate);if(!item||!confirmEditorReplacement("duplicate another automation"))return;const copy=cloneEditorValue(item);copy.id="";copy.name=`${item.name||"Automation"} copy`;copy.enabled=false;copy.review_required=true;fillEditor(copy);markEditorAsUnsaved();$("automation-studio-state").textContent="Independent disabled copy ready. Review and save when complete.";return}
    const activateDraft=event.target.closest("[data-auto-activate]");if(activateDraft){const item=state.automations.find(value=>value.id===activateDraft.dataset.autoActivate),verb=activateDraft.dataset.autoActivationLabel||"Enable",trigger=`${item?.trigger_entity||""} ${(item?.trigger_operator||"").replaceAll("_"," ")} ${item?.trigger_value||""}`.trim(),action=item?.branches?.length?`${item.branches.length} first-match branches`:item?.action_service&&item?.action_entity?`${item.action_service} → ${item.action_entity}`:"no device action";if(!item||!confirm(`${verb} ${item.name}?\n\nWhen: ${trigger}\nAction: ${action}\nAuthority: ${authorityLabel(item.execution_policy)}\nCooldown: ${item.cooldown_minutes} minutes\n\nLive evaluation begins immediately.`))return;activateDraft.disabled=true;try{await api(`api/automations/${encodeURIComponent(item.id)}/activate`,{method:"POST"});await loadWorkspace()}catch(error){alert(`Activation failed: ${error.message||error}`);activateDraft.disabled=false}return}
    const pause=event.target.closest("[data-auto-pause]");if(pause){const item=state.automations.find(value=>value.id===pause.dataset.autoPause);if(!item||!confirm(`Pause ${item.name}?\n\nLive evaluation and new actions will stop immediately. The rule and its history will be preserved.`))return;pause.disabled=true;try{await api(`api/automations/${encodeURIComponent(item.id)}/pause`,{method:"POST"});await loadWorkspace()}catch(error){alert(`Pause failed: ${error.message||error}`);pause.disabled=false}return}
    const forgetMemory=event.target.closest("[data-automation-memory-forget]");if(forgetMemory){if(!confirm("Forget this automation entity mapping? Existing rules will not be changed."))return;await api(`api/automations/entity-memory/${encodeURIComponent(forgetMemory.dataset.automationMemoryForget)}`,{method:"DELETE"});await loadWorkspace();return}
    const resetLearning=event.target.closest("[data-auto-reset-learning]");if(resetLearning){if(!confirm("Reset learned feedback for this automation? Its configured rule and episode history will remain."))return;resetLearning.disabled=true;try{await api(`api/automations/${encodeURIComponent(resetLearning.dataset.autoResetLearning)}/feedback`,{method:"DELETE"});await loadWorkspace()}catch(error){alert(`Learning reset failed: ${error.message||error}`);resetLearning.disabled=false}return}
    const recover=event.target.closest("[data-auto-recover]");if(recover){if(!confirm("Reset this automation's failure circuit? Previous failures remain in its audit history."))return;recover.disabled=true;try{await api(`api/automations/${encodeURIComponent(recover.dataset.autoRecover)}/recover`,{method:"POST"});await loadWorkspace()}catch(error){alert(`Recovery reset failed: ${error.message||error}`);recover.disabled=false}return}
    const remove=event.target.closest("[data-auto-delete]");if(remove){if(!confirm("Delete this automation draft?"))return;await api(`api/automations/${encodeURIComponent(remove.dataset.autoDelete)}`,{method:"DELETE"});await loadWorkspace()}
  });

  $("automation-chat-builder-form").addEventListener("submit",event=>{
    event.preventDefault();const request=$("automation-chat-request").value.trim();if(!request)return;
    const chatTab=document.getElementById("chat-tab"),chatInput=document.getElementById("message"),chatForm=document.getElementById("chat-form");
    if(!chatTab||!chatInput||!chatForm){$("automation-chat-builder-status").textContent="Chat is unavailable.";return}
    chatTab.click();chatInput.value=request;chatInput.dispatchEvent(new Event("input",{bubbles:true}));chatForm.requestSubmit();
  });

  function automationRequestBody(){
    const actionData=JSON.parse($("automation-action-data").value||"{}");if(!actionData||Array.isArray(actionData)||typeof actionData!=="object")throw new Error("Action data must be a JSON object");
    const body={name:$("automation-name").value.trim(),objective:$("automation-objective").value.trim(),presence_entity:$("automation-presence").value.trim(),signal_entities:$("automation-signals").value.split(/[,\n]/).map(v=>v.trim()).filter(Boolean),trigger_entity:$("automation-trigger-entity").value.trim(),trigger_operator:$("automation-trigger-operator").value,trigger_value:$("automation-trigger-value").value.trim(),trigger_for_seconds:Number($("automation-trigger-for").value||0),enabled:$("automation-enabled").checked,context_notes:$("automation-context-notes").value.trim(),proposal_template:$("automation-proposal").value.trim(),action_entity:$("automation-action-entity").value.trim(),action_service:$("automation-action-service").value.trim(),action_service_data:actionData,cooldown_minutes:Number($("automation-cooldown").value),confidence_threshold:Number($("automation-confidence").value),risk_level:$("automation-risk").value,execution_policy:$("automation-execution-policy").value,delivery_voice:$("automation-delivery-voice").checked,delivery_notification_center:$("automation-delivery-center").checked,delivery_ha_push:$("automation-delivery-push").checked,notify_on_action:$("automation-notify-action").checked,reversible_only:$("automation-reversible-only").checked,max_actions_per_hour:Number($("automation-max-actions").value)};
    body.suggestion_timeout_minutes=Number($("automation-suggestion-timeout").value||30);body.failure_limit=Number($("automation-failure-limit").value||3);body.failure_window_minutes=Number($("automation-failure-window").value||60);body.reoffer_delta=Number($("automation-reoffer-delta").value||0);body.reset_delta=Number($("automation-reset-delta").value||0);const workflow=editorSnapshot();if(workflow.actions.length&&workflow.actions[0].entity_id===body.action_entity)workflow.actions[0].service_data=actionData;Object.assign(body,{triggers:workflow.triggers,trigger_mode:workflow.trigger_mode,conditions:workflow.conditions,condition_mode:workflow.condition_mode,actions:workflow.actions,branches:workflow.branches});return body;
  }

  function renderTestTrace(result){
    const root=$("automation-studio-test-results");root.hidden=false;root.innerHTML=(result.trace||[]).map(step=>`<article class="automation-studio-test-step" data-status="${esc(step.status)}"><strong>${esc(step.title)} · ${esc(step.status)}</strong><small>${esc(step.detail)}</small></article>`).join("");
    for(const node of $("automation-flow-preview").querySelectorAll("[data-flow-kind]")){node.classList.remove("is-test-pass","is-test-fail","is-test-waiting");const kind=node.dataset.flowKind==="branch-action"?"action":node.dataset.flowKind==="branch-condition"?"decision":node.dataset.flowKind,step=(result.trace||[]).find(item=>item.kind===kind);if(step&&["pass","fail","waiting"].includes(step.status))node.classList.add(`is-test-${step.status}`)}
  }

  $("automation-draft-form").addEventListener("submit",async event=>{
    event.preventDefault();const id=$("automation-edit-id").value;const status=$("automation-draft-state"),studioStatus=$("automation-studio-state");status.textContent="Saving…";studioStatus.textContent="Saving…";
    let body;try{body=automationRequestBody()}catch(error){status.textContent=`Action data must be valid JSON: ${error.message||error}`;studioStatus.textContent=status.textContent;return}
    try{await api(id?`api/automations/${encodeURIComponent(id)}`:"api/automations",{method:id?"PUT":"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});clearEditor();studioStatus.textContent="Draft saved.";await loadWorkspace();showLibraryView("saved")}catch(error){status.textContent=`Save failed: ${error.message||error}`;studioStatus.textContent=status.textContent}
  });
  $("automation-cancel-edit").addEventListener("click",()=>{if(confirmEditorReplacement("cancel editing"))clearEditor()});
  $("automation-draft-form").addEventListener("input",()=>{renderEditorFlow();scheduleEditorHistory()});
  $("automation-draft-form").addEventListener("change",()=>{renderEditorFlow();scheduleEditorHistory()});
  $("automation-studio-undo").addEventListener("click",undoEditor);
  $("automation-studio-redo").addEventListener("click",redoEditor);
  $("automation-studio-new").addEventListener("click",()=>{if(!confirmEditorReplacement("start a new flow"))return;$("automation-studio-state").textContent="";clearEditor()});
  $("automation-studio-test").addEventListener("click",async()=>{const status=$("automation-studio-state"),results=$("automation-studio-test-results"),issues=renderEditorValidation();if(issues.length){focusEditorIssue(issues[0]);status.textContent=`Review ${issues.length} incomplete item${issues.length===1?"":"s"} before testing.`;return}status.textContent="Testing safely…";try{const result=await api("api/automations/test-flow",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(automationRequestBody())});renderTestTrace(result);status.textContent=`Dry run: ${String(result.status||"complete").replaceAll("_"," ")} · 0 actions executed`}catch(error){results.hidden=true;status.textContent=`Test failed: ${error.message||error}`}});
  $("automation-studio-save").addEventListener("click",()=>{const issues=renderEditorValidation();if(issues.length){focusEditorIssue(issues[0]);$("automation-draft-state").textContent=`Review ${issues.length} incomplete item${issues.length===1?"":"s"} before saving.`;$("automation-studio-state").textContent=$("automation-draft-state").textContent;return}$("automation-draft-form").requestSubmit()});
  $("automation-studio-advanced").addEventListener("click",()=>{const advanced=document.querySelector(".automation-advanced");advanced?.setAttribute("open","");advanced?.scrollIntoView({behavior:"smooth",block:"start"})});
  function clearFlowDropTarget(){for(const card of $("automation-flow-preview").querySelectorAll(".is-drop-before,.is-drop-after"))card.classList.remove("is-drop-before","is-drop-after");for(const lane of $("automation-flow-preview").querySelectorAll(".is-branch-drop-target"))lane.classList.remove("is-branch-drop-target");$("automation-studio-canvas").classList.remove("is-drop-target")}
  function flowDropPosition(event,sourceKind=""){
    const lane=event.target.closest?.("[data-flow-branch-drop]"),conditionLane=event.target.closest?.("[data-flow-branch-condition-drop]"),actionLane=event.target.closest?.("[data-flow-branch-action-drop]"),branchCondition=event.target.closest?.('[data-flow-kind="branch-condition"]'),branchAction=event.target.closest?.('[data-flow-kind="branch-action"]'),activeKind=sourceKind||draggedFlowCard?.kind,movingCondition=draggedStudioNode==="context"||activeKind==="branch-condition",movingAction=draggedStudioNode==="action"||["action","branch-action"].includes(activeKind);
    if(lane&&movingCondition){const branchIndex=Number(conditionLane?.dataset.flowBranchConditionDrop??lane.dataset.flowBranchDrop),targetLane=conditionLane||lane;if(branchCondition){const rect=branchCondition.getBoundingClientRect(),after=event.clientY>rect.top+rect.height/2;return {kind:"branch-condition",branchIndex,index:Number(branchCondition.dataset.flowItemIndex)+(after?1:0),card:branchCondition,lane:targetLane,after}}return {kind:"branch-condition",branchIndex,index:workflowDraft.branches[branchIndex]?.conditions?.length||0,lane:targetLane,after:true}}
    if(lane&&movingAction){const branchIndex=Number(actionLane?.dataset.flowBranchActionDrop??lane.dataset.flowBranchDrop),targetLane=actionLane||lane;if(branchAction){const rect=branchAction.getBoundingClientRect(),after=event.clientY>rect.top+rect.height/2;return {kind:"branch-action",branchIndex,index:Number(branchAction.dataset.flowItemIndex)+(after?1:0),card:branchAction,lane:targetLane,after}}return {kind:"branch-action",branchIndex,index:workflowDraft.branches[branchIndex]?.actions?.length||0,lane:targetLane,after:true}}
    const card=event.target.closest?.("[data-flow-kind]");if(!card)return null;const rect=card.getBoundingClientRect(),after=event.clientX>rect.left+rect.width/2;return {kind:card.dataset.flowKind,index:Number(card.dataset.flowIndex)+(after?1:0),card,after}
  }
  $("automation-studio-canvas").addEventListener("dragover",event=>{event.preventDefault();clearFlowDropTarget();event.currentTarget.classList.add("is-drop-target");const target=flowDropPosition(event);if(["branch-action","branch-condition"].includes(target?.kind))target.lane.classList.add("is-branch-drop-target");else if(target&&(draggedFlowCard?.kind===target.kind||draggedStudioNode===target.kind))target.card.classList.add(target.after?"is-drop-after":"is-drop-before")});
  $("automation-studio-canvas").addEventListener("dragleave",event=>{if(!event.currentTarget.contains(event.relatedTarget))clearFlowDropTarget()});
  $("automation-studio-canvas").addEventListener("drop",event=>{event.preventDefault();let transferred=null;try{transferred=JSON.parse(event.dataTransfer?.getData("application/x-zbrano-flow-card")||"null")}catch(_error){}const source=draggedFlowCard||transferred,target=flowDropPosition(event,source?.kind),kind=event.dataTransfer?.getData("text/studio-node")||draggedStudioNode;clearFlowDropTarget();draggedStudioNode="";draggedFlowCard=null;if(source){if(target?.kind==="branch-action"&&["action","branch-action"].includes(source.kind))moveActionToBranch(source,target);else if(target?.kind==="branch-condition"&&source.kind==="branch-condition")moveBranchCondition(source,target);else if(target&&source.kind===target.kind)moveFlowCard(source.kind,source.index,target.index);else $("automation-studio-state").textContent="Move cards within the same flow stage or into a decision branch.";return}if(kind==="action"&&target?.kind==="branch-action")addBranchAction(target.branchIndex,target.index);else if(kind==="context"&&target?.kind==="branch-condition")addBranchCondition(target.branchIndex,target.index);else addStudioBlock(kind,target&&target.kind===kind?target.index:null)});
  $("automation-flow-preview").addEventListener("change",event=>{const triggerLogic=event.target.closest("[data-trigger-logic]"),branchLogic=event.target.closest("[data-branch-condition-logic]");if(triggerLogic)workflowDraft.trigger_mode=triggerLogic.value==="all"?"all":"any";else if(branchLogic){const branch=workflowDraft.branches[Number(branchLogic.dataset.flowBranchIndex)];if(!branch)return;branch.condition_mode=branchLogic.value==="any"?"any":"all"}else return;renderStudioInspector();renderEditorFlow();commitEditorHistory()});
  panel.querySelector(".automation-studio-toolbox")?.addEventListener("dragstart",event=>{const block=event.target.closest("[data-studio-node]");if(!block)return;draggedStudioNode=block.dataset.studioNode;event.dataTransfer?.setData("text/studio-node",draggedStudioNode);event.dataTransfer?.setData("text/plain",draggedStudioNode);if(event.dataTransfer)event.dataTransfer.effectAllowed="copy"});
  panel.querySelector(".automation-studio-toolbox")?.addEventListener("dragend",()=>{draggedStudioNode=""});
  $("automation-flow-preview").addEventListener("dragstart",event=>{if(event.target.closest(".automation-flow-card-actions")){event.preventDefault();return}const card=event.target.closest("[data-flow-kind][draggable=true]");if(!card)return;draggedFlowCard={kind:card.dataset.flowKind,index:Number(card.dataset.flowIndex),branchIndex:card.hasAttribute("data-flow-branch-index")?Number(card.dataset.flowBranchIndex):null};card.setAttribute("aria-grabbed","true");event.dataTransfer?.setData("application/x-zbrano-flow-card",JSON.stringify(draggedFlowCard));if(event.dataTransfer)event.dataTransfer.effectAllowed="move"});
  $("automation-flow-preview").addEventListener("dragend",event=>{event.target.closest("[data-flow-kind]")?.setAttribute("aria-grabbed","false");draggedFlowCard=null;clearFlowDropTarget()});
  $("automation-flow-preview").addEventListener("keydown",event=>{if(event.target.closest(".automation-flow-card-actions")||!["Enter"," "].includes(event.key))return;const block=event.target.closest("[data-flow-kind]");if(block){event.preventDefault();selectStudioNode(block.dataset.flowKind,Number(block.dataset.flowIndex),block.hasAttribute("data-flow-branch-index")?Number(block.dataset.flowBranchIndex):null)}});
  document.addEventListener("keydown",event=>{if(panel.classList.contains("hidden")||!panel.classList.contains("studio-active")||!(event.ctrlKey||event.metaKey)||event.altKey)return;const key=event.key.toLowerCase();if(key==="z"){event.preventDefault();if(event.shiftKey)redoEditor();else undoEditor()}else if(key==="y"){event.preventDefault();redoEditor()}});
  window.addEventListener("pagehide",commitEditorHistory);
  $("autonomy-settings-form").addEventListener("submit",async event=>{
    event.preventDefault();const status=$("autonomy-settings-state");status.textContent="Saving…";const mode=panel.querySelector('input[name="autonomy-mode"]:checked')?.value||"suggest_only";
    const body={operating_mode:mode,presence_entity:$("autonomy-presence-entity").value.trim(),require_presence:$("autonomy-require-presence").checked,respect_quiet_hours:$("autonomy-respect-quiet").checked,minimum_confidence:Number($("autonomy-min-confidence").value),default_cooldown_minutes:Number($("autonomy-default-cooldown").value),autonomous_risk_ceiling:$("autonomy-risk-ceiling").value,notify_after_autonomous_action:$("autonomy-notify-autonomous").checked,passive_learning_enabled:$("autonomy-passive-learning").checked};
    try{await api("api/automations/settings",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});status.textContent="Authority policy saved.";await loadWorkspace()}catch(error){status.textContent=`Save failed: ${error.message||error}`}
  });
  $("autonomy-refresh-context").addEventListener("click",loadEntityContext);

  document.addEventListener("click",event=>{const other=event.target.closest?.("#chat-tab,#entities-tab,#settings-tab,#plugins-tab,#files-tab,#calendar-tab,#developer-tab");if(other){panel.classList.add("hidden");tab.classList.remove("active")}},true);
  tab.addEventListener("click",event=>{event.preventDefault();event.stopImmediatePropagation();activate();loadWorkspace().catch(error=>{$("autonomy-context").innerHTML=`<div class="autonomy-empty">Automation workspace unavailable: ${esc(error.message||error)}</div>`})},true);
  const libraryPrefs=readLibraryPrefs();$("automation-library-filter").value=libraryPrefs.filter;$("automation-library-sort").value=libraryPrefs.sort;$("automation-library-layout").value=libraryPrefs.layout;const localDraftRecovery=readLocalEditorDraft();clearEditor();if(localDraftRecovery)recoverLocalEditorDraft(localDraftRecovery);showLibraryView(libraryPrefs.view,false);
  window.zbranoAutomationWorkspace={ready:true,load:loadWorkspace,showView};
})();
