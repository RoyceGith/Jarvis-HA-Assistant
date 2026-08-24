(() => {
  const tab=document.getElementById("automations-tab");
  const panel=document.getElementById("automations-panel");
  if(!tab||!panel)return;
  const $=id=>document.getElementById(id);
  const esc=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"})[char]);
  let state={settings:{},automations:[],suggestions:[],timeline:[],entity_memory:[],area_context:{areas:[],entities:[]},patterns:[],discoveries:[],engine:{}};
  let entityMap=new Map();

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
  }

  function showLibraryView(name){
    for(const button of panel.querySelectorAll("[data-automation-library-view]")){const active=button.dataset.automationLibraryView===name;button.classList.toggle("active",active);button.setAttribute("aria-selected",String(active))}
    for(const view of panel.querySelectorAll("[data-automation-library-panel]")){view.classList.toggle("hidden",view.dataset.automationLibraryPanel!==name)}
  }

  function modeLabel(value){return ({observe_only:"Observe only",suggest_only:"Suggest only",approval_gated:"Approval-gated",selective_autonomy:"Selective autonomy"})[value]||"Suggest only"}
  function authorityLabel(value){return ({observe:"Observe only",suggest:"Suggest only",approval_required:"Approval required",autonomous:"Fully autonomous"})[value]||"Suggest only"}
  function renderSummary(){
    $("autonomy-engine-status").textContent=state.engine?.status==="active"?"Live":state.engine?.status==="waiting_for_home_assistant"?"Waiting for HA":"Unavailable";
    $("autonomy-mode-summary").textContent=modeLabel(state.settings?.operating_mode);
    $("autonomy-mode-detail").textContent=state.settings?.operating_mode==="selective_autonomy"?`Autonomous up to ${state.settings?.autonomous_risk_ceiling||"low"} risk`:"Per-automation authority limited by global policy";
    $("autonomy-draft-count").textContent=String(state.automations.length);
    $("autonomy-suggestion-count").textContent=String(state.suggestions.length);
  }

  function renderSuggestions(){
    const root=$("autonomy-suggestions");root.replaceChildren();
    const visible=(state.suggestions||[]).filter(item=>!["dismissed"].includes(item.status)).slice(0,30);
    if(!visible.length){root.innerHTML='<div class="autonomy-empty">No live automation suggestions yet.</div>';return}
    for(const item of visible){const row=document.createElement("div");row.className="autonomy-draft";const actionable=["pending","approval_required"].includes(item.status)&&item.action_service&&item.action_entity;const brain=item.source==="automation_brain";const actions=actionable?`<div class="autonomy-draft-actions"><button type="button" data-suggestion-approve="${esc(item.id)}">Approve action</button><button type="button" data-suggestion-dismiss="${esc(item.id)}">Not now</button>${brain?`<button type="button" data-discovery-feedback="never_suggest" data-discovery-id="${esc(item.discovery_id)}">Never suggest</button>`:""}</div>`:"";row.innerHTML=`<div class="autonomy-draft-head"><strong>${esc(item.title||"Suggestion")}</strong><span class="automation-state" data-state="${esc(item.status||"pending")}">${brain?"Brain discovery · ":""}${esc(item.status||"pending")}</span></div><span>${esc(item.detail||"")}</span>${item.evidence?`<small>Evidence: ${esc(item.evidence)}</small>`:""}${actions}`;root.appendChild(row)}
  }

  function referencedEntities(){
    const ids=new Set();
    if(state.settings?.presence_entity)ids.add(state.settings.presence_entity);
    for(const item of state.automations){if(item.presence_entity)ids.add(item.presence_entity);for(const id of item.signal_entities||[])ids.add(id);if(item.action_entity)ids.add(item.action_entity)}
    return [...ids];
  }

  function renderContext(){
    const root=$("autonomy-context");root.replaceChildren();const ids=referencedEntities();
    if(!ids.length){root.innerHTML='<div class="autonomy-empty">No entities referenced yet. Add a draft or set the default presence entity.</div>';return}
    for(const id of ids){const entity=entityMap.get(id);const row=document.createElement("div");row.className="autonomy-context-row";row.innerHTML=`<div class="autonomy-draft-head"><strong>${esc(entity?.friendly_name||id)}</strong><span>${esc(entity?.state??"not loaded")}</span></div><small>${esc(id)}${entity?.unit?` · ${esc(entity.unit)}`:""}</small>`;root.appendChild(row)}
  }

  function renderLibrary(){
    const root=$("automation-library");root.replaceChildren();
    if(!state.automations.length){root.innerHTML='<div class="autonomy-empty">No automation drafts. Start with a quick design or create your own.</div>';return}
    for(const item of state.automations){
      const row=document.createElement("div");row.className="autonomy-draft";
      const isWatch=item.kind==="notification_watch";
      const tags=[item.source==="chat"?"Chat prepared":null,isWatch?(item.status||"armed"):(item.enabled?(item.status||"armed"):item.review_required?"Review required":"Disabled"),authorityLabel(item.execution_policy),`${Math.round(Number(item.confidence_threshold||0)*100)}% confidence`,`${item.cooldown_minutes} min cooldown`,item.risk_level].filter(Boolean);
      const primaryAction=isWatch?`<button type="button" data-auto-watch="${esc(item.id)}">Notifications</button>`:item.review_required?`<button type="button" data-auto-edit="${esc(item.id)}">Review</button><button type="button" data-auto-activate="${esc(item.id)}">Enable</button>`:`<button type="button" data-auto-edit="${esc(item.id)}">Edit</button>`;
      const triggerSummary=`${item.trigger_entity||"no trigger"} ${(item.trigger_operator||"").replaceAll("_"," ")}${item.trigger_value?` ${item.trigger_value}`:""}${item.trigger_for_seconds?` for ${item.trigger_for_seconds}s`:""}`;
      const actionSummary=item.action_service&&item.action_entity?`${item.action_service} → ${item.action_entity}`:"No device action";
      row.innerHTML=`<div class="autonomy-draft-head"><div><strong>${esc(item.name)}</strong><div>${esc(item.objective)}</div></div><div class="autonomy-draft-actions">${primaryAction}<button type="button" data-auto-delete="${esc(item.id)}">Delete</button></div></div><div class="autonomy-tags">${tags.map(tag=>`<span>${esc(tag)}</span>`).join("")}</div><small><strong>When:</strong> ${esc(triggerSummary)}<br><strong>Then:</strong> ${esc(item.proposal_template||"Record the match")}<br><strong>Action:</strong> ${esc(actionSummary)}<br><strong>Presence:</strong> ${esc(item.presence_entity||"not required by this rule")}</small>`;
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
      renderContext();
    }catch(error){root.innerHTML=`<div class="autonomy-empty">Context unavailable: ${esc(error.message||error)}</div>`}
  }

  async function loadWorkspace(){state=await api("api/automations");renderAll();await loadEntityContext()}

  function clearEditor(){
    $("automation-draft-form").reset();$("automation-edit-id").value="";$("automation-editor-title").textContent="New automation draft";$("automation-cancel-edit").hidden=true;$("automation-cooldown").value=String(state.settings?.default_cooldown_minutes||30);$("automation-confidence").value=String(state.settings?.minimum_confidence||0.75);$("automation-risk").value="controlled";$("automation-execution-policy").value="suggest";$("automation-max-actions").value="2";$("automation-trigger-operator").value="changes_to";$("automation-trigger-for").value="0";$("automation-action-data").value="{}";$("automation-enabled").checked=false;$("automation-notify-action").checked=true;$("automation-reversible-only").checked=true;$("automation-draft-state").textContent="";
  }

  function fillEditor(item){
    $("automation-edit-id").value=item.id||"";$("automation-name").value=item.name||"";$("automation-objective").value=item.objective||"";$("automation-presence").value=item.presence_entity||"";$("automation-signals").value=(item.signal_entities||[]).join(", ");$("automation-trigger-entity").value=item.trigger_entity||(item.signal_entities||[])[0]||"";$("automation-trigger-operator").value=item.trigger_operator||"changes_to";$("automation-trigger-value").value=item.trigger_value||"";$("automation-trigger-for").value=String(item.trigger_for_seconds||0);$("automation-enabled").checked=Boolean(item.enabled);$("automation-context-notes").value=item.context_notes||"";$("automation-proposal").value=item.proposal_template||"";$("automation-action-entity").value=item.action_entity||"";$("automation-action-service").value=item.action_service||"";$("automation-action-data").value=JSON.stringify(item.action_service_data||{},null,2);$("automation-cooldown").value=String(item.cooldown_minutes||30);$("automation-confidence").value=String(item.confidence_threshold||0.75);$("automation-risk").value=item.risk_level||"controlled";$("automation-execution-policy").value=item.execution_policy||"suggest";$("automation-max-actions").value=String(item.max_actions_per_hour||2);$("automation-notify-action").checked=item.notify_on_action!==false;$("automation-reversible-only").checked=item.reversible_only!==false;$("automation-editor-title").textContent=item.id?"Edit automation":"New automation";$("automation-cancel-edit").hidden=!item.id;showView("library");showLibraryView("create");document.querySelector(".automation-advanced")?.setAttribute("open","");$("automation-name").focus();
  }

  function template(name){
    const presence=state.settings?.presence_entity||"binary_sensor.workshop_presence";
    const templates={
      comfort:{name:"Workshop comfort advisor",objective:"Notice uncomfortable temperature while I am present and propose an appropriate comfort action",presence_entity:presence,signal_entities:["sensor.workshop_temperature","sensor.outdoor_temperature","sensor.workshop_humidity"],context_notes:"Compare indoor temperature and trend with outdoor conditions, season, time of day, humidity, recent occupancy, and current HVAC state. Avoid reacting to brief sensor spikes.",proposal_template:"It is getting a little hot in the workshop. Would you like me to turn on the air conditioner?",action_entity:"climate.workshop",action_service:"climate.set_hvac_mode",cooldown_minutes:30,confidence_threshold:0.8,risk_level:"controlled",execution_policy:"approval_required",notify_on_action:true,reversible_only:true,max_actions_per_hour:2},
      air:{name:"Workshop air quality advisor",objective:"Notice worsening workshop air quality while occupied and suggest ventilation",presence_entity:presence,signal_entities:["sensor.workshop_co2","sensor.workshop_voc","sensor.workshop_pm25"],context_notes:"Use sustained readings and trends, not one sample. Consider active extraction and outdoor air quality.",proposal_template:"Air quality is getting worse in the workshop. Would you like me to start ventilation?",action_entity:"fan.workshop_extractor",action_service:"fan.turn_on",cooldown_minutes:20,confidence_threshold:0.82,risk_level:"controlled",execution_policy:"approval_required",notify_on_action:true,reversible_only:true,max_actions_per_hour:2},
      security:{name:"Workshop departure safety check",objective:"Notice when the workshop becomes unoccupied while an opening or selected equipment remains active",presence_entity:presence,signal_entities:["binary_sensor.workshop_door","binary_sensor.workshop_window","switch.workshop_equipment"],context_notes:"Require sustained absence and distinguish expected equipment from anything that should be switched off.",proposal_template:"It looks like the workshop is empty, but something may have been left open or running. Would you like a safety check?",action_entity:"",action_service:"",cooldown_minutes:30,confidence_threshold:0.9,risk_level:"high",execution_policy:"suggest",notify_on_action:true,reversible_only:true,max_actions_per_hour:1},
      lighting:{name:"Workshop presence lighting",objective:"Turn workshop lighting on when presence is confirmed and light is low",presence_entity:presence,signal_entities:["sensor.workshop_illuminance","light.workshop"],context_notes:"Require stable presence and low illuminance. Do nothing when daylight is sufficient or lighting is already on.",proposal_template:"Workshop lighting was turned on because presence and low light were confirmed.",action_entity:"light.workshop",action_service:"light.turn_on",cooldown_minutes:10,confidence_threshold:0.9,risk_level:"low",execution_policy:"autonomous",notify_on_action:true,reversible_only:true,max_actions_per_hour:4}
    };fillEditor(templates[name])
  }

  panel.querySelector(".autonomy-tabs")?.addEventListener("click",event=>{const button=event.target.closest("[data-auto-view]");if(button)showView(button.dataset.autoView)});
  panel.querySelector(".automation-library-tabs")?.addEventListener("click",event=>{const button=event.target.closest("[data-automation-library-view]");if(button)showLibraryView(button.dataset.automationLibraryView)});
  panel.addEventListener("click",async event=>{
    const templateButton=event.target.closest("[data-auto-template]");if(templateButton){template(templateButton.dataset.autoTemplate);return}
    const notificationWatch=event.target.closest("[data-auto-watch]");if(notificationWatch){showView("notifications");window.zbranoNotificationCenter?.showView("watchlist");window.zbranoNotificationCenter?.load();return}
    const approve=event.target.closest("[data-suggestion-approve]");if(approve){approve.disabled=true;try{await api(`api/automations/suggestions/${encodeURIComponent(approve.dataset.suggestionApprove)}/approve`,{method:"POST"});await loadWorkspace()}catch(error){alert(`Action failed: ${error.message||error}`);approve.disabled=false}return}
    const dismiss=event.target.closest("[data-suggestion-dismiss]");if(dismiss){dismiss.disabled=true;try{await api(`api/automations/suggestions/${encodeURIComponent(dismiss.dataset.suggestionDismiss)}/dismiss`,{method:"POST"});await loadWorkspace()}catch(error){alert(`Dismiss failed: ${error.message||error}`);dismiss.disabled=false}return}
    const discoveryFeedback=event.target.closest("[data-discovery-feedback]");if(discoveryFeedback){discoveryFeedback.disabled=true;try{await api(`api/automations/discoveries/${encodeURIComponent(discoveryFeedback.dataset.discoveryId)}/feedback`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({feedback:discoveryFeedback.dataset.discoveryFeedback})});await loadWorkspace()}catch(error){alert(`Learning feedback failed: ${error.message||error}`);discoveryFeedback.disabled=false}return}
    const edit=event.target.closest("[data-auto-edit]");if(edit){const item=state.automations.find(value=>value.id===edit.dataset.autoEdit);if(item)fillEditor(item);return}
    const activateDraft=event.target.closest("[data-auto-activate]");if(activateDraft){const item=state.automations.find(value=>value.id===activateDraft.dataset.autoActivate),trigger=`${item?.trigger_entity||""} ${(item?.trigger_operator||"").replaceAll("_"," ")} ${item?.trigger_value||""}`.trim(),action=item?.action_service&&item?.action_entity?`${item.action_service} → ${item.action_entity}`:"no device action";if(!item||!confirm(`Enable ${item.name}?\n\nWhen: ${trigger}\nAction: ${action}\nAuthority: ${authorityLabel(item.execution_policy)}\nCooldown: ${item.cooldown_minutes} minutes\n\nLive evaluation begins immediately.`))return;activateDraft.disabled=true;try{await api(`api/automations/${encodeURIComponent(item.id)}/activate`,{method:"POST"});await loadWorkspace()}catch(error){alert(`Activation failed: ${error.message||error}`);activateDraft.disabled=false}return}
    const forgetMemory=event.target.closest("[data-automation-memory-forget]");if(forgetMemory){if(!confirm("Forget this automation entity mapping? Existing rules will not be changed."))return;await api(`api/automations/entity-memory/${encodeURIComponent(forgetMemory.dataset.automationMemoryForget)}`,{method:"DELETE"});await loadWorkspace();return}
    const remove=event.target.closest("[data-auto-delete]");if(remove){if(!confirm("Delete this automation draft?"))return;await api(`api/automations/${encodeURIComponent(remove.dataset.autoDelete)}`,{method:"DELETE"});await loadWorkspace()}
  });

  $("automation-chat-builder-form").addEventListener("submit",event=>{
    event.preventDefault();const request=$("automation-chat-request").value.trim();if(!request)return;
    const chatTab=document.getElementById("chat-tab"),chatInput=document.getElementById("message"),chatForm=document.getElementById("chat-form");
    if(!chatTab||!chatInput||!chatForm){$("automation-chat-builder-status").textContent="Chat is unavailable.";return}
    chatTab.click();chatInput.value=request;chatInput.dispatchEvent(new Event("input",{bubbles:true}));chatForm.requestSubmit();
  });

  $("automation-draft-form").addEventListener("submit",async event=>{
    event.preventDefault();const id=$("automation-edit-id").value;const status=$("automation-draft-state");status.textContent="Saving…";
    let actionData={};try{actionData=JSON.parse($("automation-action-data").value||"{}");if(!actionData||Array.isArray(actionData)||typeof actionData!=="object")throw new Error("must be an object")}catch(error){status.textContent=`Action data must be valid JSON: ${error.message||error}`;return}
    const body={name:$("automation-name").value.trim(),objective:$("automation-objective").value.trim(),presence_entity:$("automation-presence").value.trim(),signal_entities:$("automation-signals").value.split(/[,\n]/).map(v=>v.trim()).filter(Boolean),trigger_entity:$("automation-trigger-entity").value.trim(),trigger_operator:$("automation-trigger-operator").value,trigger_value:$("automation-trigger-value").value.trim(),trigger_for_seconds:Number($("automation-trigger-for").value||0),enabled:$("automation-enabled").checked,context_notes:$("automation-context-notes").value.trim(),proposal_template:$("automation-proposal").value.trim(),action_entity:$("automation-action-entity").value.trim(),action_service:$("automation-action-service").value.trim(),action_service_data:actionData,cooldown_minutes:Number($("automation-cooldown").value),confidence_threshold:Number($("automation-confidence").value),risk_level:$("automation-risk").value,execution_policy:$("automation-execution-policy").value,notify_on_action:$("automation-notify-action").checked,reversible_only:$("automation-reversible-only").checked,max_actions_per_hour:Number($("automation-max-actions").value)};
    try{await api(id?`api/automations/${encodeURIComponent(id)}`:"api/automations",{method:id?"PUT":"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});clearEditor();await loadWorkspace();showLibraryView("saved")}catch(error){status.textContent=`Save failed: ${error.message||error}`}
  });
  $("automation-cancel-edit").addEventListener("click",clearEditor);
  $("autonomy-settings-form").addEventListener("submit",async event=>{
    event.preventDefault();const status=$("autonomy-settings-state");status.textContent="Saving…";const mode=panel.querySelector('input[name="autonomy-mode"]:checked')?.value||"suggest_only";
    const body={operating_mode:mode,presence_entity:$("autonomy-presence-entity").value.trim(),require_presence:$("autonomy-require-presence").checked,respect_quiet_hours:$("autonomy-respect-quiet").checked,minimum_confidence:Number($("autonomy-min-confidence").value),default_cooldown_minutes:Number($("autonomy-default-cooldown").value),autonomous_risk_ceiling:$("autonomy-risk-ceiling").value,notify_after_autonomous_action:$("autonomy-notify-autonomous").checked,passive_learning_enabled:$("autonomy-passive-learning").checked};
    try{await api("api/automations/settings",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});status.textContent="Authority policy saved.";await loadWorkspace()}catch(error){status.textContent=`Save failed: ${error.message||error}`}
  });
  $("autonomy-refresh-context").addEventListener("click",loadEntityContext);

  document.addEventListener("click",event=>{const other=event.target.closest?.("#chat-tab,#entities-tab,#settings-tab,#plugins-tab,#files-tab,#calendar-tab,#developer-tab");if(other){panel.classList.add("hidden");tab.classList.remove("active")}},true);
  tab.addEventListener("click",event=>{event.preventDefault();event.stopImmediatePropagation();activate();loadWorkspace().catch(error=>{$("autonomy-context").innerHTML=`<div class="autonomy-empty">Automation workspace unavailable: ${esc(error.message||error)}</div>`})},true);
  clearEditor();
  window.zbranoAutomationWorkspace={ready:true,load:loadWorkspace,showView};
})();
