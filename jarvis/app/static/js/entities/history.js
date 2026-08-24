(() => {
  const panel=document.getElementById("entities-panel");
  const form=document.getElementById("ha-history-form");
  if(!panel||!form)return;
  const $=id=>document.getElementById(id);
  const esc=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"})[char]);
  const tabs=[...panel.querySelectorAll("[data-entity-view]")];
  const views=[...panel.querySelectorAll("[data-entity-view-panel]")];

  function showView(name){
    for(const tab of tabs){const active=tab.dataset.entityView===name;tab.classList.toggle("active",active);tab.setAttribute("aria-selected",String(active));}
    for(const view of views)view.classList.toggle("hidden",view.dataset.entityViewPanel!==name);
  }
  tabs.forEach(tab=>tab.addEventListener("click",()=>showView(tab.dataset.entityView)));

  async function api(path){const response=await fetch(path,{cache:"no-store"});const data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(data.detail||`HTTP ${response.status}`);return data;}
  function selectedEntities(){return [...new Set($("ha-history-entities").value.split(",").map(value=>value.trim().toLowerCase()).filter(Boolean))];}
  function metric(label,value){return `<span>${esc(label)} <b>${esc(value??"—")}</b></span>`;}

  function renderSummaries(series){
    const root=$("ha-history-summaries");root.replaceChildren();
    for(const item of series||[]){const summary=item.summary||{};const node=document.createElement("article");node.className="ha-history-summary";
      const metrics=[metric("Latest",`${summary.last_state??"—"}${summary.unit?` ${summary.unit}`:""}`),metric("Changes",summary.transitions),metric("Points",summary.point_count),metric("Unavailable",summary.unavailable_points)];
      if(summary.numeric)metrics.push(metric("Trend",summary.trend),metric("Range",`${summary.minimum}–${summary.maximum}`),metric("Average",summary.average),metric("Possible jumps",summary.possible_anomaly_count));
      node.innerHTML=`<strong>${esc(summary.friendly_name||item.entity_id)}</strong><small>${esc(item.entity_id)}</small><div class="ha-history-summary-grid">${metrics.join("")}</div>`;root.appendChild(node);}
  }

  function renderCharts(series){
    const root=$("ha-history-charts");root.replaceChildren();
    for(const item of series||[]){const points=(item.points||[]).filter(point=>Number.isFinite(Number(point.numeric_value)));if(points.length<2)continue;
      const values=points.map(point=>Number(point.numeric_value)),minimum=Math.min(...values),maximum=Math.max(...values),span=maximum-minimum||1;
      const coordinates=values.map((value,index)=>`${(index/(values.length-1)*100).toFixed(2)},${(92-((value-minimum)/span)*84).toFixed(2)}`).join(" ");
      const node=document.createElement("article");node.className="ha-history-chart";node.innerHTML=`<div class="ha-history-chart-head"><strong>${esc(item.summary?.friendly_name||item.entity_id)}</strong><span>${esc(minimum)}–${esc(maximum)} ${esc(item.summary?.unit||"")}</span></div><svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="${esc(item.entity_id)} history trend"><line x1="0" y1="92" x2="100" y2="92"></line><line x1="0" y1="8" x2="100" y2="8"></line><polyline points="${coordinates}"></polyline></svg>`;root.appendChild(node);}
  }

  function renderEvents(events){
    const root=$("ha-timeline-events");root.replaceChildren();$("ha-history-event-count").textContent=`${events.length} bounded events`;
    if(!events.length){root.innerHTML='<div class="ha-history-empty">No matching history or logbook events in this period.</div>';return;}
    for(const event of events){const node=document.createElement("article");node.className="ha-timeline-event";node.dataset.source=event.source||"history";const when=new Date(event.when);node.innerHTML=`<time>${esc(Number.isNaN(when.getTime())?event.when:when.toLocaleString())}</time><strong>${esc(event.name||event.entity_id||"Home Assistant")}</strong><span>${esc(event.message||event.state||"")} <small class="ha-timeline-source">${esc(event.source||"")}</small></span>`;root.appendChild(node);}
  }

  async function loadTimeline(){
    const entities=selectedEntities();if(!entities.length){$("ha-history-status").textContent="Enter at least one approved entity ID.";return;}
    if(entities.length>8){$("ha-history-status").textContent="Select no more than eight entities.";return;}
    const hours=Number($("ha-history-hours").value||24),query=$("ha-history-query").value.trim();$("ha-history-status").textContent="Reading bounded Home Assistant history and logbook…";
    const data=await api(`api/ha/timeline?entity_ids=${encodeURIComponent(entities.join(","))}&hours=${hours}&query=${encodeURIComponent(query)}&limit=160`);
    renderSummaries(data.series||[]);renderCharts(data.series||[]);renderEvents(data.events||[]);
    const warning=(data.warnings||[]).length?` · ${data.warnings.join(" · ")}`:"";$("ha-history-status").textContent=`Read-only timeline loaded · ${data.entity_count||data.series?.length||entities.length} entities · ${data.hours} hours · ${data.event_count||0} events${data.live_event_count?` · ${data.live_event_count} live`:""}${data.truncated?" · bounded result":""}${warning}`;
  }
  form.addEventListener("submit",event=>{event.preventDefault();loadTimeline().catch(error=>{$("ha-history-status").textContent=`Timeline failed: ${error.message||error}`;});});
  $("ha-history-use-approved").addEventListener("click",async()=>{try{const data=await api("api/ha/approved");const ids=[...new Set([...(data.read_entities||[]),...(data.control_entities||[])])].slice(0,8);$("ha-history-entities").value=ids.join(", ");$("ha-history-status").textContent=ids.length?`${ids.length} approved entities selected.`:"No approved entities are available.";}catch(error){$("ha-history-status").textContent=`Could not load approved entities: ${error.message||error}`;}});
  window.zbranoHaHistory={show:()=>showView("history"),load:loadTimeline};
})();
