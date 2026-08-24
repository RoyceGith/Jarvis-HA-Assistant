var pluginsTab=document.getElementById("plugins-tab"),pluginsPanel=document.getElementById("plugins-panel"),pluginList=document.getElementById("plugin-list")||(() => {
  const fallback=document.createElement("div");
  fallback.id="plugin-list";
  fallback.className="muted";
  fallback.textContent="No plugins loaded.";
  (document.getElementById("plugins-panel")||document.body).appendChild(fallback);
  return fallback;
})(),pluginName=document.getElementById("plugin-name"),pluginUrl=document.getElementById("plugin-url"),pluginToken=document.getElementById("plugin-token"),installPlugin=document.getElementById("install-plugin"),pluginState=document.getElementById("plugin-state");
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"})[c]);
async function pApi(path,options={}){const r=await fetch(path,options),d=await r.json().catch(()=>({}));if(!r.ok){const detail=typeof d.detail==="string"?d.detail:(d.detail?JSON.stringify(d.detail):"");throw new Error(detail||`HTTP ${r.status}`)}return d}
function ensurePluginDomReady(){
  const panel=document.getElementById("plugins-panel")||document.body;
  if(!document.getElementById("plugin-list")){
    const node=document.createElement("div");
    node.id="plugin-list";
    node.className="muted";
    node.textContent="No plugins loaded.";
    panel.appendChild(node);
  }
  if(!document.getElementById("catalog-status")){
    const node=document.createElement("div");
    node.id="catalog-status";
    node.setAttribute("role","status");
    panel.appendChild(node);
  }
  if(!document.getElementById("catalog-results")){
    const node=document.createElement("div");
    node.id="catalog-results";
    node.className="catalog-grid";
    panel.appendChild(node);
  }
}

function currentPluginList(){
  ensurePluginDomReady();
  return document.getElementById("plugin-list");
}

function pluginIconMarkup(item){
  const label=String(item.title||item.name||"Plugin");
  const fallback=catalogEsc(label.trim().charAt(0).toUpperCase()||"P");
  if(!item.icon_url)return `<span class="plugin-icon-wrap"><span class="plugin-icon-fallback">${fallback}</span></span>`;
  return `<span class="plugin-icon-wrap"><img class="plugin-icon" src="${catalogEsc(item.icon_url)}" alt="" loading="lazy" referrerpolicy="no-referrer"><span class="plugin-icon-fallback" hidden>${fallback}</span></span>`;
}

function activateIconFallbacks(root){
  for(const image of root.querySelectorAll("img.plugin-icon")){
    image.addEventListener("error",()=>{image.hidden=true;const fallback=image.nextElementSibling;if(fallback)fallback.hidden=false},{once:true});
  }
}

