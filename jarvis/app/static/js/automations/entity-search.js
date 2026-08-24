(() => {
  const ids=["automation-presence","automation-signals","automation-trigger-entity","automation-action-entity","autonomy-presence-entity"];
  const inputs=ids.map(id=>document.getElementById(id)).filter(Boolean);
  if(!inputs.length)return;
  let entities=null,loading=null,openPicker=null;
  const normalize=value=>String(value??"").trim().toLowerCase();
  async function loadEntities(){
    if(entities)return entities;
    if(loading)return loading;
    loading=fetch("api/ha/entities",{cache:"no-store"}).then(async response=>{
      const data=await response.json().catch(()=>({}));
      if(!response.ok)throw new Error(data.detail||`HTTP ${response.status}`);
      entities=(data.entities||[]).map(item=>({
        id:String(item.entity_id||""),
        name:String(item.friendly_name||item.attributes?.friendly_name||item.entity_id||""),
        state:String(item.state??""),
      })).filter(item=>item.id).sort((a,b)=>a.name.localeCompare(b.name)||a.id.localeCompare(b.id));
      return entities;
    }).finally(()=>{loading=null});
    return loading;
  }
  function queryFor(input){
    if(input.id!=="automation-signals")return normalize(input.value);
    return normalize(input.value.split(",").pop());
  }
  function choose(input,item){
    if(input.id==="automation-signals"){
      const parts=input.value.split(",").map(value=>value.trim()).filter(Boolean);
      if(parts.length&&normalize(parts[parts.length-1])===queryFor(input))parts.pop();
      if(!parts.includes(item.id))parts.push(item.id);
      input.value=parts.join(", ")+(parts.length?", ":"");
    }else input.value=item.id;
    input.dispatchEvent(new Event("change",{bubbles:true}));
    close(input);input.focus();
  }
  function close(input){
    const picker=input?input._zbranoEntityPicker:openPicker;
    if(!picker)return;
    picker.hidden=true;picker.input.setAttribute("aria-expanded","false");
    if(openPicker===picker)openPicker=null;
  }
  function render(input){
    const picker=input._zbranoEntityPicker;if(!picker||!entities)return;
    const query=queryFor(input);
    const matches=entities.filter(item=>!query||normalize(`${item.name} ${item.id} ${item.state}`).includes(query)).slice(0,40);
    picker.replaceChildren();picker.active=-1;
    if(!matches.length){const empty=document.createElement("div");empty.className="automation-entity-empty";empty.textContent="No matching Home Assistant entities.";picker.appendChild(empty);}
    for(const item of matches){
      const option=document.createElement("button");option.type="button";option.className="automation-entity-result";option.setAttribute("role","option");option.dataset.entityId=item.id;
      const name=document.createElement("strong");name.textContent=item.name;
      const detail=document.createElement("small");detail.textContent=`${item.id}${item.state?` · ${item.state}`:""}`;
      option.append(name,detail);option.addEventListener("pointerdown",event=>{event.preventDefault();choose(input,item)});picker.appendChild(option);
    }
    picker.hidden=false;input.setAttribute("aria-expanded","true");openPicker=picker;
  }
  async function open(input){
    if(openPicker&&openPicker!==input._zbranoEntityPicker)close();
    const picker=input._zbranoEntityPicker;picker.hidden=false;picker.replaceChildren();
    const loadingRow=document.createElement("div");loadingRow.className="automation-entity-empty";loadingRow.textContent="Loading entities…";picker.appendChild(loadingRow);
    input.setAttribute("aria-expanded","true");openPicker=picker;
    try{await loadEntities();render(input)}catch(error){loadingRow.textContent=`Entity list unavailable: ${error.message||error}`}
  }
  function move(input,direction){
    const picker=input._zbranoEntityPicker,options=[...picker.querySelectorAll(".automation-entity-result")];if(!options.length)return;
    picker.active=(picker.active+direction+options.length)%options.length;
    options.forEach((option,index)=>option.dataset.active=String(index===picker.active));options[picker.active].scrollIntoView({block:"nearest"});
  }
  for(const input of inputs){
    input.removeAttribute("list");input.autocomplete="off";input.setAttribute("role","combobox");input.setAttribute("aria-autocomplete","list");input.setAttribute("aria-expanded","false");
    input.placeholder=input.id==="automation-signals"?"Type a name or entity ID, then select multiple":"Type a name or entity ID to search";
    const host=input.parentElement;host?.classList.add("automation-entity-picker-host");
    const picker=document.createElement("div");picker.className="automation-entity-results";picker.hidden=true;picker.setAttribute("role","listbox");picker.input=input;picker.active=-1;input._zbranoEntityPicker=picker;host?.appendChild(picker);
    input.addEventListener("focus",()=>open(input));input.addEventListener("input",()=>{if(entities)render(input);else open(input)});
    input.addEventListener("keydown",event=>{
      if(event.key==="ArrowDown"||event.key==="ArrowUp"){event.preventDefault();if(picker.hidden)open(input);else move(input,event.key==="ArrowDown"?1:-1);}
      else if(event.key==="Enter"&&!picker.hidden&&picker.active>=0){event.preventDefault();picker.querySelectorAll(".automation-entity-result")[picker.active]?.dispatchEvent(new PointerEvent("pointerdown"));}
      else if(event.key==="Escape")close(input);
    });
  }
  document.addEventListener("pointerdown",event=>{if(openPicker&&!openPicker.contains(event.target)&&event.target!==openPicker.input)close()});
})();
