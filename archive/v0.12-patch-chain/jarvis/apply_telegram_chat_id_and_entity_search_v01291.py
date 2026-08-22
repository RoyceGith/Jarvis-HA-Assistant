import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.91 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.91 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        '{"target": int(chat_id), "message": part}',
        '{"chat_id": int(chat_id), "message": part}',
        "deprecated Telegram target payload",
    )

    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.91 could not locate stylesheet close")
    search_css = r'''
    /* v0.12.91 searchable Home Assistant entity pickers. */
    .automation-entity-picker-host { position:relative; }
    .automation-entity-results { position:absolute; z-index:90; top:calc(100% + .25rem); left:0; right:0; display:grid; max-height:15rem; overflow:auto; padding:.28rem; border:1px solid var(--cyan-dim); border-radius:7px; background:var(--surface-strong); box-shadow:0 .65rem 1.7rem rgba(0,0,0,.24); }
    .automation-entity-results[hidden] { display:none; }
    .automation-entity-result { display:grid; gap:.08rem; width:100%; padding:.42rem .5rem; border:0; border-radius:5px; background:transparent; color:var(--text); text-align:left; }
    .automation-entity-result:hover,.automation-entity-result:focus,.automation-entity-result[data-active="true"] { background:color-mix(in srgb,var(--cyan) 13%,transparent); outline:none; }
    .automation-entity-result strong { overflow-wrap:anywhere; font-size:.75rem; font-weight:620; }
    .automation-entity-result small { overflow-wrap:anywhere; color:var(--text-muted); font-size:.66rem; }
    .automation-entity-empty { padding:.55rem; color:var(--text-muted); font-size:.72rem; }
'''
    frontend = frontend[:style_close] + search_css + frontend[style_close:]

    body_close = frontend.rfind("</body>")
    if body_close < 0:
        raise RuntimeError("ZBRANO v0.12.91 could not locate body close")
    search_runtime = r'''
<script id="zbrano-v01291-automation-entity-search">
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
</script>
'''
    frontend = frontend[:body_close] + search_runtime + frontend[body_close:]

    backend = backend.replace('version="0.12.90"', 'version="0.12.91"')
    backend = backend.replace('"version": "0.12.90"', '"version": "0.12.91"')
    frontend = frontend.replace("HUD 0.12.90", "HUD 0.12.91")

    for marker, location in [
        ('version="0.12.91"', backend),
        ('{"chat_id": int(chat_id), "message": part}', backend),
        ('id="zbrano-v01291-automation-entity-search"', frontend),
        ('"automation-signals","automation-trigger-entity"', frontend),
        ('input.setAttribute("role","combobox")', frontend),
        ('HUD 0.12.91', frontend),
    ]:
        require(location, marker, marker)
    if '{"target": int(chat_id), "message": part}' in backend:
        raise RuntimeError("ZBRANO v0.12.91 still contains the deprecated Telegram reply target")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