async function loadPlugins(){
  const listNode=currentPluginList();
  listNode.innerHTML='<div class="muted">Loading…</div>';
  try{
    const ps=(await pApi("api/plugins")).plugins||[];
    if(typeof window.renderComposerPluginIndicators==="function")window.renderComposerPluginIndicators(ps);
    if(!ps.length){listNode.innerHTML='<div class="muted">No plugins installed.</div>';return}
    listNode.innerHTML="";
    for(const p of ps){
      const row=document.createElement("div");
      row.className="plugin-row";
      const tools=(p.tools||[]).map(t=>`<label class="plugin-tool"><input type="checkbox" data-p="${esc(p.id)}" data-t="${esc(t.name)}" data-permission="${esc(t.permission)}" ${t.enabled?"checked":""} ${p.builtin||t.permission==="blocked"?"disabled":""}><span><strong>${esc(t.name)}</strong><small>${esc(t.description||"No description")}</small></span><span class="plugin-badge ${esc(t.permission)}">${t.permission==="write"?"approval required":esc(t.permission)}</span></label>`).join("");
      const oauthActions=p.auth_mode==="oauth"
        ?`<button data-a="oauth" data-id="${esc(p.id)}">${p.oauth_connected?"Reauthorize":"Connect"}</button>${p.oauth_connected?`<button data-a="oauth-disconnect" data-id="${esc(p.id)}">Sign out</button>`:""}`
        :"";
      const pluginActions=p.builtin
        ?'<button type="button" disabled>Built-in · Developer Mode</button>'
        :`${oauthActions}<button data-a="toggle" data-id="${esc(p.id)}">${p.enabled?"Disable":"Enable"}</button><button data-a="refresh" data-id="${esc(p.id)}">Refresh</button><button data-a="remove" data-id="${esc(p.id)}">Remove</button>`;
      const pluginStateSummary=p.builtin
        ?`${p.available_to_chat?"Available in Developer Mode":"Enable Developer Mode to use"} · ${p.healthy?"Healthy":"Unavailable"}`
        :`${p.enabled?"Enabled":"Installed · disabled"} · ${p.available_to_chat?"Available to chat":"Not available to chat"} · ${p.enabled_tool_count||0} tool${(p.enabled_tool_count||0)===1?"":"s"} enabled · ${p.approval_tool_count||0} require approval · ${p.healthy?"Healthy":"Unhealthy"} · token ${p.has_secret?"stored":"not set"}`;
      row.innerHTML=`<div class="plugin-head"><div class="plugin-identity">${pluginIconMarkup(p)}<div><strong>${esc(p.name)}</strong><span class="plugin-meta">${esc(p.url)}</span><span class="plugin-meta">${pluginStateSummary}</span>${p.last_error?`<span class="plugin-meta">${esc(p.last_error)}</span>`:""}</div></div><div class="plugin-actions">${pluginActions}</div></div>${p.oauth_connected?`<div class="plugin-oauth-details"><span class="plugin-meta">OAuth account: ${esc(p.oauth_account||"not reported")}</span><span class="plugin-meta">Granted scopes: ${esc((p.oauth_scopes||[]).join(", ")||"not reported")}</span></div>`:""}${tools||'<div class="muted">No tools discovered.</div>'}`;
      listNode.appendChild(row);
      activateIconFallbacks(row);
    }
  }catch(e){listNode.textContent=`Could not load plugins: ${e.message||e}`}
}
installPlugin.addEventListener("click",async()=>{installPlugin.disabled=true;pluginState.textContent="Validating…";try{await pApi("api/plugins",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:pluginName.value.trim(),url:pluginUrl.value.trim(),bearer_token:pluginToken.value})});pluginName.value=pluginUrl.value=pluginToken.value="";pluginState.textContent="Installed disabled. Review tools, then enable.";await loadPlugins()}catch(e){pluginState.textContent=`Install failed: ${e.message||e}`}finally{installPlugin.disabled=false}});
currentPluginList().addEventListener("click",async e=>{const b=e.target.closest("button[data-a]");if(!b)return;try{if(b.dataset.a==="remove"&&!confirm("Remove this plugin and stored secret?"))return;await pApi(`api/plugins/${encodeURIComponent(b.dataset.id)}${b.dataset.a==="toggle"?"/toggle":b.dataset.a==="refresh"?"/refresh":""}`,{method:b.dataset.a==="remove"?"DELETE":"POST"});await loadPlugins()}catch(x){pluginState.textContent=`Plugin action failed: ${x.message||x}`}});
currentPluginList().addEventListener("change",async e=>{const c=e.target.closest("input[data-t]");if(!c)return;c.disabled=true;try{await pApi(`api/plugins/${encodeURIComponent(c.dataset.p)}/tools/${encodeURIComponent(c.dataset.t)}`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({enabled:c.checked,permission:c.dataset.permission||"blocked"})})}catch(x){c.checked=!c.checked;pluginState.textContent=`Tool update failed: ${x.message||x}`}finally{c.disabled=false}});
pluginsTab.addEventListener("click",async()=>{showPanel("plugins");await Promise.all([loadPlugins(),loadCatalog(false)])});

var catalogSearch=document.getElementById("catalog-search");
var catalogCategory=document.getElementById("catalog-category");
var catalogRefresh=document.getElementById("catalog-refresh");
var catalogStatus=document.getElementById("catalog-status")||(() => {
  const node=document.createElement("div");
  node.id="catalog-status";
  node.setAttribute("role","status");
  (document.getElementById("plugins-panel")||document.body).appendChild(node);
  return node;
})();
var catalogResults=document.getElementById("catalog-results")||(() => {
  const node=document.createElement("div");
  node.id="catalog-results";
  node.className="catalog-grid";
  (document.getElementById("plugins-panel")||document.body).appendChild(node);
  return node;
})();
let catalogTimer=null;

function catalogEsc(value){
  return String(value??"")
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#39;");
}

