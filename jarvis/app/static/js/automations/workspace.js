(() => {
  const tab=document.getElementById("automations-tab");
  const panel=document.getElementById("automations-panel");
  if(!tab||!panel)return;
  const $=id=>document.getElementById(id);
  for(const [id,type] of [["automation-sleep-hours-enabled","checkbox"],["automation-sleep-hours-start","time"],["automation-sleep-hours-end","time"],["automation-run-during-sleep-hours","checkbox"]]){const input=document.createElement("input");input.id=id;input.type=type;input.hidden=true;panel.append(input)}
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
  $("automation-activity-root").innerHTML=`
    <div class="automation-activity-head"><div><h3>Automation activity</h3><p>See what is watching, what needs attention, and why ZBRANO did or did not act.</p></div><button id="automation-activity-refresh" type="button">Refresh activity</button></div>
    <div class="automation-activity-metrics" aria-label="Automation health summary">
      <article><span>Watching now</span><strong id="automation-activity-watching">0</strong><small>Enabled automations</small></article>
      <article><span>Needs attention</span><strong id="automation-activity-attention">0</strong><small>Permission or recovery issue</small></article>
      <article><span>Matched in 24 hours</span><strong id="automation-activity-matched">0</strong><small>Conditions became true</small></article>
      <article><span>Actions in 24 hours</span><strong id="automation-activity-actions">0</strong><small>Tasks completed</small></article>
    </div>
    <div class="automation-activity-grid">
      <article class="autonomy-card automation-decision-card">
        <div class="autonomy-card-head"><div><h3>Why ZBRANO responded</h3><p>Every evaluation is explained in plain language, including checks that stopped safely.</p></div><span id="automation-decision-count" class="automation-state">0 records</span></div>
        <div class="automation-activity-filters">
          <label>Automation<select id="automation-activity-automation-filter"><option value="all">All automations</option></select></label>
          <label>Result<select id="automation-activity-result-filter"><option value="all">All results</option><option value="matched">Matched</option><option value="no_action">Did not act</option><option value="attention">Needs attention</option></select></label>
        </div>
        <div id="automation-decision-feed" class="autonomy-list"></div>
      </article>
      <article class="autonomy-card">
        <div class="autonomy-card-head"><div><h3>Automation health</h3><p>Current state and most recent evaluation for each saved automation.</p></div></div>
        <div id="automation-health-list" class="autonomy-list"></div>
      </article>
      <article class="autonomy-card automation-results-card">
        <div class="autonomy-card-head"><div><h3>Automation results</h3><p>Judge usefulness from visible feedback and outcomes—not a hidden AI score.</p></div><label class="automation-results-filter">Show<select id="automation-results-filter"><option value="all">All automations</option><option value="attention">Needs adjustment</option><option value="learning">Still learning</option><option value="healthy">Healthy signals</option></select></label></div>
        <div class="automation-results-summary"><span><strong id="automation-results-evaluated">0</strong> with evidence</span><span><strong id="automation-results-attention">0</strong> need adjustment</span><span><strong id="automation-results-learning">0</strong> still learning</span><span><strong id="automation-results-healthy">0</strong> healthy signals</span></div>
        <div id="automation-results-list" class="automation-results-list"></div>
      </article>
      <article class="autonomy-card automation-recovery-card">
        <div class="autonomy-card-head"><div><h3>Recovery center</h3><p>Repeated action failures pause safely. Review the cause, permissions, and retry timing before resuming.</p></div><span id="automation-recovery-paused" class="automation-state">0 paused</span></div>
        <div id="automation-recovery-list" class="automation-recovery-list"></div>
      </article>
      <article class="autonomy-card automation-system-activity"><h3>System activity</h3><p>Configuration changes, suggestions, recoveries, and action events.</p><div id="autonomy-timeline" class="autonomy-list"></div></article>
    </div>`;
  $("automation-permission-root").innerHTML=`
    <div class="automation-activity-head"><div><h3>Automation permissions</h3><p>Review exactly what each automation can read and control before you enable it.</p></div><button id="automation-permission-refresh" type="button">Check again</button></div>
    <div class="automation-permission-summary" aria-label="Automation permission summary">
      <article><span>Ready</span><strong id="automation-permission-ready">0</strong><small>Have every permission needed</small></article>
      <article><span>Need permission</span><strong id="automation-permission-attention">0</strong><small>Will stop safely until fixed</small></article>
      <article><span>Sensors read</span><strong id="automation-permission-reads">0</strong><small>Unique Home Assistant entities</small></article>
      <article><span>Devices controlled</span><strong id="automation-permission-controls">0</strong><small>Unique Home Assistant entities</small></article>
    </div>
    <div class="automation-permission-toolbar"><label>Show<select id="automation-permission-filter"><option value="all">All automations</option><option value="attention">Need permission</option><option value="ready">Ready</option></select></label><button type="button" data-permission-open-entities>Manage entity permissions</button></div>
    <div id="automation-permission-list" class="automation-permission-list"></div>`;
  const entityPickerFieldIds=new Set(["automation-trigger-entity","automation-presence","automation-signals","automation-action-entity"]);
  const studioPanels={
    details:{title:"1. Setup & safety",help:"Name this automation and choose its presence, device, and sleep-hour safety rules.",fields:[["automation-name","Automation name"],["automation-objective","What should it help with?"],["automation-require-presence","Require presence"],["automation-presence","Who must be present?"],["automation-risk","Device type"],["automation-sleep-hours-enabled","Pause during sleep hours"],["automation-sleep-hours-start","Sleep starts"],["automation-sleep-hours-end","Sleep ends"],["automation-run-during-sleep-hours","Security automation — run during sleep hours"],["automation-max-actions","Most times this may run in one hour"],["automation-reversible-only","Only allow automatic actions that can be undone"],["automation-notify-action","Tell me after it runs"],["automation-enabled","Enable automation on saving"]]},
    trigger:{title:"2. When",help:"Choose the event that should start this automation. Add more events below if needed.",fields:[["automation-trigger-kind","What kind of event?"],["automation-trigger-entity","Which device or sensor?"],["automation-trigger-operator","What should it do?"],["automation-trigger-value","Compared with what value?"],["automation-trigger-for","For how many seconds?"],["automation-trigger-at","At what time?"],["automation-trigger-weekdays","On which days?"],["automation-trigger-sun-event","Sunrise or sunset?"],["automation-trigger-sun-offset","How many minutes before or after?"],["automation-trigger-interval","How often, in minutes?"],["automation-trigger-one-time","Choose the date and time"]]},
    context:{title:"3. IF conditions",help:"Optional: add a condition. The first is IF; additional conditions connect with AND or OR.",fields:[["automation-context-notes","Notes for these conditions (optional)"]]},
    decision:{title:"5. Else if",help:"Add another path for the same When event. ZBRANO uses the first path whose checks match.",fields:[["automation-proposal","Main message from ZBRANO"],["automation-confidence","How sure should ZBRANO be?"],["automation-cooldown","Wait before offering again (minutes)"],["automation-suggestion-timeout","How long can I answer? (minutes)"],["automation-reoffer-delta","Offer again if the reading worsens by"],["automation-reset-delta","Ready for a new alert after the reading improves by"],["automation-delivery-voice","Say this message aloud"],["automation-delivery-center","Show in ZBRANO notifications"],["automation-delivery-push","Send to Home Assistant notifications"]]},
    action:{title:"4. Then",help:"Choose what ZBRANO should do and whether this path needs approval.",fields:[["automation-execution-policy","Before running these tasks"],["automation-action-entity","Which device?"],["automation-action-service","What should it do?"],["automation-action-data","Extra details (advanced)"],["automation-failure-limit","Pause after this many failed attempts"],["automation-failure-window","Count failed attempts for this many minutes"]]},
  };
  const studioStepOrder=["details","trigger","context","action","decision"];
  const studioStepNames={details:"Setup & safety",trigger:"Events",context:"IF conditions",action:"Actions",decision:"Else if"};

  function apiErrorMessage(detail,status){
    if(typeof detail==="string"&&detail.trim())return detail.trim();
    if(Array.isArray(detail)){
      const fieldNames={name:"Automation name",objective:"What should it help with?",trigger_entity:"When device or sensor",trigger_operator:"When comparison",action_entity:"Task device",action_service:"Task action",cooldown_minutes:"Wait before offering again",confidence_threshold:"How sure should ZBRANO be?",max_actions_per_hour:"Hourly action limit"};
      const messages=detail.map(issue=>{if(!issue||typeof issue!=="object")return String(issue||"").trim();const path=(issue.loc||[]).filter(part=>part!=="body"),rawField=String(path.at(-1)||""),field=fieldNames[rawField]||rawField.replaceAll("_"," ")||"Automation";return `${field}: ${String(issue.msg||"has an invalid value")}`}).filter(Boolean);
      if(messages.length)return messages.join(" · ");
    }
    if(detail&&typeof detail==="object")return String(detail.message||detail.error||"").trim()||`The automation could not be saved (HTTP ${status})`;
    return `The automation could not be saved (HTTP ${status})`;
  }

  async function api(path,options={}){
    const response=await fetch(path,{cache:"no-store",...options});
    const data=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error(apiErrorMessage(data.detail,response.status));
    return data;
  }

  function activate(){
    for(const id of ["chat-panel","entities-panel","settings-panel","plugins-panel","files-panel","contacts-panel","calendar-panel","developer-panel","automations-panel"]){document.getElementById(id)?.classList.toggle("hidden",id!=="automations-panel")}
    for(const id of ["chat-tab","entities-tab","settings-tab","plugins-tab","files-tab","calendar-tab","developer-tab","automations-tab"]){document.getElementById(id)?.classList.toggle("active",id==="automations-tab")}
  }

  function showView(name){
    for(const button of panel.querySelectorAll("[data-auto-view]")){const active=button.dataset.autoView===name;button.classList.toggle("active",active);button.setAttribute("aria-selected",String(active))}
    for(const view of panel.querySelectorAll("[data-auto-panel]")){view.classList.toggle("hidden",view.dataset.autoPanel!==name)}
    panel.classList.toggle("studio-active",name==="studio");
  }

  function readLibraryPrefs(){
    try{const value=JSON.parse(localStorage.getItem(libraryPrefsKey)||"{}");return {filter:["all","active","attention","disabled","autonomous","watch"].includes(value.filter)?value.filter:"all",sort:["recent","name_asc","name_desc","active","attention"].includes(value.sort)?value.sort:"recent"}}catch(_error){return {filter:"all",sort:"recent"}}
  }
  function persistLibraryPrefs(){
    try{localStorage.setItem(libraryPrefsKey,JSON.stringify({filter:$("automation-library-filter").value,sort:$("automation-library-sort").value}))}catch(_error){}
  }
  function showLibraryView(name,persist=true){
    showView(name==="saved"?"library":"studio");
    if(persist)persistLibraryPrefs();
  }

  function openOverviewShortcut(target){
    let destination=null;
    if(target==="drafts"){
      showView("library");
      $("automation-library-search").value="";$("automation-library-filter").value="disabled";
      persistLibraryPrefs();renderLibrary();destination=$("automation-library-filter");
    }else if(target==="suggestions"){
      showView("overview");destination=$("autonomy-suggestion-inbox");
    }
    if(destination)requestAnimationFrame(()=>{destination.scrollIntoView({behavior:"smooth",block:"center"});destination.focus({preventScroll:true})});
  }

  function modeLabel(value){return ({observe_only:"Observe only",suggest_only:"Suggest only",approval_gated:"Approval-gated",selective_autonomy:"Selective autonomy"})[value]||"Suggest only"}
  function authorityLabel(value){return ({inherit:"Protected default",observe:"Monitor silently",suggest:"Notify me",approval_required:"Ask me first",autonomous:"Do it automatically"})[value]||"Notify me"}
  function automationAuthorityLabel(item){const values=[...new Set((item.branches||[]).filter(branch=>(branch.actions||[]).length).map(branch=>branch.execution_policy||item.execution_policy||"approval_required"))];return values.length>1?"Mixed branch behavior":authorityLabel(values[0]||item.execution_policy)}
  function automationHasAutonomousPath(item){return (item.branches||[]).some(branch=>(branch.actions||[]).length&&(branch.execution_policy||item.execution_policy)==="autonomous")||(!(item.branches||[]).length&&item.execution_policy==="autonomous")}
  function riskLabel(value){return value==="informational"?"Sensor device":"Control device"}
  function normalizeExecutionPolicyForDevice(){const control=$("automation-risk").value!=="informational",allowed=control?["approval_required","autonomous"]:["suggest","observe"],field=$("automation-execution-policy");if(!allowed.includes(field.value))field.value=allowed[0];return allowed}
  function entityLabel(id){const entity=entityMap.get(id),name=String(entity?.friendly_name||"").trim();return name&&name!==id?name:id}
  function actionLabel(service){const value=String(service||"");const labels={"climate.set_temperature":"Set temperature","climate.set_hvac_mode":"Set heating or cooling mode","cover.open_cover":"Open","cover.close_cover":"Close","cover.stop_cover":"Stop","lock.lock":"Lock","lock.unlock":"Unlock","button.press":"Press","vacuum.start":"Start cleaning","vacuum.return_to_base":"Return to base","media_player.media_play":"Play","media_player.media_pause":"Pause"};if(labels[value])return labels[value];if(value.endsWith(".turn_on"))return value.startsWith("scene.")?"Activate scene":value.startsWith("script.")?"Run":"Turn on";if(value.endsWith(".turn_off"))return"Turn off";if(value.endsWith(".toggle"))return"Change power";return value?"Custom action":"Only show the message"}
  function presenceEntity(){return $("automation-require-presence")?.checked?$("automation-presence").value.trim():""}
  function entityVisual(id){const entity=entityMap.get(id)||{};return {domain:entity.domain||String(id||"").split(".",1)[0],deviceClass:entity.device_class||entity.attributes?.device_class||"",unit:entity.unit_of_measurement||entity.unit||entity.attributes?.unit_of_measurement||""}}
  function flowElement(item){return window.zbranoAutomationFlow?.create(item,entityLabel,entityVisual)||null}
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
  function inspectorFields(panelConfig){
    if(selectedStudioNode==="details"){
      const sleeping=$("automation-sleep-hours-enabled").checked;
      return panelConfig.fields.filter(([id])=>sleeping||!["automation-sleep-hours-start","automation-sleep-hours-end","automation-run-during-sleep-hours"].includes(id))
    }
    if(selectedStudioNode==="action"&&!$("automation-action-entity").value.trim()&&!$("automation-action-service").value.trim())return panelConfig.fields.filter(([id])=>!["automation-action-entity","automation-action-service","automation-action-data"].includes(id));
    if(selectedStudioNode==="decision"){
      const hasBranches=workflowDraft.branches.length>0;
      return panelConfig.fields.filter(([id])=>!(hasBranches&&["automation-proposal","automation-delivery-voice","automation-delivery-center","automation-delivery-push"].includes(id)));
    }
    if(selectedStudioNode!=="trigger")return panelConfig.fields;
    if(selectedFlowCard.kind==="trigger"&&selectedFlowCard.index>0)return [];
    const kind=$("automation-trigger-kind").value||"entity",operator=$("automation-trigger-operator").value||"changes_to";
    const fields={
      entity:new Set(["automation-trigger-entity","automation-trigger-operator","automation-trigger-for"]),
      time:new Set(["automation-trigger-at","automation-trigger-weekdays"]),
      sun:new Set(["automation-trigger-sun-event","automation-trigger-sun-offset","automation-trigger-weekdays"]),
      interval:new Set(["automation-trigger-interval"]),
      one_time:new Set(["automation-trigger-one-time"]),
    }[kind]||new Set();
    const preset=triggerPreset(primaryTriggerValue());
    if(kind==="entity"&&preset.startsWith("power_"))fields.delete("automation-trigger-operator");
    else if(kind==="entity"&&operator!=="any_change")fields.add("automation-trigger-value");
    return panelConfig.fields.filter(([id])=>fields.has(id));
  }
  function renderStudioInspector(){
    window.zbranoEntitySearch?.close();
    const panelConfig=studioPanels[selectedStudioNode]||studioPanels.trigger;
    $("automation-studio-inspector-title").textContent=panelConfig.title;
    $("automation-studio-inspector-help").textContent=panelConfig.help;
    const root=$("automation-studio-inspector-fields");root.replaceChildren();
    const allowedPolicies=selectedStudioNode==="action"?["approval_required","autonomous"]:null;
    if(selectedStudioNode==="trigger")renderTriggerPresetPicker(root);
    if(selectedStudioNode==="action")renderActionTaskPalette(root);
    const groupedIds=selectedStudioNode==="decision"?new Set(["automation-confidence","automation-cooldown","automation-suggestion-timeout","automation-reoffer-delta","automation-reset-delta"]):selectedStudioNode==="action"?new Set(["automation-action-data","automation-failure-limit","automation-failure-window"]):new Set();
    let optionalGroup=null,optionalFields=null;
    if(groupedIds.size){optionalGroup=document.createElement("details");optionalGroup.className="automation-inspector-more";const summary=document.createElement("summary");summary.textContent=selectedStudioNode==="decision"?"Fine-tune timing and confidence":"Safety limits and advanced details";optionalFields=document.createElement("div");optionalFields.className="automation-inspector-more-fields";optionalGroup.append(summary,optionalFields)}
    const controlDevice=$("automation-risk").value!=="informational";
    const actionOnlyFields=new Set(["automation-max-actions","automation-notify-action"]);
    for(const [id,labelText] of inspectorFields(panelConfig)){
      if(selectedStudioNode==="details"&&((actionOnlyFields.has(id)&&!controlDevice)||(id==="automation-reversible-only"&&!controlDevice)))continue;
      const source=$(id);if(!source)continue;
      if(selectedStudioNode==="action"&&id==="automation-execution-policy"){
        const guide=document.createElement("div");guide.className="automation-rule-safety-guide";guide.innerHTML='<span class="automation-rule-safety-icon" aria-hidden="true">&#128737;</span><div><strong>Authority for this path</strong><small>Choose whether this path asks before its tasks or runs them automatically. Built-in protection can still require approval when an action is unsafe.</small></div>';root.append(guide);
      }
      const displayLabel=id==="automation-trigger-entity"&&triggerPreset(primaryTriggerValue()).startsWith("power_")?"Power device":labelText,label=document.createElement("label"),control=source.cloneNode(true);
      control.id=`studio-${id}`;control.removeAttribute("required");control.removeAttribute("hidden");
      if(id==="automation-execution-policy")for(const option of [...control.options])if(!allowedPolicies.includes(option.value))option.remove();
      if(id==="automation-presence")control.disabled=!$("automation-require-presence").checked;
      if(entityPickerFieldIds.has(id))control.dataset.entityPicker="true";
      if(id==="automation-signals")control.dataset.entityPickerMultiple="true";
      if(source.type==="checkbox"){control.checked=source.checked;label.className="is-check";label.append(control,document.createTextNode(displayLabel))}
      else{control.value=source.value;const caption=document.createElement("span");caption.textContent=displayLabel;label.append(caption,control)}
      const synchronize=()=>{if(source.type==="checkbox")source.checked=control.checked;else source.value=control.value;source.dispatchEvent(new Event("input",{bubbles:true}));if(id==="automation-trigger-kind"||id==="automation-trigger-operator"||id==="automation-execution-policy"||id==="automation-risk"||id==="automation-require-presence"||id==="automation-sleep-hours-enabled")renderStudioInspector()};
      control.addEventListener("input",synchronize);control.addEventListener("change",synchronize);(groupedIds.has(id)?optionalFields:root).append(label);
    }
    if(optionalGroup)root.append(optionalGroup);
    renderWorkflowInspector(root);
    for(const input of root.querySelectorAll('input[data-entity-picker="true"],input[list="automation-entity-options"]'))window.zbranoEntitySearch?.attach(input);
    updateStudioNavigation();
  }

  function updateStudioNavigation(){
    const index=Math.max(0,studioStepOrder.indexOf(selectedStudioNode)),step=index+1,progress=$("automation-studio-progressbar"),back=$("automation-studio-step-back"),next=$("automation-studio-step-next");
    $("automation-studio-current-step").textContent=`Step ${step} of ${studioStepOrder.length}`;
    progress.setAttribute("aria-valuenow",String(step));progress.querySelector("i").style.width=`${step/studioStepOrder.length*100}%`;
    back.disabled=index===0;
    next.textContent=index===studioStepOrder.length-1?"Review and finish":`Next: ${studioStepNames[studioStepOrder[index+1]]}`;
  }

  function moveThroughStudio(direction){
    const index=Math.max(0,studioStepOrder.indexOf(selectedStudioNode));
    if(direction<0){selectStudioNode(studioStepOrder[Math.max(0,index-1)]);requestAnimationFrame(()=>$("automation-studio-inspector-fields").querySelector("input,select,textarea")?.focus());return}
    const currentIssues=editorValidationIssues().filter(issue=>issue.kind===selectedStudioNode);
    if(currentIssues.length){focusEditorIssue(currentIssues[0]);$("automation-studio-state").textContent=`Complete this step first: ${currentIssues[0].message}.`;return}
    if(index<studioStepOrder.length-1){selectStudioNode(studioStepOrder[index+1]);requestAnimationFrame(()=>$("automation-studio-inspector-fields").querySelector("input,select,textarea,button")?.focus());return}
    const issues=renderEditorValidation();
    if(issues.length){focusEditorIssue(issues[0]);$("automation-studio-state").textContent=`Almost ready — complete ${issues.length} highlighted item${issues.length===1?"":"s"}.`;return}
    $("automation-studio-state").textContent="Everything required is ready. Try it safely, or save the automation.";$("automation-studio-test").focus();$("automation-studio-test").scrollIntoView({behavior:"smooth",block:"nearest"});
  }

  function workflowOperatorOptions(selected,trigger=false){const labels={any_change:"Changes at all",changes_to:"Becomes →",equals:"Is =",not_equals:"Is not ≠",above:"Is above >",below:"Is below <"};return (trigger?["any_change","changes_to","equals","not_equals","above","below"]:["equals","not_equals","above","below"]).map(value=>`<option value="${value}"${value===selected?" selected":""}>${labels[value]}</option>`).join("")}
  const weekdayNames=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
  function parseWeekdays(value){return [...new Set(String(value||"").split(/[,\s]+/).map(part=>weekdayNames.findIndex(day=>day.toLowerCase()===part.slice(0,3).toLowerCase())).filter(index=>index>=0))]}
  function formatWeekdays(values){return (values||[]).map(value=>weekdayNames[Number(value)]).filter(Boolean).join(", ")}
  function triggerPreset(item={}){
    const kind=item.kind||"entity";
    if(kind!=="entity")return kind;
    const value=String(item.value||"").toLowerCase(),operator=item.operator||"changes_to",isPowerState=["changes_to","equals"].includes(operator)&&["on","off"].includes(value);
    if(isPowerState&&value==="on")return"power_on";
    if(isPowerState&&value==="off")return"power_off";
    return"sensor";
  }
  function selectedTriggerValue(){return selectedFlowCard.kind==="trigger"&&selectedFlowCard.index>0?workflowDraft.triggers[selectedFlowCard.index-1]:primaryTriggerValue()}
  function applyTriggerPreset(preset){
    const current=cloneEditorValue(selectedTriggerValue()||{}),wasPower=triggerPreset(current).startsWith("power_");
    if(preset==="power_on"||preset==="power_off")Object.assign(current,{kind:"entity",operator:"changes_to",value:preset==="power_on"?"on":"off"});
    else if(preset==="sensor"){const resetComparison=wasPower||(current.kind||"entity")!=="entity";Object.assign(current,{kind:"entity",operator:resetComparison?"above":current.operator||"above",value:resetComparison?"":current.value||""})}
    else if(["time","sun","interval","one_time"].includes(preset))current.kind=preset;
    if(selectedFlowCard.kind==="trigger"&&selectedFlowCard.index>0)workflowDraft.triggers[selectedFlowCard.index-1]=current;else writePrimaryTrigger(current);
    renderStudioInspector();renderEditorFlow();commitEditorHistory();
  }
  function addToolbarTrigger(preset){
    const primary=primaryTriggerValue(),blank=(primary.kind||"entity")==="entity"&&!primary.entity_id&&!primary.value&&!workflowDraft.triggers.length;
    const item={kind:"entity",entity_id:"",operator:preset==="sensor"?"above":"changes_to",value:preset==="power_on"?"on":preset==="power_off"?"off":"",for_seconds:0,weekdays:[],at:"",sun_event:"sunrise",offset_minutes:0,interval_minutes:5,one_time_at:""};
    if(["time","sun","interval","one_time"].includes(preset))item.kind=preset;
    if(blank){writePrimaryTrigger(item);selectedFlowCard={kind:"trigger",index:0,branchIndex:null}}else{if(workflowDraft.triggers.length>=9){$("automation-studio-state").textContent="A flow supports up to 10 events.";return}workflowDraft.triggers.push(item);selectedFlowCard={kind:"trigger",index:workflowDraft.triggers.length,branchIndex:null}}
    selectedStudioNode="trigger";renderStudioInspector();renderEditorFlow();commitEditorHistory();$("automation-studio-state").textContent="Event block added. Choose its device or timing.";
  }
  function addToolbarCondition(template){
    const branchIndex=selectedFlowCard.kind==="decision"?selectedFlowCard.index:["branch-condition","branch-action"].includes(selectedFlowCard.kind)?selectedFlowCard.branchIndex:null;
    if(Number.isInteger(branchIndex)&&workflowDraft.branches[branchIndex]){addBranchCondition(branchIndex,workflowDraft.branches[branchIndex].conditions.length,template);return}
    if(workflowDraft.conditions.length>=20){$("automation-studio-state").textContent="A flow supports up to 20 conditions.";return}workflowDraft.conditions.push(newBranchCondition(template));const offset=(presenceEntity()?1:0)+$("automation-signals").value.split(/[,\n]/).map(value=>value.trim()).filter(Boolean).length;selectedStudioNode="context";selectedFlowCard={kind:"context",index:offset+workflowDraft.conditions.length-1,branchIndex:null};renderStudioInspector();renderEditorFlow();commitEditorHistory();$("automation-studio-state").textContent="IF condition added. Use AND / OR when you add another condition.";
  }
  function addToolbarAction(template){
    const branchIndex=selectedFlowCard.kind==="decision"?selectedFlowCard.index:["branch-condition","branch-action"].includes(selectedFlowCard.kind)?selectedFlowCard.branchIndex:null;
    if(Number.isInteger(branchIndex)&&workflowDraft.branches[branchIndex]){addBranchActionTemplate(branchIndex,template,workflowDraft.branches[branchIndex].actions.length);return}
    if(workflowDraft.actions.length>=19){$("automation-studio-state").textContent="A flow supports up to 20 actions.";return}workflowDraft.actions.push(newActionTask(template));selectedStudioNode="action";selectedFlowCard={kind:"action",index:visualFlowItems("action").length-1,branchIndex:null};renderStudioInspector();renderEditorFlow();commitEditorHistory();$("automation-studio-state").textContent="THEN action added. Complete its settings.";
  }
  function renderTriggerPresetPicker(root){
    const item=selectedTriggerValue()||{},active=triggerPreset(item),section=document.createElement("section");section.className="automation-trigger-palette";
    const choices=[["sensor","&#128202;","Sensor reading","Temperature, motion, humidity or another value"],["power_on","&#9211;","Power turns on","A switch, light or device becomes on"],["power_off","&#9711;","Power turns off","A switch, light or device becomes off"],["time","&#9201;","Time","At a chosen time"],["sun","&#9728;","Sun","At sunrise or sunset"],["interval","&#8635;","Repeat","Every few minutes"],["one_time","&#128197;","One time","At one date and time"]];
    section.innerHTML=`<div class="automation-task-palette-head"><strong>What does this When block watch?</strong><small>Choose the card that matches the event.</small></div><div class="automation-trigger-palette-grid">${choices.map(([key,icon,title,detail])=>`<button type="button" data-trigger-preset="${key}" aria-pressed="${key===active}"><span aria-hidden="true">${icon}</span><strong>${title}</strong><small>${detail}</small></button>`).join("")}</div>`;
    section.addEventListener("click",event=>{const button=event.target.closest("[data-trigger-preset]");if(button)applyTriggerPreset(button.dataset.triggerPreset)});root.append(section);
  }
  function friendlyTriggerStepHtml(item,attributes,includeType=true){
    const kind=item.kind||"entity",attr=field=>`${attributes} data-trigger-field="${field}"`;
    const labelled=(label,control)=>`<label><span>${label}</span>${control}</label>`;
    const type=includeType?labelled("Start when",`<select ${attr("kind")}><option value="entity"${kind==="entity"?" selected":""}>A device or sensor changes</option><option value="time"${kind==="time"?" selected":""}>It is a specific time</option><option value="sun"${kind==="sun"?" selected":""}>The sun rises or sets</option><option value="interval"${kind==="interval"?" selected":""}>A set time passes</option><option value="one_time"${kind==="one_time"?" selected":""}>A one-time date arrives</option></select>`):"";
    if(kind==="entity"){
      const preset=triggerPreset(item),powerState=preset==="power_on"?"on":"off";
      if(preset.startsWith("power_"))return `${type}${labelled("Power device",`<input ${attr("entity_id")} list="automation-entity-options" value="${esc(item.entity_id||"")}" placeholder="Choose a switch, light or powered device">`)}${labelled(`Keep it ${powerState} for (seconds)`,`<input ${attr("for_seconds")} type="number" min="0" max="86400" value="${Number(item.for_seconds||0)}">`)}`;
      const comparison=item.operator==="any_change"?"":labelled("Compared with",`<input ${attr("value")} value="${esc(item.value||"")}" placeholder="For example: 26, home, off">`);
      return `${type}${labelled("Device or sensor",`<input ${attr("entity_id")} list="automation-entity-options" value="${esc(item.entity_id||"")}" placeholder="Choose a device or sensor">`)}${labelled("Change to watch for",`<select ${attr("operator")}>${workflowOperatorOptions(item.operator,true)}</select>`)}${comparison}${labelled("Keep this state for (seconds)",`<input ${attr("for_seconds")} type="number" min="0" max="86400" value="${Number(item.for_seconds||0)}">`)}`;
    }
    if(kind==="time")return `${type}${labelled("Time",`<input ${attr("at")} type="time" value="${esc(item.at||"")}">`)}${labelled("Days",`<input ${attr("weekdays")} value="${esc(formatWeekdays(item.weekdays))}" placeholder="Mon, Tue">`)}`;
    if(kind==="sun")return `${type}${labelled("Sun event",`<select ${attr("sun_event")}><option value="sunrise"${item.sun_event!=="sunset"?" selected":""}>Sunrise</option><option value="sunset"${item.sun_event==="sunset"?" selected":""}>Sunset</option></select>`)}${labelled("Move it by (minutes)",`<input ${attr("offset_minutes")} type="number" min="-180" max="180" value="${Number(item.offset_minutes||0)}">`)}${labelled("Days",`<input ${attr("weekdays")} value="${esc(formatWeekdays(item.weekdays))}" placeholder="Mon, Tue">`)}`;
    if(kind==="interval")return `${type}${labelled("Repeat every (minutes)",`<input ${attr("interval_minutes")} type="number" min="1" max="10080" value="${Number(item.interval_minutes||5)}">`)}`;
    return `${type}${labelled("Date and time",`<input ${attr("one_time_at")} type="datetime-local" value="${esc(item.one_time_at||"")}">`)}`;
  }
  function triggerStepHtml(item,attributes){const kind=item.kind||"entity",attr=field=>`${attributes} data-trigger-field="${field}"`;return `<select ${attr("kind")}><option value="entity"${kind==="entity"?" selected":""}>Entity state</option><option value="time"${kind==="time"?" selected":""}>Specific time</option><option value="sun"${kind==="sun"?" selected":""}>Sunrise / sunset</option><option value="interval"${kind==="interval"?" selected":""}>Interval</option><option value="one_time"${kind==="one_time"?" selected":""}>One time</option></select>${kind==="entity"?`<input ${attr("entity_id")} list="automation-entity-options" value="${esc(item.entity_id||"")}" placeholder="sensor.entity"><select ${attr("operator")}>${workflowOperatorOptions(item.operator,true)}</select><input ${attr("value")} value="${esc(item.value||"")}" placeholder="value"><input ${attr("for_seconds")} type="number" min="0" max="86400" value="${Number(item.for_seconds||0)}">`:kind==="time"?`<input ${attr("at")} type="time" value="${esc(item.at||"")}"><input ${attr("weekdays")} value="${esc(formatWeekdays(item.weekdays))}" placeholder="Mon, Tue">`:kind==="sun"?`<select ${attr("sun_event")}><option value="sunrise"${item.sun_event!=="sunset"?" selected":""}>Sunrise</option><option value="sunset"${item.sun_event==="sunset"?" selected":""}>Sunset</option></select><input ${attr("offset_minutes")} type="number" min="-180" max="180" value="${Number(item.offset_minutes||0)}"><input ${attr("weekdays")} value="${esc(formatWeekdays(item.weekdays))}" placeholder="Mon, Tue">`:kind==="interval"?`<input ${attr("interval_minutes")} type="number" min="1" max="10080" value="${Number(item.interval_minutes||5)}">`:`<input ${attr("one_time_at")} type="datetime-local" value="${esc(item.one_time_at||"")}">`}`}
  function conditionStepHtml(item,attributes){
    const kind=item.kind||"entity",attr=field=>`${attributes} data-condition-field="${field}"`;
    const labelled=(label,control)=>`<label><span>${label}</span>${control}</label>`;
    const advanced=(summary,controls,open=false)=>`<details class="automation-condition-advanced automation-inspector-more"${open?" open":""}><summary>${summary}</summary><div class="automation-inspector-more-fields">${controls}</div></details>`;
    const type=labelled("Check",`<select ${attr("kind")}><option value="entity"${kind==="entity"?" selected":""}>Device or sensor state</option><option value="entity_compare"${kind==="entity_compare"?" selected":""}>Compare two device values</option><option value="time_window"${kind==="time_window"?" selected":""}>The time is within a range</option><option value="weekday"${kind==="weekday"?" selected":""}>Today is one of these days</option><option value="sun"${kind==="sun"?" selected":""}>The sun is up or down</option></select>`);
    if(kind==="entity"){const attribute=labelled("Device attribute",`<input ${attr("attribute")} list="automation-attribute-options" value="${esc(item.attribute||"")}" placeholder="For example: temperature">`);return `${type}${labelled("Device or sensor",`<input ${attr("entity_id")} list="automation-entity-options" value="${esc(item.entity_id||"")}" placeholder="Choose a device or sensor">`)}${labelled("Must be",`<select ${attr("operator")}>${workflowOperatorOptions(item.operator)}</select>`)}${labelled("Compared with",`<input ${attr("value")} value="${esc(item.value||"")}" placeholder="For example: home, off, cooling, 26">`)}${labelled("Keep true for (seconds)",`<input ${attr("for_seconds")} type="number" min="0" max="86400" value="${Number(item.for_seconds||0)}">`)}${advanced("Use a specific device attribute",attribute,Boolean(item.attribute))}`}
    if(kind==="entity_compare"){const attributes=labelled("First device attribute",`<input ${attr("attribute")} list="automation-attribute-options" value="${esc(item.attribute||"")}" placeholder="For example: temperature">`)+labelled("Other device attribute",`<input ${attr("compare_attribute")} list="automation-attribute-options" value="${esc(item.compare_attribute||"")}" placeholder="For example: temperature">`);return `${type}${labelled("First device or sensor",`<input ${attr("entity_id")} list="automation-entity-options" value="${esc(item.entity_id||"")}" placeholder="Choose the value to test">`)}${labelled("Must be",`<select ${attr("operator")}>${workflowOperatorOptions(item.operator)}</select>`)}${labelled("Other device or sensor",`<input ${attr("compare_entity_id")} list="automation-entity-options" value="${esc(item.compare_entity_id||"")}" placeholder="Choose the comparison device">`)}${labelled("Keep true for (seconds)",`<input ${attr("for_seconds")} type="number" min="0" max="86400" value="${Number(item.for_seconds||0)}">`)}${advanced("Use specific device attributes",attributes,Boolean(item.attribute||item.compare_attribute))}`}
    if(kind==="time_window")return `${type}${labelled("From",`<input ${attr("start_time")} type="time" value="${esc(item.start_time||"")}">`)}${labelled("Until",`<input ${attr("end_time")} type="time" value="${esc(item.end_time||"")}">`)}`;
    if(kind==="weekday")return `${type}${labelled("Days",`<input ${attr("weekdays")} value="${esc(formatWeekdays(item.weekdays))}" placeholder="Mon, Tue, Wed">`)}`;
    return `${type}${labelled("Sun position",`<select ${attr("sun_state")}><option value="below_horizon"${item.sun_state!=="above_horizon"?" selected":""}>The sun is down</option><option value="above_horizon"${item.sun_state==="above_horizon"?" selected":""}>The sun is up</option></select>`)}`;
  }
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
    const commonTemplates=templates.filter(([key])=>key!=="service");
    const iconCodes={turn_on:"&#9889;",turn_off:"&#9675;",toggle:"&#8644;",set_temperature:"&#8451;",set_brightness:"&#9728;",notification:"&#9993;",delay:"&#9201;",wait:"&#9655;",service:"&#9881;"};
    section.innerHTML=`<div class="automation-task-palette-head"><strong>What should happen?</strong><small>Choose a task. You can add more than one.</small></div><div class="automation-task-palette-grid">${commonTemplates.map(([key,title,detail,_icon,disabled])=>`<button type="button" data-action-template="${key}"${disabled?' disabled aria-disabled="true"':""}><span aria-hidden="true">${iconCodes[key]}</span><strong>${title}</strong><small>${detail}</small></button>`).join("")}</div><details class="automation-task-custom"><summary>Advanced: custom Home Assistant action</summary><button type="button" data-action-template="service"><span aria-hidden="true">${iconCodes.service}</span><span><strong>Custom action</strong><small>Enter a Home Assistant command manually</small></span></button></details>`;
    section.addEventListener("click",event=>{const button=event.target.closest("[data-action-template]");if(!button||button.disabled)return;if(workflowDraft.actions.length>=19){$("automation-studio-state").textContent="A flow supports up to 20 actions including the primary action.";return}workflowDraft.actions.push(newActionTask(button.dataset.actionTemplate));renderStudioInspector();renderEditorFlow();commitEditorHistory();$("automation-studio-state").textContent=`${button.querySelector("strong").textContent} task added. Complete its settings.`});
    root.append(section);
  }
  function validEntityId(value){return /^[a-z0-9_]+\.[a-z0-9_]+$/.test(String(value||""))}
  function actionStepValid(item){const kind=item.kind||"service";return kind==="delay"?Number(item.delay_seconds)>0:kind==="wait_state"?validEntityId(item.entity_id):kind==="notification"?Boolean(validEntityId(item.entity_id)&&item.notification_message):Boolean(validEntityId(item.entity_id)&&item.service)}
  function conditionStepValid(item){const kind=item?.kind||"entity";if(kind==="entity")return validEntityId(item.entity_id);if(kind==="entity_compare")return validEntityId(item.entity_id)&&validEntityId(item.compare_entity_id);if(kind==="time_window")return Boolean(item.start_time&&item.end_time);if(kind==="weekday")return Boolean((item.weekdays||[]).length);return kind==="sun"}
  function branchCardNeedsAttention(kind,index,branchIndex){const branch=workflowDraft.branches[branchIndex];if(!branch)return true;if(kind==="branch-action")return !actionStepValid(branch.actions?.[index]||{});if(kind==="branch-condition")return !conditionStepValid(branch.conditions?.[index]||{});if(kind==="branch-message")return branchHasMessage(branch)&&!String(branch.suggestion||"").trim();return false}
  function actionStepHtml(item,attributes){
    const kind=item.kind||"service",template=actionTaskKey(item),attr=field=>`${attributes} data-action-field="${field}"`;
    const labelled=(label,control)=>`<label><span>${label}</span>${control}</label>`;
    const labels={turn_on:"Power on",turn_off:"Power off",toggle:"Toggle",set_temperature:"Set temperature",set_brightness:"Set brightness",notification:"Notification",delay:"Delay",wait:"Wait until",service:"Custom service"};
    const type=template!=="service"?`<span class="automation-task-kind">${labels[template]}</span>`:labelled("Task type",`<select ${attr("kind")}><option value="service"${kind==="service"?" selected":""}>Control a device</option><option value="notification"${kind==="notification"?" selected":""}>Send a notification</option><option value="delay"${kind==="delay"?" selected":""}>Wait for a set time</option><option value="wait_state"${kind==="wait_state"?" selected":""}>Wait until something changes</option></select>`);
    if(kind==="delay")return `${type}${labelled("Wait for (seconds)",`<input ${attr("delay_seconds")} type="number" min="1" max="300" value="${Number(item.delay_seconds||1)}" placeholder="Seconds">`)}`;
    if(kind==="wait_state")return `${type}${labelled("Device or sensor",`<input ${attr("entity_id")} list="automation-entity-options" value="${esc(item.entity_id||"")}" placeholder="Choose a device or sensor">`)}${labelled("Must be",`<select ${attr("wait_operator")}>${workflowOperatorOptions(item.wait_operator)}</select>`)}${labelled("Compared with",`<input ${attr("wait_value")} value="${esc(item.wait_value||"")}" placeholder="For example: on, home, 26">`)}${labelled("Stop waiting after (seconds)",`<input ${attr("timeout_seconds")} type="number" min="1" max="300" value="${Number(item.timeout_seconds||30)}">`)}`;
    if(kind==="notification"){
      const channels=[...(notificationState.channels||[])];if(item.entity_id&&!channels.some(channel=>channel.entity_id===item.entity_id))channels.unshift({entity_id:item.entity_id,friendly_name:item.entity_id,available:false});
      return `${type}${labelled("Where to send it",`<select ${attr("entity_id")}><option value="">Choose a notification channel</option>${channels.map(channel=>`<option value="${esc(channel.entity_id)}"${channel.entity_id===item.entity_id?" selected":""}>${esc(channel.friendly_name||channel.entity_id)}${channel.available===false?" (unavailable)":""}</option>`).join("")}</select>`)}${labelled("Title",`<input ${attr("notification_title")} value="${esc(item.notification_title||"ZBRANO automation")}" placeholder="Notification title">`)}${labelled("Message",`<textarea ${attr("notification_message")} maxlength="1000" placeholder="Message to send">${esc(item.notification_message||"")}</textarea>`)}${labelled("Importance",`<select ${attr("notification_severity")}><option value="information"${item.notification_severity==="information"?" selected":""}>Information</option><option value="suggestion"${item.notification_severity!=="information"&&item.notification_severity!=="warning"&&item.notification_severity!=="critical"?" selected":""}>Suggestion</option><option value="warning"${item.notification_severity==="warning"?" selected":""}>Warning</option><option value="critical"${item.notification_severity==="critical"?" selected":""}>Critical</option></select>`)}`;
    }
    if(template==="set_temperature")return `${type}${labelled("Thermostat",`<input ${attr("entity_id")} list="automation-entity-options" value="${esc(item.entity_id||"")}" placeholder="Choose a thermostat">`)}${labelled("Target temperature",`<input ${attributes} data-action-data-field="temperature" type="number" min="5" max="35" step="0.5" value="${Number(item.service_data?.temperature??22)}">`)}`;
    if(template==="set_brightness")return `${type}${labelled("Light",`<input ${attr("entity_id")} list="automation-entity-options" value="${esc(item.entity_id||"")}" placeholder="Choose a light">`)}${labelled("Brightness (%)",`<input ${attributes} data-action-data-field="brightness_pct" type="number" min="1" max="100" value="${Number(item.service_data?.brightness_pct??70)}">`)}`;
    if(["turn_on","turn_off","toggle"].includes(template))return `${type}${labelled("Device",`<input ${attr("entity_id")} list="automation-entity-options" value="${esc(item.entity_id||"")}" placeholder="Choose a device">`)}${labelled("Wait before (seconds)",`<input ${attr("delay_seconds")} type="number" min="0" max="300" value="${Number(item.delay_seconds||0)}">`)}`;
    return `${type}${labelled("Device",`<input ${attr("entity_id")} list="automation-entity-options" value="${esc(item.entity_id||"")}" placeholder="Choose a device">`)}${labelled("Action command",`<input ${attr("service")} value="${esc(item.service||"")}" placeholder="For example: light.turn_on">`)}${labelled("Wait before (seconds)",`<input ${attr("delay_seconds")} type="number" min="0" max="300" value="${Number(item.delay_seconds||0)}">`)}`;
  }
  function renderWorkflowInspector(root){
    if(selectedStudioNode==="decision"){renderBranchInspector(root);return}
    if(selectedStudioNode==="trigger"){
      const items=workflowDraft.triggers,selectedIndex=selectedFlowCard.kind==="trigger"?Number(selectedFlowCard.index||0):0,workflowIndex=selectedIndex-1,total=items.length+1,section=document.createElement("section");section.className="automation-workflow-steps automation-selected-block-settings";
      const selected=workflowIndex>=0&&items[workflowIndex]?`<div class="automation-workflow-head"><strong>This When block</strong><button type="button" data-workflow-remove="${workflowIndex}">Remove block</button></div><div class="automation-workflow-step">${friendlyTriggerStepHtml(items[workflowIndex],`data-workflow-index="${workflowIndex}"`,false)}</div>`:"";
      const mode=total>1?`<label class="automation-trigger-connection">How this block connects<select data-trigger-mode><option value="any"${workflowDraft.trigger_mode!=="all"?" selected":""}>OR â€” either event can start it</option><option value="all"${workflowDraft.trigger_mode==="all"?" selected":""}>AND â€” both must be true</option></select></label>`:"";
      section.innerHTML=`${selected}${mode}<button class="automation-add-when" type="button" data-workflow-add="triggers">+ Add another When block</button>`;root.append(section);
      section.addEventListener("input",event=>{const field=event.target.dataset.triggerField,index=Number(event.target.dataset.workflowIndex);if(!field||!items[index])return;items[index][field]=field==="weekdays"?parseWeekdays(event.target.value):field.endsWith("seconds")||field.endsWith("minutes")?Number(event.target.value||0):event.target.value;renderEditorFlow();scheduleEditorHistory()});
      section.addEventListener("change",event=>{if(event.target.hasAttribute("data-trigger-mode")){workflowDraft.trigger_mode=event.target.value==="all"?"all":"any";renderEditorFlow();scheduleEditorHistory()}});
      section.addEventListener("click",event=>{const add=event.target.closest("[data-workflow-add]"),remove=event.target.closest("[data-workflow-remove]");if(add){items.push({kind:"entity",entity_id:"",operator:"above",value:"",for_seconds:0,weekdays:[],at:"",sun_event:"sunrise",offset_minutes:0,interval_minutes:5,one_time_at:""});selectedFlowCard={kind:"trigger",index:items.length,branchIndex:null}}else if(remove){items.splice(Number(remove.dataset.workflowRemove),1);selectedFlowCard={kind:"trigger",index:0,branchIndex:null}}else return;renderStudioInspector();renderEditorFlow();commitEditorHistory()});
      return;
    }
    const specs=selectedStudioNode==="trigger"?["triggers","More ways to start"]:selectedStudioNode==="context"?["conditions","Extra checks"]:selectedStudioNode==="action"?["actions","More things to do"]:null;
    if(!specs)return;
    const [collection,title]=specs,items=workflowDraft[collection];
    const section=document.createElement("section");section.className="automation-workflow-steps";
    const mode=collection==="triggers"?`<label>Start when<select data-trigger-mode><option value="any"${workflowDraft.trigger_mode!=="all"?" selected":""}>ANY of these happen (OR)</option><option value="all"${workflowDraft.trigger_mode==="all"?" selected":""}>ALL of these are true (AND)</option></select></label>`:collection==="conditions"?`<label>Continue when<select data-workflow-mode><option value="all"${workflowDraft.condition_mode==="all"?" selected":""}>ALL checks pass (AND)</option><option value="any"${workflowDraft.condition_mode==="any"?" selected":""}>ANY check passes (OR)</option></select></label>`:"";
    const rows=items.map((item,index)=>{
      if(collection==="actions")return `<div class="automation-workflow-step">${actionStepHtml(item,`data-workflow-index="${index}"`)}<button type="button" data-workflow-remove="${index}">Remove</button></div>`;
      return `<div class="automation-workflow-step">${collection==="triggers"?friendlyTriggerStepHtml(item,`data-workflow-index="${index}"`):conditionStepHtml(item,`data-workflow-index="${index}"`)}<button type="button" data-workflow-remove="${index}">Remove</button></div>`;
    }).join("");
    const addControl=collection==="actions"?"":`<button type="button" data-workflow-add="${collection}">+ Add</button>`,empty=collection==="actions"?"Choose a task above. Nothing will be controlled unless you add one.":"None added. The primary block above remains active.";
    section.innerHTML=`<div class="automation-workflow-head"><strong>${collection==="actions"?"Your tasks":title}</strong>${addControl}</div>${mode}${rows||`<small class="automation-workflow-empty">${empty}</small>`}`;root.append(section);
    section.addEventListener("input",event=>{const field=event.target.dataset.actionField||event.target.dataset.triggerField||event.target.dataset.conditionField,dataField=event.target.dataset.actionDataField,index=Number(event.target.dataset.workflowIndex);if((!field&&!dataField)||!items[index])return;if(dataField){items[index].service_data={...(items[index].service_data||{}),[dataField]:Number(event.target.value)}}else items[index][field]=field==="weekdays"?parseWeekdays(event.target.value):field.endsWith("seconds")||field.endsWith("minutes")?Number(event.target.value||0):event.target.value;if(collection==="actions"&&field==="entity_id"&&["turn_on","turn_off","toggle"].includes(items[index].task_template)){const domain=String(event.target.value||"").split(".",1)[0];items[index].service=domain?`${domain}.${items[index].task_template}`:""}if(field==="kind")renderStudioInspector();renderEditorFlow();scheduleEditorHistory()});
    section.addEventListener("change",event=>{if(event.target.dataset.triggerField==="operator"){renderStudioInspector()}else if(event.target.hasAttribute("data-trigger-mode")){workflowDraft.trigger_mode=event.target.value;renderEditorFlow();scheduleEditorHistory()}else if(event.target.hasAttribute("data-workflow-mode")){workflowDraft.condition_mode=event.target.value;renderEditorFlow();scheduleEditorHistory()}});
    section.addEventListener("click",event=>{const add=event.target.closest("[data-workflow-add]"),remove=event.target.closest("[data-workflow-remove]");if(add){items.push(collection==="actions"?newActionTask():collection==="triggers"?{kind:"entity",entity_id:"",operator:"changes_to",value:"",for_seconds:0,weekdays:[],at:"",sun_event:"sunrise",offset_minutes:0,interval_minutes:5,one_time_at:""}:newBranchCondition());renderStudioInspector();renderEditorFlow();commitEditorHistory()}else if(remove){items.splice(Number(remove.dataset.workflowRemove),1);renderStudioInspector();renderEditorFlow();commitEditorHistory()}});
  }

  function branchDeliveryValue(branch,key){const source={delivery_voice:"automation-delivery-voice",delivery_notification_center:"automation-delivery-center",delivery_ha_push:"automation-delivery-push"}[key];return Object.hasOwn(branch||{},key)?branch[key]!==false:$(source).checked}
  function branchDeliveryDefaults(){return {delivery_voice:$("automation-delivery-voice").checked,delivery_notification_center:$("automation-delivery-center").checked,delivery_ha_push:$("automation-delivery-push").checked}}
  function branchHasMessage(branch){return Boolean(branch?.message_enabled||String(branch?.suggestion||"").trim())}
  function branchExecutionPolicy(branch){const value=branch?.execution_policy||$("automation-execution-policy").value;return value==="autonomous"?"autonomous":"approval_required"}
  function branchMessageEditor(branch,branchIndex){return `<label>Message<textarea data-branch-suggestion="${branchIndex}" maxlength="1000" placeholder="Write what ZBRANO should say">${esc(branch.suggestion||"")}</textarea></label><div class="automation-branch-delivery"><strong>Send this message</strong><label class="is-check"><input type="checkbox" data-branch-delivery="delivery_voice" data-branch-index="${branchIndex}"${branchDeliveryValue(branch,"delivery_voice")?" checked":""}> Say this message aloud</label><label class="is-check"><input type="checkbox" data-branch-delivery="delivery_notification_center" data-branch-index="${branchIndex}"${branchDeliveryValue(branch,"delivery_notification_center")?" checked":""}> Show in ZBRANO notifications</label><label class="is-check"><input type="checkbox" data-branch-delivery="delivery_ha_push" data-branch-index="${branchIndex}"${branchDeliveryValue(branch,"delivery_ha_push")?" checked":""}> Send to Home Assistant notifications</label></div>`}
  function renderBranchInspector(root){
    const section=document.createElement("section");section.className="automation-workflow-steps automation-branch-editor";
    const showMessages=true;
    const selectedBranchIndex=["branch-action","branch-condition","branch-message"].includes(selectedFlowCard.kind)?Number(selectedFlowCard.branchIndex||0):selectedFlowCard.kind==="decision"?Number(selectedFlowCard.index||0):0;
    const cards=workflowDraft.branches.map((branch,branchIndex)=>[branch,branchIndex]).filter(([,branchIndex])=>branchIndex===Math.max(0,Math.min(selectedBranchIndex,workflowDraft.branches.length-1))).map(([branch,branchIndex])=>{
      if(selectedFlowCard.kind==="branch-condition"&&selectedFlowCard.branchIndex===branchIndex&&branch.conditions?.[selectedFlowCard.index])return `<article class="automation-branch-card"><div class="automation-branch-path-label">${branchIndex?"ELSE IF":"IF"} · AND CHECK</div><div class="automation-workflow-step">${conditionStepHtml(branch.conditions[selectedFlowCard.index],`data-branch-collection="conditions" data-branch-index="${branchIndex}" data-item-index="${selectedFlowCard.index}"`)}<button type="button" data-branch-remove-item="conditions" data-branch-index="${branchIndex}" data-item-index="${selectedFlowCard.index}">Remove check</button></div></article>`;
      if(selectedFlowCard.kind==="branch-action"&&selectedFlowCard.branchIndex===branchIndex&&branch.actions?.[selectedFlowCard.index])return `<article class="automation-branch-card"><div class="automation-branch-path-label">${branchIndex?"ELSE IF":"IF"} · THEN TASK</div><div class="automation-workflow-step"><label><span>Before running this path's tasks</span><select data-branch-policy data-branch-index="${branchIndex}"><option value="approval_required"${branchExecutionPolicy(branch)==="approval_required"?" selected":""}>Ask before running</option><option value="autonomous"${branchExecutionPolicy(branch)==="autonomous"?" selected":""}>Run automatically</option></select></label>${actionStepHtml(branch.actions[selectedFlowCard.index],`data-branch-collection="actions" data-branch-index="${branchIndex}" data-item-index="${selectedFlowCard.index}"`)}<button type="button" data-branch-remove-item="actions" data-branch-index="${branchIndex}" data-item-index="${selectedFlowCard.index}">Remove task</button></div></article>`;
      if(selectedFlowCard.kind==="branch-message"&&selectedFlowCard.branchIndex===branchIndex&&branchHasMessage(branch))return `<article class="automation-branch-card"><div class="automation-branch-path-label">${branchIndex?"ELSE IF":"IF"} · MESSAGE TASK</div><div class="automation-workflow-step">${branchMessageEditor(branch,branchIndex)}<button type="button" data-branch-remove-message="${branchIndex}">Remove message task</button></div></article>`;
      const fallback=branchIndex===workflowDraft.branches.length-1&&!(branch.conditions||[]).length,pathWord=fallback?"ELSE":branchIndex?"ELSE IF":"IF";
      return `<article class="automation-branch-card"><div class="automation-branch-path-label">${pathWord}</div><div class="automation-workflow-head"><strong>${pathWord} path</strong><button type="button" data-branch-remove="${branchIndex}">Remove path</button></div><small>${showMessages?"Select a condition or task block to edit only that block.":"This path monitors quietly."}</small>${fallback?"<small>This fallback is used only when no path above matches.</small>":""}</article>`;
    }).join("");
    section.innerHTML=cards?`<div class="automation-workflow-head"><strong>IF / ELSE IF paths</strong><button type="button" data-branch-add>+ ELSE IF</button></div><small>The first matching path runs. Each path keeps its own checks, message, and tasks.</small>${cards}`:`<div class="automation-outcome-choice"><span class="automation-outcome-choice-icon" aria-hidden="true">&#8646;</span><strong>Add an ELSE IF path</strong><small>Your current IF conditions and THEN actions become the first path. The new path stays separate.</small><button type="button" data-branch-add>Add ELSE IF</button></div>`;root.append(section);
    section.addEventListener("input",event=>{const branchIndex=Number(event.target.dataset.branchIndex),branch=workflowDraft.branches[branchIndex];if(event.target.hasAttribute("data-branch-policy")&&branch){branch.execution_policy=event.target.value==="autonomous"?"autonomous":"approval_required";renderEditorFlow();scheduleEditorHistory();return}if(event.target.hasAttribute("data-branch-suggestion")){const messageBranch=workflowDraft.branches[Number(event.target.dataset.branchSuggestion)];messageBranch.message_enabled=true;messageBranch.suggestion=event.target.value;renderEditorFlow();scheduleEditorHistory();return}if(event.target.hasAttribute("data-branch-delivery")&&branch){branch[event.target.dataset.branchDelivery]=event.target.checked;renderEditorFlow();scheduleEditorHistory();return}const collection=event.target.dataset.branchCollection,itemIndex=Number(event.target.dataset.itemIndex),field=event.target.dataset.actionField||event.target.dataset.conditionField,dataField=event.target.dataset.actionDataField;if(!branch||!collection||(!field&&!dataField))return;const item=branch[collection][itemIndex];if(dataField)item.service_data={...(item.service_data||{}),[dataField]:Number(event.target.value)};else item[field]=field==="weekdays"?parseWeekdays(event.target.value):field.endsWith("seconds")||field.endsWith("minutes")?Number(event.target.value||0):event.target.value;if(collection==="actions"&&field==="entity_id"&&["turn_on","turn_off","toggle"].includes(item.task_template)){const domain=String(event.target.value||"").split(".",1)[0];item.service=domain?`${domain}.${item.task_template}`:""}if(field==="kind")renderStudioInspector();renderEditorFlow();scheduleEditorHistory()});
    section.addEventListener("click",event=>{const add=event.target.closest("[data-branch-add]"),remove=event.target.closest("[data-branch-remove]"),removeMessage=event.target.closest("[data-branch-remove-message]"),addItem=event.target.closest("[data-branch-add-item]"),removeItem=event.target.closest("[data-branch-remove-item]");if(add){addBranchPath();return}else if(remove){workflowDraft.branches.splice(Number(remove.dataset.branchRemove),1)}else if(removeMessage){const branch=workflowDraft.branches[Number(removeMessage.dataset.branchRemoveMessage)];branch.message_enabled=false;branch.suggestion="";selectedFlowCard={kind:"decision",index:Number(removeMessage.dataset.branchRemoveMessage),branchIndex:null}}else if(addItem){const branch=workflowDraft.branches[Number(addItem.dataset.branchIndex)],collection=addItem.dataset.branchAddItem;branch[collection].push(collection==="actions"?newActionTask():newBranchCondition())}else if(removeItem){workflowDraft.branches[Number(removeItem.dataset.branchIndex)][removeItem.dataset.branchRemoveItem].splice(Number(removeItem.dataset.itemIndex),1)}else return;renderStudioInspector();renderEditorFlow();commitEditorHistory()});
  }

  function selectStudioNode(kind,index=null,branchIndex=null){
    const inspectorKind=["branch-action","branch-condition","branch-message"].includes(kind)?"decision":kind;if(!studioPanels[inspectorKind])return;
    selectedStudioNode=inspectorKind;if(Number.isInteger(index))selectedFlowCard={kind,index,branchIndex:Number.isInteger(branchIndex)?branchIndex:null};else if(selectedFlowCard.kind!==kind)selectedFlowCard={kind,index:0,branchIndex:null};renderEditorFlow();renderStudioInspector();
    if(Number.isInteger(index))requestAnimationFrame(()=>focusSelectedFlowEditor(kind,index,branchIndex));
  }
  function focusSelectedFlowEditor(kind,index,branchIndex=null){
    const root=$("automation-studio-inspector-fields");if(!root)return;
    let target=null;
    if(kind==="trigger"){
      if(index===0)target=$("studio-automation-trigger-entity");
      else{
        const workflowIndex=index-1,item=workflowDraft.triggers[workflowIndex]||{},preferredField=({entity:"entity_id",time:"at",sun:"sun_event",interval:"interval_minutes",one_time:"one_time_at"})[item.kind||"entity"]||"kind";
        target=root.querySelector(`[data-workflow-index="${workflowIndex}"][data-trigger-field="${preferredField}"]`)||root.querySelector(`[data-workflow-index="${workflowIndex}"]`);
      }
    }
    else if(kind==="context"){const hasPresence=Boolean(presenceEntity()),signalCount=$("automation-signals").value.split(/[,\n]/).map(value=>value.trim()).filter(Boolean).length,offset=(hasPresence?1:0)+signalCount;if(hasPresence&&index===0)target=$("studio-automation-presence");else if(index<offset)target=$("studio-automation-signals");else target=root.querySelector(`[data-workflow-index="${index-offset}"]`)}
    else if(kind==="action"){const primary=Boolean($("automation-action-entity").value.trim()||$("automation-action-service").value.trim());target=primary&&index===0?$("studio-automation-action-entity"):root.querySelector(`[data-workflow-index="${index-(primary?1:0)}"]`)}
    else if(kind==="decision")target=root.querySelector(`[data-branch-index="${index}"]`);
    else if(kind==="branch-message")target=root.querySelector(`[data-branch-suggestion="${branchIndex}"]`);
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
    const presence=presenceEntity(),signals=$("automation-signals").value.split(/[,\n]/).map(value=>value.trim()).filter(Boolean);
    if(presence&&index===0)return {type:"presence",item:presence,index:0,signals};
    const offset=presence?1:0,signalIndex=index-offset;
    if(signalIndex>=0&&signalIndex<signals.length)return {type:"signal",item:signals[signalIndex],index:signalIndex,signals};
    return {type:"condition",item:workflowDraft.conditions[signalIndex-signals.length],index:signalIndex-signals.length,signals};
  }
  function deleteFlowCard(kind,index,branchIndex=null){
    if(kind==="decision")return deleteBranchPath(index);
    if(kind==="trigger"){if(index===0)clearPrimaryTrigger();else workflowDraft.triggers.splice(index-1,1)}
    else if(kind==="context"){
      const hasPresence=Boolean(presenceEntity()),signals=$("automation-signals").value.split(/[,\n]/).map(value=>value.trim()).filter(Boolean);
      if(hasPresence&&index===0)$("automation-require-presence").checked=false;
      else{const signalIndex=index-(hasPresence?1:0);if(signalIndex<signals.length){signals.splice(signalIndex,1);$("automation-signals").value=signals.join(", ")}else workflowDraft.conditions.splice(signalIndex-signals.length,1)}
    }else if(kind==="branch-message"){const branch=workflowDraft.branches[branchIndex];if(!branch)return;branch.message_enabled=false;branch.suggestion=""}
    else if(kind==="branch-action"){const branch=workflowDraft.branches[branchIndex];if(!branch?.actions?.[index])return;branch.actions.splice(index,1)}
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
      const source=contextFlowSource(fromIndex),presence=presenceEntity()?1:0;
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
    targetActions.splice(Math.max(0,Math.min(insertion,targetActions.length)),0,item);selectedStudioNode="decision";selectedFlowCard={kind:"branch-action",index:Math.max(0,Math.min(insertion,targetActions.length-1)),branchIndex:target.branchIndex};renderStudioInspector();renderEditorFlow();commitEditorHistory();$("automation-studio-state").textContent="Task moved into the selected outcome. Use Undo to restore the previous flow.";return true;
  }
  function moveBranchCondition(source,target){
    const targetConditions=workflowDraft.branches[target.branchIndex]?.conditions,sameBranch=source.branchIndex===target.branchIndex;if(!targetConditions||targetConditions.length>=20&&!sameBranch){$("automation-studio-state").textContent="That outcome cannot accept another check.";return false}
    const sourceConditions=workflowDraft.branches[source.branchIndex]?.conditions;if(!sourceConditions?.[source.index])return false;let insertion=target.index;const item=sourceConditions.splice(source.index,1)[0];if(sameBranch&&insertion>source.index)insertion-=1;
    targetConditions.splice(Math.max(0,Math.min(insertion,targetConditions.length)),0,item);selectedStudioNode="decision";selectedFlowCard={kind:"branch-condition",index:Math.max(0,Math.min(insertion,targetConditions.length-1)),branchIndex:target.branchIndex};renderStudioInspector();renderEditorFlow();commitEditorHistory();$("automation-studio-state").textContent="Check moved into the selected outcome. Use Undo to restore the previous flow.";return true;
  }
  function newBranchCondition(template="entity"){return {kind:["entity","entity_compare","time_window","weekday","sun"].includes(template)?template:"entity",entity_id:"",attribute:"",operator:template==="entity_compare"?"above":"equals",value:"",compare_entity_id:"",compare_attribute:"",for_seconds:0,weekdays:[],start_time:"",end_time:"",sun_state:"below_horizon"}}
  function addBranchCondition(branchIndex,insertionIndex,template="entity"){
    const conditions=workflowDraft.branches[branchIndex]?.conditions;if(!conditions)return false;if(conditions.length>=20){$("automation-studio-state").textContent="This outcome already has its maximum of 20 checks.";return false}const target=Math.max(0,Math.min(insertionIndex,conditions.length));conditions.splice(target,0,newBranchCondition(template));selectedStudioNode="decision";selectedFlowCard={kind:"branch-condition",index:target,branchIndex};renderStudioInspector();renderEditorFlow();commitEditorHistory();requestAnimationFrame(()=>focusSelectedFlowEditor("branch-condition",target,branchIndex));$("automation-studio-state").textContent=`${({entity:"Device or sensor",entity_compare:"Compare two values",time_window:"Time of day",weekday:"Day of week",sun:"Sunrise or sunset"})[template]||"IF"} check added to the selected outcome. Complete its settings before saving.`;return true;
  }
  function branchQuickInsertion(kind,branchIndex){return selectedFlowCard.kind===kind&&selectedFlowCard.branchIndex===branchIndex?selectedFlowCard.index+1:(kind==="branch-condition"?workflowDraft.branches[branchIndex]?.conditions?.length:workflowDraft.branches[branchIndex]?.actions?.length)||0}
  function addBranchActionTemplate(branchIndex,template,insertionIndex){
    if(template==="message"){
      const branch=workflowDraft.branches[branchIndex];if(!branch||branchHasMessage(branch))return false;branch.message_enabled=true;branch.suggestion="";selectedStudioNode="decision";selectedFlowCard={kind:"branch-message",index:0,branchIndex};renderStudioInspector();renderEditorFlow();commitEditorHistory();requestAnimationFrame(()=>focusSelectedFlowEditor("branch-message",0,branchIndex));$("automation-studio-state").textContent="Message task added. Write its text and choose where ZBRANO should send it.";return true
    }
    const actions=workflowDraft.branches[branchIndex]?.actions;if(!actions)return false;if(actions.length>=20){$("automation-studio-state").textContent="This outcome already has its maximum of 20 tasks.";return false}const target=Math.max(0,Math.min(insertionIndex,actions.length));actions.splice(target,0,newActionTask(template));selectedStudioNode="decision";selectedFlowCard={kind:"branch-action",index:target,branchIndex};renderStudioInspector();renderEditorFlow();commitEditorHistory();requestAnimationFrame(()=>focusSelectedFlowEditor("branch-action",target,branchIndex));$("automation-studio-state").textContent=`${({turn_on:"Power on",turn_off:"Power off",toggle:"Change power",set_temperature:"Set temperature",set_brightness:"Set brightness",notification:"Send notification",delay:"Wait",wait:"Wait until",service:"Custom action"})[template]||"Action"} task added to the selected outcome. Complete its settings.`;return true;
  }
  function addBranchAction(branchIndex,insertionIndex){
    return addBranchActionTemplate(branchIndex,"service",insertionIndex)
  }
  function startElseIfFlow(){
    const firstChecks=workflowDraft.conditions.splice(0),firstActions=visualFlowItems("action"),firstMessage=$("automation-proposal").value.trim();
    writeFlowSequence("action",[]);
    workflowDraft.branches=[
      {name:"IF",execution_policy:branchExecutionPolicy(),suggestion:firstMessage,message_enabled:Boolean(firstMessage),condition_mode:"all",...branchDeliveryDefaults(),conditions:firstChecks.length?firstChecks:[newBranchCondition()],actions:firstActions},
      {name:"ELSE IF",execution_policy:"approval_required",suggestion:"",message_enabled:false,condition_mode:"all",...branchDeliveryDefaults(),conditions:[newBranchCondition()],actions:[]},
    ];
    selectedStudioNode="decision";selectedFlowCard={kind:"decision",index:1,branchIndex:null};renderStudioInspector();renderEditorFlow();commitEditorHistory();requestAnimationFrame(()=>focusSelectedFlowEditor("decision",1));$("automation-studio-state").textContent="ELSE IF path added. Existing IF conditions and THEN actions remain connected to the first path.";return true;
  }
  function addBranchPath(){
    if(!workflowDraft.branches.length)return startElseIfFlow();
    if(workflowDraft.branches.length>=10){$("automation-studio-state").textContent="A flow supports up to 10 paths.";return false}const fallbackIndex=workflowDraft.branches.findIndex((branch,index)=>index===workflowDraft.branches.length-1&&!(branch.conditions||[]).length),selectedAfter=selectedFlowCard.kind==="decision"?selectedFlowCard.index+1:workflowDraft.branches.length,target=Math.max(0,Math.min(fallbackIndex>=0?Math.min(selectedAfter,fallbackIndex):selectedAfter,workflowDraft.branches.length));workflowDraft.branches.splice(target,0,{name:"ELSE IF",execution_policy:"approval_required",suggestion:"",message_enabled:false,condition_mode:"all",...branchDeliveryDefaults(),conditions:[newBranchCondition()],actions:[]});selectedStudioNode="decision";selectedFlowCard={kind:"decision",index:target,branchIndex:null};renderStudioInspector();renderEditorFlow();commitEditorHistory();requestAnimationFrame(()=>focusSelectedFlowEditor("decision",target));$("automation-studio-state").textContent="ELSE IF path added. Add its check, then add only the tasks this path needs.";return true;
  }
  function moveBranchPathTo(fromIndex,targetIndex){
    const branches=workflowDraft.branches;if(!branches[fromIndex])return false;const fallbackIndex=branches.length&&!(branches.at(-1)?.conditions||[]).length?branches.length-1:-1;if(fromIndex===fallbackIndex){$("automation-studio-state").textContent="The OTHERWISE outcome stays last so the flow remains predictable.";return false}const maxTarget=fallbackIndex>=0?fallbackIndex-1:branches.length-1,target=Math.max(0,Math.min(Number(targetIndex),maxTarget));if(target===fromIndex)return false;const moved=branches.splice(fromIndex,1)[0];branches.splice(target,0,moved);selectedStudioNode="decision";selectedFlowCard={kind:"decision",index:target,branchIndex:null};renderStudioInspector();renderEditorFlow();commitEditorHistory();requestAnimationFrame(()=>focusSelectedFlowEditor("decision",target));$("automation-studio-state").textContent="Outcome moved. OTHERWISE remains last. Use Undo to restore the previous order.";return true;
  }
  function duplicateBranchPath(index){
    const branches=workflowDraft.branches,source=branches[index];if(!source)return false;if(branches.length>=10){$("automation-studio-state").textContent="A flow supports up to 10 outcomes.";return false}const copy=cloneEditorValue(source),sourceIsFallback=index===branches.length-1&&!(source.conditions||[]).length;copy.name=`${source.name||`Outcome ${index+1}`} copy`;if(sourceIsFallback)copy.conditions=[newBranchCondition()];const fallbackIndex=branches.length&&!(branches.at(-1)?.conditions||[]).length?branches.length-1:-1,target=sourceIsFallback?index:Math.min(index+1,fallbackIndex>=0?fallbackIndex:branches.length);branches.splice(target,0,copy);selectedStudioNode="decision";selectedFlowCard={kind:"decision",index:target,branchIndex:null};renderStudioInspector();renderEditorFlow();commitEditorHistory();requestAnimationFrame(()=>focusSelectedFlowEditor("decision",target));$("automation-studio-state").textContent=sourceIsFallback?"OTHERWISE copied as a conditional outcome so only one fallback remains.":"Outcome duplicated with its checks and tasks. Use Undo to restore the previous flow.";return true;
  }
  function deleteBranchPath(index){
    const branches=workflowDraft.branches;if(!branches[index])return false;if(branches.length===1){$("automation-studio-state").textContent="Keep at least one outcome, or turn off outcomes in All settings.";return false}const removed=branches.splice(index,1)[0],target=Math.max(0,Math.min(index,branches.length-1));selectedStudioNode="decision";selectedFlowCard={kind:"decision",index:target,branchIndex:null};renderStudioInspector();renderEditorFlow();commitEditorHistory();requestAnimationFrame(()=>focusSelectedFlowEditor("decision",target));$("automation-studio-state").textContent=`${removed.name||"Outcome"} removed. Use Undo to restore it.`;return true;
  }
  function addStudioBlock(kind,insertionIndex=null){
    const trigger=()=>({kind:"entity",entity_id:"",operator:"changes_to",value:"",for_seconds:0,weekdays:[],at:"",sun_event:"sunrise",offset_minutes:0,interval_minutes:5,one_time_at:""});
    const condition=()=>newBranchCondition();
    const action=()=>({kind:"service",entity_id:"",service:"",service_data:{},delay_seconds:0,wait_operator:"equals",wait_value:"",timeout_seconds:30});
    if(kind==="trigger"){
      if(workflowDraft.triggers.length>=9){$("automation-studio-state").textContent="A flow supports up to 10 triggers including the primary trigger.";return}
      const items=visualFlowItems("trigger"),target=insertionIndex==null?items.length:Math.max(0,Math.min(insertionIndex,items.length));items.splice(target,0,trigger());writeFlowSequence("trigger",items);selectedFlowCard={kind,index:target};
    }else if(kind==="context"){
      if(workflowDraft.conditions.length>=20){$("automation-studio-state").textContent="A flow supports up to 20 context conditions.";return}
      const presence=presenceEntity()?1:0,signals=$("automation-signals").value.split(/[,\n]/).map(value=>value.trim()).filter(Boolean).length,target=insertionIndex==null?workflowDraft.conditions.length:Math.max(0,Math.min(insertionIndex-presence-signals,workflowDraft.conditions.length));workflowDraft.conditions.splice(target,0,condition());selectedFlowCard={kind,index:presence+signals+target};
    }else if(kind==="decision"){
      if(!workflowDraft.branches.length){startElseIfFlow();return}
      if(workflowDraft.branches.length>=10){$("automation-studio-state").textContent="A flow supports up to 10 paths.";return}
      const target=insertionIndex==null?workflowDraft.branches.length:Math.max(0,Math.min(insertionIndex,workflowDraft.branches.length));workflowDraft.branches.splice(target,0,{name:"ELSE IF",execution_policy:"approval_required",suggestion:"",message_enabled:false,condition_mode:"all",...branchDeliveryDefaults(),conditions:[condition()],actions:[]});selectedFlowCard={kind,index:target};
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
    $("autonomy-mode-summary").textContent="Per automation";
    $("autonomy-mode-detail").textContent="Chosen separately in Step 1";
    const draftCount=(state.automations||[]).filter(item=>!item.enabled).length;
    const suggestionCount=(state.suggestions||[]).filter(item=>["pending","approval_required"].includes(item.status)&&item.delivery_notification_center!==false).length;
    $("autonomy-draft-count").textContent=String(draftCount);
    $("autonomy-suggestion-count").textContent=String(suggestionCount);
    panel.querySelector('[data-automation-overview-target="drafts"]')?.setAttribute("aria-label",`View ${draftCount} automation draft${draftCount===1?"":"s"}`);
    panel.querySelector('[data-automation-overview-target="suggestions"]')?.setAttribute("aria-label",`View ${suggestionCount} pending suggestion${suggestionCount===1?"":"s"}`);
  }

  function automationNeedsAttention(item){
    const recovery=item.recovery_state||{},readiness=item.readiness||{};
    return Boolean(item.review_required||recovery.circuit_open||readiness.ready===false||["blocked_permission","paused_failure","failed","deferred"].includes(item.status));
  }

  const decisionLabels={
    waiting_trigger_group:"Waiting for all When events",suppressed_sleep_hours:"Paused for sleep hours",suppressed_presence:"Required person is not present",suppressed_context:"A shared check is false",suppressed_branch:"No IF or ELSE IF path matched",already_satisfied:"The task was already done",deferred_not_now:"Waiting after Not now",blocked_permission:"Permission blocked the task",paused_failure:"Paused after repeated failures",deferred_learning:"Held back by learned feedback",rate_limited:"Hourly run limit reached",observed:"Matched — monitored silently",pending:"Matched — message sent",approval_required:"Matched — waiting for approval",executing:"Running automatically",executed:"Action completed",failed:"Action failed"
  };
  const matchedDecisionOutcomes=new Set(["observed","pending","approval_required","executing","executed"]);
  const attentionDecisionOutcomes=new Set(["blocked_permission","paused_failure","failed"]);
  const friendlyDecision=value=>decisionLabels[value]||String(value||"Evaluation").replaceAll("_"," ");

  function automationDecisions(){
    return (state.automations||[]).flatMap(item=>(item.decision_history||[]).map(entry=>({...entry,automation_id:item.id,automation_name:item.name||"Unnamed automation"}))).sort((left,right)=>Number(right.created_at||0)-Number(left.created_at||0));
  }

  function renderActivity(){
    const automations=state.automations||[],decisions=automationDecisions(),cutoff=Date.now()/1000-86400;
    $("automation-activity-watching").textContent=String(automations.filter(item=>item.enabled).length);
    $("automation-activity-attention").textContent=String(automations.filter(automationNeedsAttention).length);
    $("automation-activity-matched").textContent=String(decisions.filter(item=>Number(item.created_at||0)>=cutoff&&matchedDecisionOutcomes.has(item.outcome)).length);
    $("automation-activity-actions").textContent=String(decisions.filter(item=>Number(item.created_at||0)>=cutoff&&item.outcome==="executed").length);
    const automationFilter=$("automation-activity-automation-filter"),previousAutomation=automationFilter.value||"all";
    automationFilter.replaceChildren(new Option("All automations","all"));
    for(const item of [...automations].sort((left,right)=>String(left.name||"").localeCompare(String(right.name||""))))automationFilter.add(new Option(item.name||"Unnamed automation",item.id));
    automationFilter.value=[...automationFilter.options].some(option=>option.value===previousAutomation)?previousAutomation:"all";
    const resultFilter=$("automation-activity-result-filter").value||"all";
    const visible=decisions.filter(item=>automationFilter.value==="all"||item.automation_id===automationFilter.value).filter(item=>resultFilter==="all"||(resultFilter==="matched"&&matchedDecisionOutcomes.has(item.outcome))||(resultFilter==="attention"&&attentionDecisionOutcomes.has(item.outcome))||(resultFilter==="no_action"&&!matchedDecisionOutcomes.has(item.outcome)&&!attentionDecisionOutcomes.has(item.outcome)));
    $("automation-decision-count").textContent=`${visible.length} record${visible.length===1?"":"s"}`;
    const feed=$("automation-decision-feed");feed.replaceChildren();
    if(!visible.length)feed.innerHTML='<div class="autonomy-empty">No evaluations match these filters yet.</div>';
    for(const item of visible.slice(0,100)){
      const row=document.createElement("div"),tone=attentionDecisionOutcomes.has(item.outcome)?"attention":matchedDecisionOutcomes.has(item.outcome)?"matched":"safe";row.className="automation-decision-row";row.dataset.tone=tone;
      const path=item.branch?`<small>Path: ${esc(item.branch)}</small>`:"",policy=item.policy?`<span>${esc(authorityLabel(item.policy))}</span>`:"";
      row.innerHTML=`<div class="automation-decision-title"><div><strong>${esc(friendlyDecision(item.outcome))}</strong><small>${esc(item.automation_name)}</small></div>${policy}</div><p>${esc(item.detail||"No additional detail was recorded.")}</p>${path}${item.evidence?`<details><summary>Evidence used</summary><small>${esc(item.evidence)}</small></details>`:""}<time>${new Date(Number(item.created_at||0)*1000).toLocaleString()}</time>`;feed.appendChild(row);
    }
    const health=$("automation-health-list");health.replaceChildren();
    if(!automations.length)health.innerHTML='<div class="autonomy-empty">No saved automations yet.</div>';
    for(const item of [...automations].sort((left,right)=>Number(automationNeedsAttention(right))-Number(automationNeedsAttention(left))||Number(Boolean(right.enabled))-Number(Boolean(left.enabled))||String(left.name||"").localeCompare(String(right.name||"")))){
      const recovery=item.recovery_state||{},readiness=item.readiness||{},attention=automationNeedsAttention(item),last=item.last_decision||(item.decision_history||[])[0],status=!item.enabled?"Off":recovery.circuit_open||item.status==="paused_failure"?"Paused after failures":readiness.ready===false||item.status==="blocked_permission"?"Permission needed":attention?"Check this automation":"Watching";
      const row=document.createElement("div");row.className="automation-health-row";row.dataset.tone=attention?"attention":item.enabled?"healthy":"off";row.innerHTML=`<div><strong>${esc(item.name||"Unnamed automation")}</strong><span>${esc(status)}</span></div><button type="button" data-activity-open-automation="${esc(item.id)}">Open</button><small>${last?`${esc(friendlyDecision(last.outcome))} · ${new Date(Number(last.created_at||0)*1000).toLocaleString()}`:item.enabled?"Waiting for its first matching event":"Enable it when you are ready"}</small>`;health.appendChild(row);
    }
  }

  const permissionSourceLabels={trigger_read:"Starts the automation",signal_read:"Provides context",condition_read:"Used by an IF check",condition_compare_read:"Compared in an IF check",presence_read:"Checks presence",wait_read:"Waits for this state",action_control:"Used by a task"};
  function permissionRequirementText(requirement){
    if(requirement.allowed)return requirement.permission==="control"?"Control allowed":"Reading allowed";
    if(requirement.safety_label_blocked)return"Control blocked by its Home Assistant safety label";
    if(requirement.permission==="control"&&requirement.access==="read_only")return"Set as Sensor device — control is not allowed";
    return requirement.permission==="control"?"Control permission is missing":"Reading permission is missing";
  }
  function renderPermissions(){
    const automations=state.automations||[],filter=$("automation-permission-filter").value||"all",requirements=automations.flatMap(item=>item.readiness?.requirements||[]);
    const uniqueReads=new Set(requirements.filter(item=>item.permission==="read").map(item=>item.entity_id)),uniqueControls=new Set(requirements.filter(item=>item.permission==="control").map(item=>item.entity_id));
    $("automation-permission-ready").textContent=String(automations.filter(item=>item.readiness?.ready!==false).length);
    $("automation-permission-attention").textContent=String(automations.filter(item=>item.readiness?.ready===false).length);
    $("automation-permission-reads").textContent=String(uniqueReads.size);$("automation-permission-controls").textContent=String(uniqueControls.size);
    const visible=automations.filter(item=>filter==="all"||(filter==="attention"&&item.readiness?.ready===false)||(filter==="ready"&&item.readiness?.ready!==false));
    const root=$("automation-permission-list");root.replaceChildren();
    if(!visible.length){root.innerHTML=`<div class="autonomy-empty">${automations.length?"No automations match this filter.":"No saved automations yet."}</div>`;return}
    for(const item of visible.sort((left,right)=>Number(left.readiness?.ready!==false)-Number(right.readiness?.ready!==false)||String(left.name||"").localeCompare(String(right.name||"")))){
      const readiness=item.readiness||{},needed=readiness.requirements||[],card=document.createElement("article");card.className="autonomy-card automation-permission-card";card.dataset.tone=readiness.ready===false?"attention":"ready";
      const rows=needed.map(requirement=>{const name=entityLabel(requirement.entity_id)||requirement.entity_id,sources=(requirement.sources||[]).map(source=>permissionSourceLabels[source]||"Used by this automation").join(" · ");return `<div class="automation-permission-row" data-allowed="${requirement.allowed}"><span class="automation-permission-kind" aria-hidden="true">${requirement.permission==="control"?"⚡":"◉"}</span><div><strong>${esc(name)}</strong><small>${esc(requirement.entity_id)} · ${esc(sources)}</small></div><span class="automation-permission-state">${esc(permissionRequirementText(requirement))}</span></div>`}).join("");
      const empty='<div class="autonomy-empty">This automation does not use a Home Assistant sensor or device.</div>',status=readiness.ready===false?"Needs permission":"Ready";
      card.innerHTML=`<div class="automation-permission-card-head"><div><strong>${esc(item.name||"Unnamed automation")}</strong><small>${item.enabled?"Enabled":"Not enabled"}</small></div><span>${status}</span></div><div class="automation-permission-rows">${rows||empty}</div>${readiness.ready===false?`<div class="automation-permission-fix"><p>ZBRANO will not run a protected task until these permissions are fixed.</p><button type="button" data-permission-open-entities>Fix entity permissions</button></div>`:""}<button class="automation-permission-open" type="button" data-activity-open-automation="${esc(item.id)}">Open automation</button>`;root.appendChild(card);
    }
  }

  function renderRecovery(){
    const automations=state.automations||[],paused=automations.filter(item=>item.recovery_state?.circuit_open),affected=automations.filter(item=>{const recovery=item.recovery_state||{};return recovery.circuit_open||Number(recovery.recent_failures||0)>0||Number(recovery.recovery_resets||0)>0||["failed","paused_failure"].includes(item.status)});
    $("automation-recovery-paused").textContent=`${paused.length} paused`;
    const root=$("automation-recovery-list");root.replaceChildren();
    if(!affected.length){root.innerHTML='<div class="autonomy-empty">No automation failures need recovery. If repeated actions fail, ZBRANO will pause the affected rule here instead of continuing blindly.</div>';return}
    for(const item of affected.sort((left,right)=>Number(Boolean(right.recovery_state?.circuit_open))-Number(Boolean(left.recovery_state?.circuit_open))||Number(right.recovery_state?.last_failure_at||0)-Number(left.recovery_state?.last_failure_at||0))){
      const recovery=item.recovery_state||{},count=Number(recovery.recent_failures||0),limit=Math.max(1,Number(recovery.failure_limit||item.failure_limit||3)),open=Boolean(recovery.circuit_open),percent=Math.min(100,Math.round(count/limit*100)),lastFailure=Number(recovery.last_failure_at||0),retryAt=Number(recovery.retry_available_at||0),readiness=item.readiness||{},row=document.createElement("div");row.className="automation-recovery-row";row.dataset.tone=open?"paused":count?"warning":"recovered";
      const status=open?"Paused safely":count?"Still watching":"Recovered",failureText=count?`${count} of ${limit} failures in ${Number(recovery.window_minutes||60)} minutes`:`Failure count cleared${Number(recovery.recovery_resets||0)?` · ${Number(recovery.recovery_resets)} manual reset${Number(recovery.recovery_resets)===1?"":"s"}`:""}`,lastError=recovery.last_error||item.last_error||"No error detail was stored.",timing=open&&retryAt?`The pause clears automatically after ${new Date(retryAt*1000).toLocaleString()}, or you can reset it after reviewing the cause.`:count?`${Math.max(0,Number(recovery.remaining_before_pause??limit-count))} more failure${Number(recovery.remaining_before_pause??limit-count)===1?"":"s"} would pause this automation.`:"The automation can run under its existing branch authority.";
      row.innerHTML=`<div class="automation-recovery-title"><div><strong>${esc(item.name||"Unnamed automation")}</strong><small>${lastFailure?`Last failure ${new Date(lastFailure*1000).toLocaleString()}`:"Previous failure acknowledged"}</small></div><span>${esc(status)}</span></div><div class="automation-recovery-progress"><span style="width:${percent}%"></span></div><p><strong>${esc(failureText)}</strong> · ${esc(timing)}</p><details><summary>Failure detail</summary><small>${esc(lastError)}</small></details><div class="automation-recovery-actions"><button type="button" data-activity-open-automation="${esc(item.id)}">Open automation</button>${readiness.ready===false?'<button type="button" data-permission-open-entities>Review permissions</button>':""}${open?`<button type="button" data-auto-recover="${esc(item.id)}" data-recovery-label="${item.enabled?"Reset and resume watching":"Acknowledge failure"}">${item.enabled?"Reset and resume watching":"Acknowledge failure"}</button>`:""}</div>`;root.appendChild(row);
    }
  }

  const evaluationAttentionStates=new Set(["attention","reliability","tune","delivery"]);
  function renderEvaluation(){
    const automations=state.automations||[],evaluated=automations.filter(item=>Number(item.evaluation?.evidence_count||0)>0),attention=automations.filter(item=>evaluationAttentionStates.has(item.evaluation?.state)),learning=automations.filter(item=>(item.evaluation?.state||"learning")==="learning"),healthy=automations.filter(item=>item.evaluation?.state==="healthy"),filter=$("automation-results-filter").value||"all";
    $("automation-results-evaluated").textContent=String(evaluated.length);$("automation-results-attention").textContent=String(attention.length);$("automation-results-learning").textContent=String(learning.length);$("automation-results-healthy").textContent=String(healthy.length);
    const visible=automations.filter(item=>filter==="all"||(filter==="attention"&&evaluationAttentionStates.has(item.evaluation?.state))||(filter==="learning"&&(item.evaluation?.state||"learning")==="learning")||(filter==="healthy"&&item.evaluation?.state==="healthy")),root=$("automation-results-list");root.replaceChildren();
    if(!visible.length){root.innerHTML=`<div class="autonomy-empty">${automations.length?"No automations match this results filter.":"No saved automations yet."}</div>`;return}
    for(const item of visible.sort((left,right)=>Number(evaluationAttentionStates.has(right.evaluation?.state))-Number(evaluationAttentionStates.has(left.evaluation?.state))||Number(right.evaluation?.evidence_count||0)-Number(left.evaluation?.evidence_count||0))){
      const evaluation=item.evaluation||{},answered=Number(evaluation.answered||0),accepted=Number(evaluation.accepted||0),acceptance=evaluation.acceptance_rate==null?null:Math.round(Number(evaluation.acceptance_rate)*100),response=evaluation.response_rate==null?null:Math.round(Number(evaluation.response_rate)*100),row=document.createElement("div");row.className="automation-result-row";row.dataset.tone=evaluation.state||"learning";
      const suggestionLine=Number(evaluation.suggestions||0)?`${accepted} accepted or handled manually · ${Number(evaluation.dismissals||0)} Not now · ${Number(evaluation.expired||0)} unanswered`:`No suggestion responses yet`,actionLine=`${Number(evaluation.automatic_successes||0)} automatic successes · ${Number(evaluation.action_failures||0)} task failures · ${Number(evaluation.recent_completed_actions||0)} recent completed actions`,rates=answered?`<div class="automation-result-rate"><span><i style="width:${acceptance}%"></i></span><small>${acceptance}% accepted when answered${response==null?"":` · ${response}% response rate`}</small></div>`:"";
      row.innerHTML=`<div class="automation-result-title"><div><strong>${esc(item.name||"Unnamed automation")}</strong><small>${Number(evaluation.evidence_count||0)} recorded outcome${Number(evaluation.evidence_count||0)===1?"":"s"} · ${Number(evaluation.recent_matches||0)} recent match${Number(evaluation.recent_matches||0)===1?"":"es"}</small></div><span>${esc(evaluation.headline||"Still learning")}</span></div>${rates}<p>${esc(suggestionLine)}</p><p>${esc(actionLine)}</p><div class="automation-result-recommendation">${esc(evaluation.recommendation||"Let this automation run longer before changing it.")}</div><button type="button" data-activity-open-automation="${esc(item.id)}">Open automation</button>`;root.appendChild(row);
    }
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
    const root=$("automation-library"),all=state.automations||[],query=$("automation-library-search").value.trim().toLowerCase(),filter=$("automation-library-filter").value,sort=$("automation-library-sort").value;root.replaceChildren();root.classList.add("is-compact");
    const searchable=item=>[item.name,item.objective,item.trigger_entity,item.action_entity,item.action_service,item.proposal_template,...(item.signal_entities||[]),...(item.triggers||[]).flatMap(part=>[part.entity_id,part.kind]),...(item.conditions||[]).flatMap(part=>[part.entity_id,part.compare_entity_id,part.compare_attribute,part.kind]),...(item.actions||[]).flatMap(part=>[part.entity_id,part.service,part.kind]),...(item.branches||[]).flatMap(branch=>[branch.name,branch.suggestion,...(branch.conditions||[]).flatMap(part=>[part.entity_id,part.compare_entity_id,part.compare_attribute]),...(branch.actions||[]).flatMap(part=>[part.entity_id,part.service])])].filter(Boolean).join(" ").toLowerCase();
    const matchesFilter=item=>{if(filter==="active")return Boolean(item.enabled);if(filter==="attention")return automationNeedsAttention(item);if(filter==="disabled")return !item.enabled;if(filter==="autonomous")return automationHasAutonomousPath(item);if(filter==="watch")return item.kind==="notification_watch";return true};
    const attentionScore=item=>Number(automationNeedsAttention(item));
    const summary={all:all.length,active:all.filter(item=>item.enabled).length,attention:all.filter(automationNeedsAttention).length,disabled:all.filter(item=>!item.enabled).length,autonomous:all.filter(automationHasAutonomousPath).length};
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
      const tags=[item.source==="chat"?"Chat prepared":null,isWatch?(item.status||"armed"):(item.enabled?(item.status||"armed"):item.review_required?"Review before turning on":"Off"),automationAuthorityLabel(item),`${Math.round(Number(item.confidence_threshold||0)*100)}% sure`,`Waits ${item.cooldown_minutes} min before repeating`,riskLabel(item.risk_level)].filter(Boolean);
      const feedback=item.feedback_memory||{},feedbackTotal=Number(feedback.dismissals||0)+Number(feedback.approvals||0)+Number(feedback.manual_resolutions||0)+Number(feedback.expired_suggestions||0)+Number(feedback.action_failures||0)+Number(feedback.autonomous_successes||0),resetLearning=feedbackTotal?`<button type="button" data-auto-reset-learning="${esc(item.id)}">Reset learning</button>`:"";
      const recovery=item.recovery_state||{},recoverAction=recovery.circuit_open?`<button type="button" data-auto-recover="${esc(item.id)}">Reset recovery</button>`:"";
      const primaryAction=isWatch?`<button type="button" data-auto-watch="${esc(item.id)}">Notifications</button>`:item.review_required?`<button type="button" data-auto-edit="${esc(item.id)}">Review</button><button type="button" data-auto-activate="${esc(item.id)}">Enable</button>`:`<button type="button" data-auto-edit="${esc(item.id)}">Edit</button>${item.enabled?`<button type="button" data-auto-pause="${esc(item.id)}">Pause</button>`:`<button type="button" data-auto-activate="${esc(item.id)}" data-auto-activation-label="Resume">Resume</button>`}`;
      const triggerSummary=`${entityLabel(item.trigger_entity)||"Nothing selected"} ${(item.trigger_operator||"").replaceAll("_"," ")}${item.trigger_value?` ${item.trigger_value}`:""}${item.trigger_for_seconds?` for ${item.trigger_for_seconds}s`:""}`;
      const actionSummary=item.action_service&&item.action_entity?`${entityLabel(item.action_entity)} — ${actionLabel(item.action_service)}`:"Only show the message";
      row.innerHTML=`<div class="autonomy-draft-head"><div><strong>${esc(item.name)}</strong><div>${esc(item.objective)}</div></div><div class="autonomy-draft-actions">${primaryAction}<button type="button" data-auto-duplicate="${esc(item.id)}">Duplicate</button>${recoverAction}${resetLearning}<button type="button" data-auto-delete="${esc(item.id)}">Delete</button></div></div><div class="autonomy-tags">${tags.map(tag=>`<span>${esc(tag)}</span>`).join("")}</div>`;
      const flow=flowElement(item);
      const flowDisclosure=document.createElement("details");flowDisclosure.className="automation-library-flow";flowDisclosure.innerHTML='<summary><span class="automation-library-flow-arrow" aria-hidden="true">›</span><span>View flow diagram</span></summary>';
      if(flow)flowDisclosure.append(flow);else flowDisclosure.insertAdjacentHTML("beforeend",`<small><strong>When:</strong> ${esc(triggerSummary)}<br><strong>Then:</strong> ${esc(item.proposal_template||"Record the match")}<br><strong>Action:</strong> ${esc(actionSummary)}<br><strong>Presence:</strong> ${esc(item.presence_entity||"not required by this rule")}</small>`);row.append(flowDisclosure);
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

  function renderAll(){renderSummary();renderSuggestions();renderContext();renderLibrary();renderAutomationMemory();renderAutomationBrain();renderActivity();renderPermissions();renderRecovery();renderEvaluation();renderTimeline();renderSettings()}

  async function loadEntityContext(){
    const root=$("autonomy-context");root.innerHTML='<div class="autonomy-empty">Loading Home Assistant context…</div>';
    try{
      const data=await api("api/ha/entities");entityMap=new Map((data.entities||[]).map(item=>[item.entity_id,item]));
      const options=$("automation-entity-options");options.replaceChildren();
      for(const entity of data.entities||[]){const option=document.createElement("option");option.value=entity.entity_id;option.label=entity.friendly_name||entity.entity_id;options.appendChild(option)}
      renderContext();renderLibrary();renderPermissions();renderEditorFlow();
    }catch(error){root.innerHTML=`<div class="autonomy-empty">Context unavailable: ${esc(error.message||error)}</div>`}
  }

  async function loadWorkspace(){state=await api("api/automations");try{notificationState=await api("api/notifications")}catch(_error){notificationState={channels:[]}}renderAll();await loadEntityContext()}

  function editorSnapshot(){
    const trigger={kind:$("automation-trigger-kind").value,entity_id:$("automation-trigger-entity").value.trim(),operator:$("automation-trigger-operator").value,value:$("automation-trigger-value").value.trim(),for_seconds:Number($("automation-trigger-for").value||0),at:$("automation-trigger-at").value,weekdays:parseWeekdays($("automation-trigger-weekdays").value),sun_event:$("automation-trigger-sun-event").value,offset_minutes:Number($("automation-trigger-sun-offset").value||0),interval_minutes:Number($("automation-trigger-interval").value||5),one_time_at:$("automation-trigger-one-time").value};
    const action={kind:"service",entity_id:$("automation-action-entity").value.trim(),service:$("automation-action-service").value.trim(),service_data:{},delay_seconds:0,wait_operator:"equals",wait_value:"",timeout_seconds:30};
    return {
      name:$("automation-name").value.trim()||"New automation",
      objective:$("automation-objective").value.trim(),
      presence_entity:presenceEntity(),
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
      branches:workflowDraft.branches.map(branch=>({...branch,name:(branch.name||"Outcome").trim(),execution_policy:branchExecutionPolicy(branch),suggestion:branchHasMessage(branch)?String(branch.suggestion||"").trim():"",message_enabled:branchHasMessage(branch),condition_mode:"all",delivery_voice:branchDeliveryValue(branch,"delivery_voice"),delivery_notification_center:branchDeliveryValue(branch,"delivery_notification_center"),delivery_ha_push:branchDeliveryValue(branch,"delivery_ha_push"),conditions:(branch.conditions||[]).filter(item=>(item.kind||"entity")!=="entity"||item.entity_id),actions:(branch.actions||[]).filter(actionStepValid)})),
    };
  }

  function editorValidationIssues(){
    const issues=[],add=(kind,message,field)=>issues.push({kind,message,field});
    const name=$("automation-name").value.trim(),objective=$("automation-objective").value.trim();
    if(name.length<2)add("details",name?"Use at least 2 characters for the automation name":"Give this automation a name","automation-name");
    if(objective.length<3)add("details",objective?"Use at least 3 characters to describe what it should help with":"Say what you want this automation to help with","automation-objective");
    if($("automation-require-presence").checked&&!$("automation-presence").value.trim())add("details","Choose who must be present","automation-presence");
    const validateTrigger=(item,primary=false)=>{const kind=item.kind||"entity",prefix=primary?"When":"Another When step";if(kind==="entity"&&!item.entity_id)add("trigger",`${prefix}: choose a device or sensor`,primary?"automation-trigger-entity":null);else if(kind==="time"&&!item.at)add("trigger",`${prefix}: choose a time`,primary?"automation-trigger-at":null);else if(kind==="interval"&&Number(item.interval_minutes)<1)add("trigger",`${prefix}: choose how often it repeats`,primary?"automation-trigger-interval":null);else if(kind==="one_time"&&!item.one_time_at)add("trigger",`${prefix}: choose a date and time`,primary?"automation-trigger-one-time":null)};
    validateTrigger({kind:$("automation-trigger-kind").value,entity_id:$("automation-trigger-entity").value.trim(),at:$("automation-trigger-at").value,interval_minutes:Number($("automation-trigger-interval").value||0),one_time_at:$("automation-trigger-one-time").value},true);
    for(const trigger of workflowDraft.triggers)validateTrigger(trigger);
    if(workflowDraft.trigger_mode==="all"){
      const allTriggers=[{kind:$("automation-trigger-kind").value,operator:$("automation-trigger-operator").value},...workflowDraft.triggers];
      if(allTriggers.some(item=>(item.kind||"entity")!=="entity"))add("trigger","With ALL, use only device or sensor changes. Use ANY when a time or schedule is included.");
      if(allTriggers.some(item=>(item.operator||"changes_to")==="any_change"))add("trigger","With ALL, each device needs a value or threshold to wait for.");
    }
    const validateCondition=(condition,issueKind="context",prefix="Check")=>{const kind=condition.kind||"entity";if(["entity","entity_compare"].includes(kind)&&!condition.entity_id)add(issueKind,`${prefix}: choose a device or sensor`);else if(kind==="entity_compare"&&!condition.compare_entity_id)add(issueKind,`${prefix}: choose the other device or sensor`);else if(kind==="time_window"&&(!condition.start_time||!condition.end_time))add(issueKind,`${prefix}: choose both times`);else if(kind==="weekday"&&!(condition.weekdays||[]).length)add(issueKind,`${prefix}: choose at least one day`)};
    for(const condition of workflowDraft.conditions)validateCondition(condition);
    const primaryEntity=$("automation-action-entity").value.trim(),primaryService=$("automation-action-service").value.trim();if(Boolean(primaryEntity)!==Boolean(primaryService))add("action","Choose both the device and what it should do",primaryEntity?"automation-action-service":"automation-action-entity");
    try{const data=JSON.parse($("automation-action-data").value||"{}");if(!data||Array.isArray(data)||typeof data!=="object")throw new Error()}catch(_error){add("action","The extra action details have an invalid format","automation-action-data")}
    const validateAction=(item,issueKind="action",prefix="Task")=>{const kind=item.kind||"service";if(kind==="service"&&(!validEntityId(item.entity_id)||!item.service))add(issueKind,`${prefix}: select a complete device name and choose what it should do`);else if(kind==="notification"&&(!validEntityId(item.entity_id)||!item.notification_message))add(issueKind,`${prefix}: choose where to send it and enter a message`);else if(kind==="delay"&&Number(item.delay_seconds)<1)add(issueKind,`${prefix}: wait for at least one second`);else if(kind==="wait_state"&&!validEntityId(item.entity_id))add(issueKind,`${prefix}: choose a device or sensor`)};
    for(const action of workflowDraft.actions)validateAction(action);
    for(const [branchIndex,branch] of workflowDraft.branches.entries()){const pathName=branchIndex?"ELSE IF":"IF";if(branch.message_enabled&&!String(branch.suggestion||"").trim())add("decision",`${pathName} message task: write its message`);for(const condition of branch.conditions||[])validateCondition(condition,"decision",`${pathName} check`);for(const action of branch.actions||[])validateAction(action,"decision",`${pathName} task`)}
    return issues;
  }
  function renderEditorValidation(){
    const issues=editorValidationIssues(),root=$("automation-studio-validation");root.hidden=!issues.length;root.replaceChildren();
    if(issues.length){const title=document.createElement("strong");title.textContent=`${issues.length} item${issues.length===1?"":"s"} to review`;root.append(title);for(const issue of issues){const button=document.createElement("button");button.type="button";button.dataset.validationKind=issue.kind;button.dataset.validationField=issue.field||"";button.textContent=issue.message;root.append(button)}}
    const kinds=new Set(issues.map(issue=>issue.kind));for(const node of $("automation-flow-preview").querySelectorAll("[data-flow-kind]")){const flowKind=node.dataset.flowKind,isBranchCard=["branch-action","branch-condition","branch-message"].includes(flowKind),invalid=isBranchCard?branchCardNeedsAttention(flowKind,Number(node.dataset.flowIndex),Number(node.dataset.flowBranchIndex)):kinds.has(flowKind);node.classList.toggle("has-validation-error",invalid);node.setAttribute("aria-invalid",String(invalid))}
    updateStudioGuide(issues);
    return issues;
  }
  function updateStudioGuide(issues){
    const needs=new Set(issues.map(issue=>issue.kind));
    const contextCount=(presenceEntity()?1:0)+$("automation-signals").value.split(/[,\n]/).map(value=>value.trim()).filter(Boolean).length+workflowDraft.conditions.length;
    const primaryTask=Boolean($("automation-action-entity").value.trim()||$("automation-action-service").value.trim()),taskCount=(primaryTask?1:0)+workflowDraft.actions.length;
    const states={
      details:needs.has("details")?["Needs attention",false,true]:["Ready",true,false],
      trigger:needs.has("trigger")?["Needs attention",false,true]:["Ready",true,false],
      context:needs.has("context")?["Needs attention",false,true]:[contextCount?`${contextCount} check${contextCount===1?"":"s"}`:"Optional",Boolean(contextCount),false],
      action:needs.has("action")?["Needs attention",false,true]:[taskCount?`${taskCount} task${taskCount===1?"":"s"}`:"Optional — message only",Boolean(taskCount),false],
      decision:needs.has("decision")?["Needs attention",false,true]:[workflowDraft.branches.length?`${workflowDraft.branches.length} outcome${workflowDraft.branches.length===1?"":"s"}`:"Optional",Boolean(workflowDraft.branches.length),false],
    };
    for(const button of panel.querySelectorAll(".automation-studio-preview [data-studio-node]")){const [message,complete,attention]=states[button.dataset.studioNode]||["Optional",false,false],status=button.querySelector("[data-studio-step-status]");if(status)status.textContent=message;button.classList.toggle("is-complete",complete);button.classList.toggle("is-needs-attention",attention);button.setAttribute("aria-label",`${button.querySelector("strong")?.textContent||"Step"}: ${message}`)}
    const requiredMissing=["details","trigger"].filter(kind=>needs.has(kind)).length;$("automation-studio-required-progress").textContent=requiredMissing?`${requiredMissing} required step${requiredMissing===1?"":"s"} left`:`Required steps ready`;
  }
  function focusEditorIssue(issue){selectStudioNode(issue.kind);const field=issue.field?$("studio-"+issue.field):null;(field||$("automation-studio-inspector-fields").querySelector("input,select,textarea"))?.focus()}

  function renderEditorFlow(){
    const snapshot=editorSnapshot(),root=$("automation-flow-preview");
    const primaryTrigger={kind:$("automation-trigger-kind").value,entity_id:$("automation-trigger-entity").value.trim(),operator:$("automation-trigger-operator").value,value:$("automation-trigger-value").value.trim(),for_seconds:Number($("automation-trigger-for").value||0),at:$("automation-trigger-at").value,weekdays:parseWeekdays($("automation-trigger-weekdays").value),sun_event:$("automation-trigger-sun-event").value,offset_minutes:Number($("automation-trigger-sun-offset").value||0),interval_minutes:Number($("automation-trigger-interval").value||5),one_time_at:$("automation-trigger-one-time").value};
    const primaryAction={kind:"service",entity_id:$("automation-action-entity").value.trim(),service:$("automation-action-service").value.trim(),service_data:{}};
    const visualSnapshot={...snapshot,studio_visual_draft:true,trigger_mode:workflowDraft.trigger_mode,triggers:[primaryTrigger,...cloneEditorValue(workflowDraft.triggers)],conditions:cloneEditorValue(workflowDraft.conditions),actions:[...(primaryAction.entity_id||primaryAction.service?[primaryAction]:[]),...cloneEditorValue(workflowDraft.actions)],branches:cloneEditorValue(workflowDraft.branches)};
    window.zbranoAutomationFlow?.render(root,visualSnapshot,entityLabel,entityVisual);
    const actualContextCount=(snapshot.presence_entity?1:0)+(snapshot.signal_entities||[]).length+(visualSnapshot.conditions||[]).length,actualDecisionCount=(visualSnapshot.branches||[]).length,actualActionCount=(visualSnapshot.actions||[]).length;
    for(const card of root?.querySelectorAll("[data-flow-kind]")||[]){
      const kind=card.dataset.flowKind,index=Number(card.dataset.flowIndex),branchIndex=card.hasAttribute("data-flow-branch-index")?Number(card.dataset.flowBranchIndex):null,deletable=kind==="trigger"?(index>0||primaryTrigger.kind!=="entity"||Boolean(primaryTrigger.entity_id)):kind==="context"?index<actualContextCount:kind==="decision"?index<actualDecisionCount:kind==="action"?index<actualActionCount:kind==="branch-message"?branchHasMessage(visualSnapshot.branches?.[branchIndex]):kind==="branch-action"?Boolean(visualSnapshot.branches?.[branchIndex]?.actions?.[index]):kind==="branch-condition"?Boolean(visualSnapshot.branches?.[branchIndex]?.conditions?.[index]):false;
      if(deletable&&kind!=="decision"){
        const controls=document.createElement("span");controls.className="automation-flow-card-actions";
        const duplicate=document.createElement("button");duplicate.type="button";duplicate.className="automation-flow-card-duplicate";duplicate.dataset.flowDuplicateKind=kind;duplicate.dataset.flowDuplicateIndex=String(index);if(branchIndex!=null)duplicate.dataset.flowBranchIndex=String(branchIndex);duplicate.setAttribute("aria-label",`Duplicate ${kind} card ${index+1}`);duplicate.title=kind==="context"&&contextFlowSource(index).type==="presence"?"Presence is unique":"Duplicate card";duplicate.textContent="⧉";if(kind==="context"&&contextFlowSource(index).type==="presence")duplicate.disabled=true;
        const remove=document.createElement("button");remove.type="button";remove.className="automation-flow-card-delete";remove.dataset.flowDeleteKind=kind;remove.dataset.flowDeleteIndex=String(index);if(branchIndex!=null)remove.dataset.flowBranchIndex=String(branchIndex);remove.setAttribute("aria-label",`Delete ${kind} card ${index+1}`);remove.title="Delete card";remove.textContent="×";if(kind!=="branch-message")controls.append(duplicate);controls.append(remove);card.append(controls);if(kind!=="branch-message"){card.draggable=true;card.setAttribute("aria-grabbed","false")}
      }
      if(kind===selectedFlowCard.kind&&index===selectedFlowCard.index&&(!["branch-action","branch-condition","branch-message"].includes(kind)||branchIndex===selectedFlowCard.branchIndex))card.classList.add("is-selected");
    }
    $("automation-studio-flow-name").textContent=snapshot.name;
    for(const button of panel.querySelectorAll("[data-studio-node]"))button.classList.toggle("active",button.dataset.studioNode===selectedStudioNode);
    renderEditorValidation();
    updateEditorDirtyState();
  }

  function clearEditor(){
    $("automation-studio-test-results").hidden=true;
    $("automation-draft-form").reset();$("automation-edit-id").value="";$("automation-editor-title").textContent="New automation draft";$("automation-cancel-edit").hidden=true;$("automation-cooldown").value=String(state.settings?.default_cooldown_minutes||30);$("automation-confidence").value=String(state.settings?.minimum_confidence||0.75);$("automation-risk").value="controlled";$("automation-execution-policy").value="approval_required";$("automation-max-actions").value="2";$("automation-trigger-operator").value="changes_to";$("automation-trigger-for").value="0";$("automation-action-data").value="{}";$("automation-enabled").checked=false;$("automation-notify-action").checked=true;$("automation-reversible-only").checked=true;$("automation-delivery-voice").checked=true;$("automation-delivery-center").checked=true;$("automation-delivery-push").checked=true;$("automation-draft-state").textContent="";
    $("automation-risk").value="informational";
    $("automation-require-presence").checked=false;$("automation-presence").value="";
    $("automation-suggestion-timeout").value="30";
    $("automation-failure-limit").value="3";$("automation-failure-window").value="60";
    $("automation-reoffer-delta").value="0";$("automation-reset-delta").value="0";
    $("automation-sleep-hours-enabled").checked=false;$("automation-sleep-hours-start").value="22:00";$("automation-sleep-hours-end").value="07:00";$("automation-run-during-sleep-hours").checked=false;
    $("automation-trigger-kind").value="entity";$("automation-trigger-at").value="";$("automation-trigger-weekdays").value="";$("automation-trigger-sun-event").value="sunrise";$("automation-trigger-sun-offset").value="0";$("automation-trigger-interval").value="5";$("automation-trigger-one-time").value="";
    workflowDraft={triggers:[],trigger_mode:"any",conditions:[],condition_mode:"all",actions:[],branches:[]};selectedStudioNode="details";selectedFlowCard={kind:"details",index:0};renderEditorFlow();renderStudioInspector();resetEditorHistory();
  }

  function fillEditor(item){
    $("automation-suggestion-timeout").value=String(item.suggestion_timeout_minutes||30);
    $("automation-failure-limit").value=String(item.failure_limit||3);$("automation-failure-window").value=String(item.failure_window_minutes||60);
    $("automation-reoffer-delta").value=String(item.reoffer_delta||0);$("automation-reset-delta").value=String(item.reset_delta||0);
    $("automation-edit-id").value=item.id||"";$("automation-name").value=item.name||"";$("automation-objective").value=item.objective||"";$("automation-presence").value=item.presence_entity||"";$("automation-require-presence").checked=Boolean(item.presence_entity);$("automation-signals").value=(item.signal_entities||[]).join(", ");$("automation-trigger-entity").value=item.trigger_entity||(item.signal_entities||[])[0]||"";$("automation-trigger-operator").value=item.trigger_operator||"changes_to";$("automation-trigger-value").value=item.trigger_value||"";$("automation-trigger-for").value=String(item.trigger_for_seconds||0);$("automation-enabled").checked=Boolean(item.enabled);$("automation-sleep-hours-enabled").checked=Boolean(item.sleep_hours_enabled);$("automation-sleep-hours-start").value=item.sleep_hours_start||"22:00";$("automation-sleep-hours-end").value=item.sleep_hours_end||"07:00";$("automation-run-during-sleep-hours").checked=Boolean(item.run_during_sleep_hours);$("automation-context-notes").value=item.context_notes||"";$("automation-proposal").value=item.proposal_template||"";$("automation-action-entity").value=item.action_entity||"";$("automation-action-service").value=item.action_service||"";$("automation-action-data").value=JSON.stringify(item.action_service_data||{},null,2);$("automation-cooldown").value=String(item.cooldown_minutes||30);$("automation-confidence").value=String(item.confidence_threshold||0.75);$("automation-risk").value=item.risk_level||"controlled";$("automation-execution-policy").value=item.execution_policy||"inherit";$("automation-max-actions").value=String(item.max_actions_per_hour||2);$("automation-notify-action").checked=item.notify_on_action!==false;$("automation-reversible-only").checked=item.reversible_only!==false;$("automation-delivery-voice").checked=item.delivery_voice!==false;$("automation-delivery-center").checked=item.delivery_notification_center!==false;$("automation-delivery-push").checked=item.delivery_ha_push!==false;$("automation-editor-title").textContent=item.id?"Edit automation":"New automation";$("automation-cancel-edit").hidden=!item.id;showView("studio");showLibraryView("create");document.querySelector(".automation-advanced")?.removeAttribute("open");selectedStudioNode="details";
    $("automation-risk").value=item.risk_level==="informational"?"informational":"controlled";
    const triggers=Array.isArray(item.triggers)&&item.triggers.length?item.triggers:[{kind:"entity",entity_id:item.trigger_entity||"",operator:item.trigger_operator||"changes_to",value:item.trigger_value||"",for_seconds:item.trigger_for_seconds||0}],primary=triggers[0]||{};$("automation-trigger-kind").value=primary.kind||"entity";$("automation-trigger-entity").value=primary.entity_id||"";$("automation-trigger-operator").value=primary.operator||"changes_to";$("automation-trigger-value").value=primary.value||"";$("automation-trigger-for").value=String(primary.for_seconds||0);$("automation-trigger-at").value=primary.at||"";$("automation-trigger-weekdays").value=formatWeekdays(primary.weekdays);$("automation-trigger-sun-event").value=primary.sun_event||"sunrise";$("automation-trigger-sun-offset").value=String(primary.offset_minutes||0);$("automation-trigger-interval").value=String(primary.interval_minutes||5);$("automation-trigger-one-time").value=primary.one_time_at||"";const actions=Array.isArray(item.actions)?item.actions:[],legacyPrimary=actions[0]&&(actions[0].kind||"service")==="service";if(!legacyPrimary){$("automation-action-entity").value="";$("automation-action-service").value="";$("automation-action-data").value="{}"}workflowDraft={triggers:triggers.slice(1),trigger_mode:item.trigger_mode==="all"?"all":"any",conditions:Array.isArray(item.conditions)?item.conditions:[],condition_mode:item.condition_mode||"all",actions:legacyPrimary?actions.slice(1):actions,branches:Array.isArray(item.branches)?item.branches.map(branch=>({...branch,execution_policy:branch.execution_policy==="autonomous"?"autonomous":"approval_required",message_enabled:Object.hasOwn(branch,"message_enabled")?branch.message_enabled:Boolean(String(branch.suggestion||"").trim()),condition_mode:"all",delivery_voice:Object.hasOwn(branch,"delivery_voice")?branch.delivery_voice:item.delivery_voice!==false,delivery_notification_center:Object.hasOwn(branch,"delivery_notification_center")?branch.delivery_notification_center:item.delivery_notification_center!==false,delivery_ha_push:Object.hasOwn(branch,"delivery_ha_push")?branch.delivery_ha_push:item.delivery_ha_push!==false})):[]};
    workflowDraft.branches.forEach((branch,index)=>{if(!item.branches?.[index]?.execution_policy)branch.execution_policy=item.execution_policy==="autonomous"?"autonomous":"approval_required"});renderEditorFlow();renderStudioInspector();resetEditorHistory();
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
  $("automation-library-search").addEventListener("input",renderLibrary);
  $("automation-library-filter").addEventListener("change",()=>{persistLibraryPrefs();renderLibrary()});
  $("automation-library-sort").addEventListener("change",()=>{persistLibraryPrefs();renderLibrary()});
  $("automation-activity-automation-filter").addEventListener("change",renderActivity);
  $("automation-activity-result-filter").addEventListener("change",renderActivity);
  $("automation-results-filter").addEventListener("change",renderEvaluation);
  $("automation-activity-refresh").addEventListener("click",()=>loadWorkspace().catch(error=>{$("automation-decision-feed").innerHTML=`<div class="autonomy-empty">Activity refresh failed: ${esc(error.message||error)}</div>`}));
  $("automation-permission-filter").addEventListener("change",renderPermissions);
  $("automation-permission-refresh").addEventListener("click",()=>loadWorkspace().catch(error=>{$("automation-permission-list").innerHTML=`<div class="autonomy-empty">Permission check failed: ${esc(error.message||error)}</div>`}));
  $("automation-library-summary").addEventListener("click",event=>{const button=event.target.closest("[data-library-quick-filter]");if(!button)return;$("automation-library-filter").value=button.dataset.libraryQuickFilter;persistLibraryPrefs();renderLibrary()});
  panel.addEventListener("pointerdown",event=>{if(event.target.closest(".automation-flow-card-actions"))return;const block=event.target.closest(".automation-studio-preview [data-flow-kind]");if(block&&!block.draggable)selectStudioNode(block.dataset.flowKind,Number(block.dataset.flowIndex),block.hasAttribute("data-flow-branch-index")?Number(block.dataset.flowBranchIndex):null)},{capture:true});
  panel.addEventListener("click",async event=>{
    const toolTrigger=event.target.closest("[data-tool-trigger]");if(toolTrigger){addToolbarTrigger(toolTrigger.dataset.toolTrigger);return}
    const entityPermissions=event.target.closest("[data-permission-open-entities]");if(entityPermissions){document.getElementById("entities-tab")?.click();return}
    const activityAutomation=event.target.closest("[data-activity-open-automation]");if(activityAutomation){const item=state.automations.find(value=>value.id===activityAutomation.dataset.activityOpenAutomation);if(item&&confirmEditorReplacement("open this automation")){fillEditor(item);showView("studio")}return}
    const toolCondition=event.target.closest("[data-tool-condition]");if(toolCondition){addToolbarCondition(toolCondition.dataset.toolCondition);return}
    const toolAction=event.target.closest("[data-tool-action]");if(toolAction){addToolbarAction(toolAction.dataset.toolAction);return}
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
    const activateDraft=event.target.closest("[data-auto-activate]");if(activateDraft){const item=state.automations.find(value=>value.id===activateDraft.dataset.autoActivate),verb=activateDraft.dataset.autoActivationLabel||"Turn on",trigger=`${entityLabel(item?.trigger_entity)||""} ${(item?.trigger_operator||"").replaceAll("_"," ")} ${item?.trigger_value||""}`.trim(),action=item?.branches?.length?`${item.branches.length} possible outcomes`:item?.action_service&&item?.action_entity?`${entityLabel(item.action_entity)} — ${actionLabel(item.action_service)}`:"only show the message";if(!item||!confirm(`${verb} ${item.name}?\n\nWhen: ${trigger}\nThen: ${action}\nBranch behavior: ${automationAuthorityLabel(item)}\nWait before repeating: ${item.cooldown_minutes} minutes\n\nThis automation will start watching immediately.`))return;activateDraft.disabled=true;try{await api(`api/automations/${encodeURIComponent(item.id)}/activate`,{method:"POST"});await loadWorkspace()}catch(error){alert(`Activation failed: ${error.message||error}`);activateDraft.disabled=false}return}
    const pause=event.target.closest("[data-auto-pause]");if(pause){const item=state.automations.find(value=>value.id===pause.dataset.autoPause);if(!item||!confirm(`Pause ${item.name}?\n\nLive evaluation and new actions will stop immediately. The rule and its history will be preserved.`))return;pause.disabled=true;try{await api(`api/automations/${encodeURIComponent(item.id)}/pause`,{method:"POST"});await loadWorkspace()}catch(error){alert(`Pause failed: ${error.message||error}`);pause.disabled=false}return}
    const forgetMemory=event.target.closest("[data-automation-memory-forget]");if(forgetMemory){if(!confirm("Forget this automation entity mapping? Existing rules will not be changed."))return;await api(`api/automations/entity-memory/${encodeURIComponent(forgetMemory.dataset.automationMemoryForget)}`,{method:"DELETE"});await loadWorkspace();return}
    const resetLearning=event.target.closest("[data-auto-reset-learning]");if(resetLearning){if(!confirm("Reset learned feedback for this automation? Its configured rule and episode history will remain."))return;resetLearning.disabled=true;try{await api(`api/automations/${encodeURIComponent(resetLearning.dataset.autoResetLearning)}/feedback`,{method:"DELETE"});await loadWorkspace()}catch(error){alert(`Learning reset failed: ${error.message||error}`);resetLearning.disabled=false}return}
    const recover=event.target.closest("[data-auto-recover]");if(recover){const label=recover.dataset.recoveryLabel||"Reset recovery";if(!confirm(`${label}?\n\nPrevious failures remain in the audit history. ZBRANO will still enforce this automation's permissions and branch authority before any task runs.`))return;recover.disabled=true;try{await api(`api/automations/${encodeURIComponent(recover.dataset.autoRecover)}/recover`,{method:"POST"});await loadWorkspace()}catch(error){alert(`Recovery reset failed: ${error.message||error}`);recover.disabled=false}return}
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
    const body={name:$("automation-name").value.trim(),objective:$("automation-objective").value.trim(),presence_entity:presenceEntity(),signal_entities:$("automation-signals").value.split(/[,\n]/).map(v=>v.trim()).filter(Boolean),trigger_entity:$("automation-trigger-entity").value.trim(),trigger_operator:$("automation-trigger-operator").value,trigger_value:$("automation-trigger-value").value.trim(),trigger_for_seconds:Number($("automation-trigger-for").value||0),enabled:$("automation-enabled").checked,sleep_hours_enabled:$("automation-sleep-hours-enabled").checked,sleep_hours_start:$("automation-sleep-hours-start").value||"22:00",sleep_hours_end:$("automation-sleep-hours-end").value||"07:00",run_during_sleep_hours:$("automation-run-during-sleep-hours").checked,context_notes:$("automation-context-notes").value.trim(),proposal_template:$("automation-proposal").value.trim(),action_entity:$("automation-action-entity").value.trim(),action_service:$("automation-action-service").value.trim(),action_service_data:actionData,cooldown_minutes:Number($("automation-cooldown").value),confidence_threshold:Number($("automation-confidence").value),risk_level:$("automation-risk").value,execution_policy:$("automation-execution-policy").value,delivery_voice:$("automation-delivery-voice").checked,delivery_notification_center:$("automation-delivery-center").checked,delivery_ha_push:$("automation-delivery-push").checked,notify_on_action:$("automation-notify-action").checked,reversible_only:$("automation-reversible-only").checked,max_actions_per_hour:Number($("automation-max-actions").value)};
    body.suggestion_timeout_minutes=Number($("automation-suggestion-timeout").value||30);body.failure_limit=Number($("automation-failure-limit").value||3);body.failure_window_minutes=Number($("automation-failure-window").value||60);body.reoffer_delta=Number($("automation-reoffer-delta").value||0);body.reset_delta=Number($("automation-reset-delta").value||0);const workflow=editorSnapshot();if(workflow.actions.length&&workflow.actions[0].entity_id===body.action_entity)workflow.actions[0].service_data=actionData;Object.assign(body,{triggers:workflow.triggers,trigger_mode:workflow.trigger_mode,conditions:workflow.conditions,condition_mode:workflow.condition_mode,actions:workflow.actions,branches:workflow.branches});return body;
  }

  function renderTestTrace(result){
    const root=$("automation-studio-test-results");root.hidden=false;root.innerHTML=(result.trace||[]).map(step=>`<article class="automation-studio-test-step" data-status="${esc(step.status)}"><strong>${esc(step.title)} · ${esc(step.status)}</strong><small>${esc(step.detail)}</small></article>`).join("");
    for(const node of $("automation-flow-preview").querySelectorAll("[data-flow-kind]")){node.classList.remove("is-test-pass","is-test-fail","is-test-waiting");const kind=node.dataset.flowKind==="branch-action"?"action":["branch-condition","branch-message"].includes(node.dataset.flowKind)?"decision":node.dataset.flowKind,step=(result.trace||[]).find(item=>item.kind===kind);if(step&&["pass","fail","waiting"].includes(step.status))node.classList.add(`is-test-${step.status}`)}
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
  $("automation-studio-step-back").addEventListener("click",()=>moveThroughStudio(-1));
  $("automation-studio-step-next").addEventListener("click",()=>moveThroughStudio(1));
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
  $("automation-studio-canvas").addEventListener("drop",event=>{event.preventDefault();let transferred=null;try{transferred=JSON.parse(event.dataTransfer?.getData("application/x-zbrano-flow-card")||"null")}catch(_error){}const source=draggedFlowCard||transferred,target=flowDropPosition(event,source?.kind),kind=event.dataTransfer?.getData("text/studio-node")||draggedStudioNode;clearFlowDropTarget();draggedStudioNode="";draggedFlowCard=null;if(source){if(target?.kind==="branch-action"&&["action","branch-action"].includes(source.kind))moveActionToBranch(source,target);else if(target?.kind==="branch-condition"&&source.kind==="branch-condition")moveBranchCondition(source,target);else if(target&&source.kind===target.kind)moveFlowCard(source.kind,source.index,target.index);else $("automation-studio-state").textContent="Move cards within the same step, or move checks and tasks into an outcome.";return}if(kind==="action"&&target?.kind==="branch-action")addBranchAction(target.branchIndex,target.index);else if(kind==="context"&&target?.kind==="branch-condition")addBranchCondition(target.branchIndex,target.index);else addStudioBlock(kind,target&&target.kind===kind?target.index:null)});
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

  document.addEventListener("click",event=>{const other=event.target.closest?.("#chat-tab,#entities-tab,#settings-tab,#plugins-tab,#files-tab,#contacts-tab,#calendar-tab,#developer-tab");if(other){panel.classList.add("hidden");tab.classList.remove("active")}},true);
  tab.addEventListener("click",event=>{event.preventDefault();event.stopImmediatePropagation();activate();loadWorkspace().catch(error=>{$("autonomy-context").innerHTML=`<div class="autonomy-empty">Automation workspace unavailable: ${esc(error.message||error)}</div>`})},true);
  const libraryPrefs=readLibraryPrefs();$("automation-library-filter").value=libraryPrefs.filter;$("automation-library-sort").value=libraryPrefs.sort;const localDraftRecovery=readLocalEditorDraft();clearEditor();if(localDraftRecovery)recoverLocalEditorDraft(localDraftRecovery);
  window.zbranoAutomationWorkspace={ready:true,load:loadWorkspace,showView};
})();
