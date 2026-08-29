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
  function logicConnector(mode,interactive,type="trigger"){
    const element=document.createElement("span");element.className="automation-flow-logic";const normalized=mode==="all"?"all":"any";
    if(!interactive){element.textContent=normalized==="all"?"AND":"OR";return element}
    const select=document.createElement("select");select.className="automation-flow-logic-select";select.dataset[type==="trigger"?"triggerLogic":"conditionLogic"]="";select.setAttribute("aria-label",type==="trigger"?"Relationship between triggers":"Relationship between conditions");
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
    const operator=operatorLabels[item.operator]||text(item.operator,"equals");return node("context",index,`CONDITION ${index+1}`,entityName(text(item.entity_id,"Choose a condition entity")),`${operator} ${text(item.value,"a value")}`);
  }
  function actionLabel(item,entityName){
    const kind=item.kind||"service";
    if(kind==="delay")return [`Delay ${Number(item.delay_seconds||0)||"?"}s`,"Pause the process"];
    if(kind==="wait_state")return [`Wait for ${item.entity_id?entityName(item.entity_id):"an entity"}`,`${text(item.wait_operator,"equals").replaceAll("_"," ")} ${text(item.wait_value,"a value")}`];
    if(kind==="notification")return [`Notify ${item.entity_id?entityName(item.entity_id):"a channel"}`,text(item.notification_message,"Write a notification message")];
    if(item.task_template==="turn_on")return [item.entity_id?entityName(item.entity_id):"Choose a device","Power on"];
    if(item.task_template==="turn_off")return [item.entity_id?entityName(item.entity_id):"Choose a device","Power off"];
    if(item.task_template==="toggle")return [item.entity_id?entityName(item.entity_id):"Choose a device","Toggle power state"];
    return [item.entity_id?entityName(item.entity_id):"Choose an action entity",text(item.service,"Configure a service action")];
  }
  function create(automation={},entityName=value=>value){
    const flow=document.createElement("div");flow.className="automation-flow";flow.setAttribute("role","group");flow.setAttribute("aria-label",`${text(automation.name,"Automation")} visual flow`);const interactive=Boolean(automation.studio_visual_draft);
    let triggers=Array.isArray(automation.triggers)?automation.triggers.filter(item=>item&&typeof item==="object"):[];if(!triggers.length)triggers=[{kind:"entity",entity_id:automation.trigger_entity,operator:automation.trigger_operator,value:automation.trigger_value,for_seconds:automation.trigger_for_seconds}];
    flow.append(stage("trigger","WHEN THIS HAPPENS",triggers.map((item,index)=>triggerCard(item,index,entityName)),automation.trigger_mode,interactive));
    const contextNodes=[];if(automation.presence_entity)contextNodes.push(node("context",contextNodes.length,"CONTEXT",entityName(automation.presence_entity),"Presence must be confirmed"));for(const entityId of (automation.signal_entities||[]).filter(Boolean))contextNodes.push(node("context",contextNodes.length,"SIGNAL",entityName(entityId),"Supporting context signal"));for(const condition of (automation.conditions||[]).filter(item=>item&&typeof item==="object"))contextNodes.push(conditionCard(condition,contextNodes.length,entityName));if(!contextNodes.length)contextNodes.push(node("context",0,"CONTEXT","No extra condition","Continue when an event matches"));
    flow.append(verticalConnector(),stage("context","CHECK THESE CONDITIONS",contextNodes,automation.condition_mode,false));
    const branches=(automation.branches||[]).filter(item=>item&&typeof item==="object"),decisionNodes=branches.length?branches.map((branch,index)=>node("decision",index,index===branches.length-1&&!(branch.conditions||[]).length?"ELSE":`PATH ${index+1}`,text(branch.name,`Branch ${index+1}`),`${(branch.conditions||[]).length} condition${(branch.conditions||[]).length===1?"":"s"} · ${(branch.actions||[]).length} task${(branch.actions||[]).length===1?"":"s"}`)):[node("decision",0,"PROCESS",text(automation.proposal_template,text(automation.objective,"Record the match")),`${Math.round(Number(automation.confidence_threshold??.75)*100)}% confidence · ${text(automation.execution_policy,"suggest").replaceAll("_"," ")}`)];
    flow.append(verticalConnector(),stage("decision",branches.length?"CHOOSE THE FIRST MATCHING PATH":"RUN THIS PROCESS",decisionNodes));
    let actions=(automation.actions||[]).filter(item=>item&&typeof item==="object");if(!actions.length&&automation.action_entity&&automation.action_service)actions=[{kind:"service",entity_id:automation.action_entity,service:automation.action_service}];const actionNodes=actions.length?actions.map((item,index)=>{const [title,detail]=actionLabel(item,entityName);return node("action",index,`TASK ${index+1}`,title,detail)}):[node("action",0,"TASK","Suggestion only","No Home Assistant service call")];
    flow.append(verticalConnector(),stage("action","DO THESE TASKS",actionNodes));return flow;
  }
  function render(root,automation,entityName){if(root)root.replaceChildren(create(automation,entityName))}
  window.zbranoAutomationFlow={create,render};
})();