function catalogCard(item){
  const card=document.createElement("article");
  card.className=`catalog-card${item.installed?" installed":""}`;
  const verified=item.verified?'<span class="catalog-pill">Verified publisher</span>':'';
  const auth=item.auth_required?'<span class="catalog-pill">Authentication required</span>':'<span class="catalog-pill">No authentication</span>';
  const availability=item.availability?`<div class="catalog-availability">${catalogEsc(item.availability)}</div>`:"";
  let actions="";
  if(item.installed){
    actions=`<button type="button" disabled>${item.installed_enabled?"Installed · enabled":"Installed · disabled"}</button>`;
  }else if(item.auth_mode==="oauth"&&item.oauth_available){
    actions=`<button type="button" data-oauth-connect="${catalogEsc(item.id)}">${catalogEsc(item.setup_label||"Connect")}</button>`;
  }else if(item.id==="gmail-official"&&item.oauth_available===false){
    const guide=item.docs_url?`<a href="${catalogEsc(item.docs_url)}" target="_blank" rel="noopener noreferrer">Setup guide</a>`:"";
    actions=`<button type="button" data-copy-google-callback>Copy callback URL</button>${guide}`;
  }else if(item.installable===false){
    const guide=item.docs_url?`<a href="${catalogEsc(item.docs_url)}" target="_blank" rel="noopener noreferrer">Setup guide</a>`:"";
    actions=`<button type="button" disabled>${catalogEsc(item.setup_label||"Setup required")}</button>${guide}`;
  }else{
    actions=`<button type="button" data-catalog-install="${catalogEsc(item.id)}">Install</button>`;
  }
  card.innerHTML=`<div class="catalog-title">${pluginIconMarkup(item)}<div><h3>${catalogEsc(item.title||item.name)}</h3><div class="plugin-meta">${catalogEsc(item.publisher||"")}</div></div></div>
    <div class="catalog-details">${catalogEsc(item.description||"No description available.")}</div>
    <div class="catalog-meta">${verified}${auth}<span class="catalog-pill">${catalogEsc(item.category||"other")}</span></div>
    ${availability}<div class="catalog-details">${catalogEsc(item.url||item.package_ref||"")}</div>
    <div class="catalog-actions">${actions}</div>`;
  activateIconFallbacks(card);
  return card;
}

async function loadCatalog(force=false){
  ensurePluginDomReady();
  catalogSearch=document.getElementById("catalog-search");
  catalogCategory=document.getElementById("catalog-category");
  catalogRefresh=document.getElementById("catalog-refresh");
  catalogStatus=document.getElementById("catalog-status");
  catalogResults=document.getElementById("catalog-results");
  if(!catalogResults||!catalogStatus)return;
  catalogStatus.textContent="Loading catalog…";
  catalogRefresh.disabled=true;
  try{
    const params=new URLSearchParams();
    if(catalogSearch.value.trim())params.set("q",catalogSearch.value.trim());
    if(catalogCategory.value)params.set("category",catalogCategory.value);
    if(force)params.set("refresh","1");
    const data=await pApi(`api/plugin-catalog?${params.toString()}`);
    const items=data.plugins||[];
    catalogResults.replaceChildren();
    if(!items.length){
      catalogResults.innerHTML='<div class="catalog-empty">No matching remote MCP plugins found.</div>';
    }else{
      for(const item of items)catalogResults.appendChild(catalogCard(item));
    }
    const registryNote=data.registry_error?` · Registry warning: ${data.registry_error}`:"";
    catalogStatus.textContent=`${items.length} compatible remote plugin${items.length===1?"":"s"}${data.cached?" · cached":""}${registryNote} · ${data.source||"Official MCP Registry"}.`;
  }catch(error){
    catalogStatus.textContent=`Catalog unavailable: ${error.message||error}`;
  }finally{
    catalogRefresh.disabled=false;
  }
}

catalogSearch?.addEventListener("input",()=>{
  clearTimeout(catalogTimer);
  catalogTimer=setTimeout(()=>loadCatalog(false),250);
});
catalogCategory?.addEventListener("change",()=>loadCatalog(false));
catalogRefresh?.addEventListener("click",()=>loadCatalog(true));
catalogResults?.addEventListener("click",async event=>{
  const button=event.target.closest("button[data-catalog-install]");
  if(!button)return;
  const token=window.prompt("Bearer token or GitHub PAT, when required. Leave blank if not needed.")??"";
  button.disabled=true;
  catalogStatus.textContent="Validating and installing…";
  try{
    await pApi(`api/plugin-catalog/${encodeURIComponent(button.dataset.catalogInstall)}/install`,{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({bearer_token:token})
    });
    catalogStatus.textContent="Installed disabled. Review discovered tools before enabling.";
    await Promise.all([loadPlugins(),loadCatalog(false)]);
  }catch(error){
    catalogStatus.textContent=`Install failed: ${error.message||error}`;
  }finally{
    button.disabled=false;
  }
});
