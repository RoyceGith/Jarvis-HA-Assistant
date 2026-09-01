"use strict";

(() => {
  const operatorLabels = {any_change:"changes",changes_to:"changes to",equals:"equals",not_equals:"does not equal",above:"rises above",below:"falls below"};
  const text = (value, fallback) => String(value ?? "").trim() || fallback;

  function node(kind,index,label,title,detail) {
    const element=document.createElement("section");element.className=`automation-flow-node is-${kind}`;element.dataset.flowKind=kind;element.dataset.flowIndex=String(index);element.tabIndex=0;element.setAttribute("role","button");element.setAttribute("aria-label",`Configure ${label.toLowerCase()} block ${index+1}`);
    const kicker=document.createElement("span");kicker.className="automation-flow-kicker";kicker.textContent=label;
    const heading=document.createElement("strong");heading.textContent=title;
    const description=document.createElement("small");description.textContent=detail;
    element.append(kicker,heading,description);return element;
  }
  function verticalConnector(){const element=document.createElement("span");element.className="automation-flow-stage-connector";element.setAttribute("aria-hidden","true");return element}
  function logicConnector(mode,interactive,type="trigger",branchIndex=null){
    const element=document.createElement("span");element.className="automation-flow-logic";const normalized=mode==="all"?"all":"any";
    if(!interactive){element.textContent=normalized==="all"?"AND":"OR";return element}
    const select=document.createElement("select");select.className="automation-flow-logic-select";select.dataset[type==="trigger"?"triggerLogic":type==="branch"?"branchConditionLogic":"conditionLogic"]="";if(type==="branch"&&branchIndex!=null)select.dataset.flowBranchIndex=String(branchIndex);select.setAttribute("aria-label",type==="trigger"?"Relationship between triggers":type==="branch"?"Relationship between conditions in this path":"Relationship between conditions");
    for(const [value,label] of [["any","OR"],["all","AND"]]){const option=document.createElement("option");option.value=value;option.textContent=label;option.selected=normalized===value;select.append(option)}element.append(select);return element;
  }
  function stage(kind,title,nodes,joinMode="",interactive=false){
    const section=document.createElement("section");section.className=`automation-flow-stage is-${kind}${nodes.length>2?" is-dense":""}`;section.dataset.flowCount=String(nodes.length);
    const heading=document.createElement("div");heading.className="automation-flow-stage-heading";heading.textContent=title;
    const row=document.createElement("div");row.className="automation-flow-node-row";
    nodes.forEach((item,index)=>{if(index)row.append(logicConnector(joinMode,interactive,kind==="trigger"?"trigger":"condition"));row.append(item)});section.append(heading,row);return section;
  }
  function triggerCard(item,index,entityName){
    const kind=item.kind||"entity";
    if(kind==="time")return node("trigger",index,`EVENT ${index+1}`,`At ${text(item.at,"a local time")}`,"Home Assistant local time");
    if(kind==="sun")return node("trigger",index,`EVENT ${index+1}`,`${item.sun_event||"sunrise"} ${Number(item.offset_minutes||0)>=0?"+":""}${Number(item.offset_minutes||0)} min`,"Sun event schedule");
    if(kind==="interval")return node("trigger",index,`EVENT ${index+1}`,`Every ${Number(item.interval_minutes||5)} min`,"Repeating schedule");
    if(kind==="one_time")return node("trigger",index,`EVENT ${index+1}`,text(item.one_time_at,"Choose a date and time"),"One-time schedule");
    const operator=operatorLabels[item.operator]||text(item.operator,"changes to"),value=text(item.value,"any value"),duration=Number(item.for_seconds||0);
    return node("trigger",index,`EVENT ${index+1}`,entityName(text(item.entity_id,"Choose a trigger entity")),`${operator} ${value}${duration?` for ${duration} seconds`:""}`);
  }
  function conditionCard(item,index,entityName){
    const kind=item.kind||"entity";
    if(kind==="time_window")return node("context",index,`CONDITION ${index+1}`,`${text(item.start_time,"start")} – ${text(item.end_time,"end")}`,"Local time window");
    if(kind==="weekday")return node("context",index,`CONDITION ${index+1}`,Array.isArray(item.weekdays)&&item.weekdays.length?`${item.weekdays.length} selected days`:"Choose weekdays","Calendar condition");
    if(kind==="sun")return node("context",index,`CONDITION ${index+1}`,`Sun is ${text(item.sun_state,"below horizon").replaceAll("_"," ")}`,"Home Assistant sun state");
    if(kind==="entity_compare"){
      const operator=operatorLabels[item.operator]||text(item.operator,"equals"),attribute=item.compare_attribute?` · ${item.compare_attribute}`:" · state";
      return node("context",index,`CONDITION ${index+1}`,entityName(text(item.entity_id,"Choose a source entity")),`${operator} ${entityName(text(item.compare_entity_id,"choose a comparison entity"))}${attribute}`);
    }
    const operator=operatorLabels[item.operator]||text(item.operator,"equals");return node("context",index,`CONDITION ${index+1}`,entityName(text(item.entity_id,"Choose a condition entity")),`${operator} ${text(item.value,"a value")}`);
  }
  function actionLabel(item,entityName){
    const kind=item.kind||"service";
    if(kind==="delay")return [`Delay ${Number(item.delay_seconds||0)||"?"}s`,"Pause the process"];
    if(kind==="wait_state")return [`Wait for ${item.entity_id?entityName(item.entity_id):"an entity"}`,`${text(item.wait_operator,"equals").replaceAll("_"," ")} ${text(item.wait_value,"a value")}`];
    if(kind==="notification")return [`Notify ${item.entity_id?entityName(item.entity_id):"a channel"}`,text(item.notification_message,"Write a notification message")];
    if(item.task_template==="set_temperature")return [item.entity_id?entityName(item.entity_id):"Choose a thermostat",`Set to ${Number(item.service_data?.temperature??22)}°`];
    if(item.task_template==="set_brightness")return [item.entity_id?entityName(item.entity_id):"Choose a light",`Brightness ${Number(item.service_data?.brightness_pct??70)}%`];
    if(item.task_template==="turn_on")return [item.entity_id?entityName(item.entity_id):"Choose a device","Power on"];
    if(item.task_template==="turn_off")return [item.entity_id?entityName(item.entity_id):"Choose a device","Power off"];
    if(item.task_template==="toggle")return [item.entity_id?entityName(item.entity_id):"Choose a device","Toggle power state"];
    return [item.entity_id?entityName(item.entity_id):"Choose an action entity",text(item.service,"Configure a service action")];
  }
  function branchStage(branches,entityName,interactive=false){
    const section=document.createElement("section");section.className=`automation-flow-stage is-decision is-branching${branches.length>2?" is-dense":""}`;section.dataset.flowCount=String(branches.length);
    const heading=document.createElement("div");heading.className="automation-flow-stage-heading";heading.textContent="CHOOSE THE FIRST MATCHING PATH";
    if(interactive){const addPath=document.createElement("button");addPath.type="button";addPath.className="automation-flow-add-path";addPath.dataset.flowAddBranch="";addPath.textContent="+ Path";heading.append(addPath)}
    const grid=document.createElement("div");grid.className="automation-flow-branch-grid";
    branches.forEach((branch,branchIndex)=>{
      const lane=document.createElement("section");lane.className="automation-flow-branch-lane";lane.dataset.flowBranchDrop=String(branchIndex);
      const conditions=(branch.conditions||[]).filter(item=>item&&typeof item==="object"),isElse=branchIndex===branches.length-1&&!conditions.length;
      if(interactive){const toolbar=document.createElement("div");toolbar.className="automation-flow-branch-toolbar";const label=document.createElement("span");label.textContent=isElse?"ELSE path":`Path ${branchIndex+1}`;toolbar.append(label);for(const [action,symbol,title,disabled] of [["previous","←",`Move ${label.textContent} left`,branchIndex===0||isElse],["next","→",`Move ${label.textContent} right`,branchIndex===branches.length-1||isElse||(branchIndex===branches.length-2&&!(branches.at(-1)?.conditions||[]).length)],["duplicate","⧉",`Duplicate ${label.textContent}`,branches.length>=10],["delete","×",`Delete ${label.textContent}`,branches.length===1]]){const button=document.createElement("button");button.type="button";button.dataset.flowBranchAction=action;button.dataset.flowBranchIndex=String(branchIndex);button.setAttribute("aria-label",title);button.title=title;button.textContent=symbol;button.disabled=disabled;toolbar.append(button)}lane.append(toolbar)}
      lane.append(node("decision",branchIndex,isElse?"ELSE":`PATH ${branchIndex+1}`,text(branch.name,`Branch ${branchIndex+1}`),conditions.length?`${conditions.length} visible condition${conditions.length===1?"":"s"}`:"Fallback path"));
      const conditionLane=document.createElement("div");conditionLane.className="automation-flow-branch-conditions";conditionLane.dataset.flowBranchConditionDrop=String(branchIndex);conditionLane.setAttribute("aria-label",`${text(branch.name,`Branch ${branchIndex+1}`)} conditions`);
      const conditionLabel=document.createElement("span");conditionLabel.className="automation-flow-branch-section-label";conditionLabel.textContent=isElse?"OTHERWISE":"IF";conditionLane.append(conditionLabel);
      if(conditions.length){conditions.forEach((item,itemIndex)=>{if(itemIndex)conditionLane.append(logicConnector(branch.condition_mode,true,"branch",branchIndex));const card=conditionCard(item,itemIndex,entityName);card.classList.remove("is-context");card.classList.add("is-branch-condition");card.dataset.flowKind="branch-condition";card.dataset.flowBranchIndex=String(branchIndex);card.dataset.flowItemIndex=String(itemIndex);card.querySelector(".automation-flow-kicker").textContent=`IF ${itemIndex+1}`;conditionLane.append(card)})}
      else{const empty=document.createElement("span");empty.className="automation-flow-branch-empty is-condition-empty";empty.textContent="ELSE — no conditions";conditionLane.append(empty)}
      if(interactive){const menu=document.createElement("details");menu.className="automation-flow-branch-condition-menu";const summary=document.createElement("summary");summary.textContent="+ IF condition";const choices=document.createElement("div");choices.className="automation-flow-branch-condition-choices";for(const [key,label] of [["entity","Entity state"],["entity_compare","Compare entities"],["time_window","Time window"],["weekday","Weekdays"],["sun","Sun state"]]){const button=document.createElement("button");button.type="button";button.dataset.flowBranchConditionTemplate=key;button.dataset.flowBranchIndex=String(branchIndex);if(key==="entity")button.dataset.flowBranchAddCondition=String(branchIndex);button.textContent=label;choices.append(button)}menu.append(summary,choices);conditionLane.append(menu)}
      lane.append(verticalConnector(),conditionLane,verticalConnector());
      const suggestion=document.createElement("div");suggestion.className="automation-flow-branch-suggestion";const suggestionLabel=document.createElement("span");suggestionLabel.className="automation-flow-branch-section-label";suggestionLabel.textContent="SUGGEST";const suggestionText=document.createElement("small");suggestionText.textContent=text(branch.suggestion,"Use the automation's default suggestion");suggestion.append(suggestionLabel,suggestionText);lane.append(suggestion,verticalConnector());
      const tasks=document.createElement("div");tasks.className="automation-flow-branch-actions";tasks.dataset.flowBranchActionDrop=String(branchIndex);tasks.setAttribute("aria-label",`${text(branch.name,`Branch ${branchIndex+1}`)} tasks`);
      const taskLabel=document.createElement("span");taskLabel.className="automation-flow-branch-section-label";taskLabel.textContent="THEN";tasks.append(taskLabel);
      const actions=(branch.actions||[]).filter(item=>item&&typeof item==="object");
      if(actions.length){actions.forEach((item,itemIndex)=>{const [title,detail]=actionLabel(item,entityName),card=node("branch-action",itemIndex,`TASK ${itemIndex+1}`,title,detail);card.dataset.flowBranchIndex=String(branchIndex);card.dataset.flowItemIndex=String(itemIndex);tasks.append(card)})}
      else{const empty=document.createElement("span");empty.className="automation-flow-branch-empty";empty.textContent="Drop an Action here";tasks.append(empty)}
      if(interactive){const menu=document.createElement("details");menu.className="automation-flow-branch-task-menu";const summary=document.createElement("summary");summary.textContent="+ Task";const choices=document.createElement("div");choices.className="automation-flow-branch-task-choices";for(const [key,label] of [["turn_on","Power on"],["turn_off","Power off"],["toggle","Toggle"],["set_temperature","Set temperature"],["set_brightness","Set brightness"],["notification","Notification"],["delay","Delay"],["wait","Wait until"],["service","Custom service"]]){const button=document.createElement("button");button.type="button";button.dataset.flowBranchTaskTemplate=key;button.dataset.flowBranchIndex=String(branchIndex);button.textContent=label;choices.append(button)}menu.append(summary,choices);tasks.append(menu)}
      lane.append(tasks);grid.append(lane);
    });section.append(heading,grid);return section;
  }
  function create(automation={},entityName=value=>value){
    const flow=document.createElement("div");flow.className="automation-flow";flow.setAttribute("role","group");flow.setAttribute("aria-label",`${text(automation.name,"Automation")} visual flow`);const interactive=Boolean(automation.studio_visual_draft);
    let triggers=Array.isArray(automation.triggers)?automation.triggers.filter(item=>item&&typeof item==="object"):[];if(!triggers.length)triggers=[{kind:"entity",entity_id:automation.trigger_entity,operator:automation.trigger_operator,value:automation.trigger_value,for_seconds:automation.trigger_for_seconds}];
    flow.append(stage("trigger","WHEN THIS HAPPENS",triggers.map((item,index)=>triggerCard(item,index,entityName)),automation.trigger_mode,interactive));
    const contextNodes=[];if(automation.presence_entity)contextNodes.push(node("context",contextNodes.length,"CONTEXT",entityName(automation.presence_entity),"Presence must be confirmed"));for(const entityId of (automation.signal_entities||[]).filter(Boolean))contextNodes.push(node("context",contextNodes.length,"SIGNAL",entityName(entityId),"Supporting context signal"));for(const condition of (automation.conditions||[]).filter(item=>item&&typeof item==="object"))contextNodes.push(conditionCard(condition,contextNodes.length,entityName));if(!contextNodes.length)contextNodes.push(node("context",0,"CONTEXT","No extra condition","Continue when an event matches"));
    flow.append(verticalConnector(),stage("context","CHECK THESE CONDITIONS",contextNodes,automation.condition_mode,false));
    const branches=(automation.branches||[]).filter(item=>item&&typeof item==="object");
    if(branches.length){
      flow.append(verticalConnector(),branchStage(branches,entityName,interactive));
      let unassigned=(automation.actions||[]).filter(item=>item&&typeof item==="object");if(!unassigned.length&&automation.action_entity&&automation.action_service)unassigned=[{kind:"service",entity_id:automation.action_entity,service:automation.action_service}];
      if(unassigned.length){const nodes=unassigned.map((item,index)=>{const [title,detail]=actionLabel(item,entityName);return node("action",index,`UNASSIGNED ${index+1}`,title,detail)});flow.append(verticalConnector(),stage("action","UNASSIGNED TASKS — NOT RUN",nodes))}
    }
    else{
      flow.append(verticalConnector(),stage("decision","RUN THIS PROCESS",[node("decision",0,"PROCESS",text(automation.proposal_template,text(automation.objective,"Record the match")),`${Math.round(Number(automation.confidence_threshold??.75)*100)}% confidence · ${text(automation.execution_policy,"suggest").replaceAll("_"," ")}`)]));
      let actions=(automation.actions||[]).filter(item=>item&&typeof item==="object");if(!actions.length&&automation.action_entity&&automation.action_service)actions=[{kind:"service",entity_id:automation.action_entity,service:automation.action_service}];const actionNodes=actions.length?actions.map((item,index)=>{const [title,detail]=actionLabel(item,entityName);return node("action",index,`TASK ${index+1}`,title,detail)}):[node("action",0,"TASK","Suggestion only","No Home Assistant service call")];
      flow.append(verticalConnector(),stage("action","DO THESE TASKS",actionNodes));
    }return flow;
  }
  function render(root,automation,entityName){if(root)root.replaceChildren(create(automation,entityName))}
  window.zbranoAutomationFlow={create,render};
})();
