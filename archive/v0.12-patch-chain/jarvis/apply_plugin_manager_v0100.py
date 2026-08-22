from pathlib import Path

ROOT = Path('/opt/jarvis')
INDEX = ROOT / 'app/static/index.html'
MAIN = ROOT / 'app/main.py'


def req(text, old, new, label):
    if old not in text:
        raise RuntimeError(f'Jarvis v0.10.0 patch missing: {label}')
    return text.replace(old, new, 1)


def before(text, marker, addition, label):
    return req(text, marker, addition + marker, label)


def patch_index():
    text = INDEX.read_text(encoding='utf-8')
    text = before(text, '</style>', '''
    .plugin-layout{display:grid;grid-template-columns:minmax(260px,.8fr) minmax(360px,1.4fr);gap:1rem}.plugin-card{border:1px solid var(--line);background:var(--panel);border-radius:8px;padding:1rem}.plugin-form{display:grid;gap:.7rem}.plugin-form label{display:grid;gap:.3rem}.plugin-form input{padding:.65rem;border:1px solid var(--line);background:var(--surface-strong);color:inherit}.plugin-row{border:1px solid var(--line);border-radius:7px;padding:.75rem;margin:.6rem 0}.plugin-head{display:flex;justify-content:space-between;gap:.7rem}.plugin-actions{display:flex;gap:.3rem;flex-wrap:wrap}.plugin-tool{display:grid;grid-template-columns:auto 1fr auto;gap:.5rem;align-items:center;border-top:1px solid var(--line);padding:.5rem}.plugin-tool small,.plugin-meta{display:block;color:var(--text-muted);overflow-wrap:anywhere}.plugin-badge{font-size:.68rem;text-transform:uppercase;border:1px solid var(--line);border-radius:999px;padding:.15rem .4rem}.plugin-badge.blocked{color:#b24a4a}.security-note{border-left:3px solid var(--cyan);padding:.65rem;background:var(--surface);color:var(--text-muted)}@media(max-width:900px){.plugin-layout{grid-template-columns:1fr}}
''', 'style')
    text = req(text, '<button id="settings-tab">SETTINGS</button>', '<button id="settings-tab">SETTINGS</button>\n    <button id="plugins-tab">PLUGINS</button>', 'tab')
    text = before(text, '</main>', '''
  <section id="plugins-panel" class="panel hidden"><div class="plugin-layout">
    <div class="plugin-card"><h2>INSTALL MCP PLUGIN</h2><p class="security-note">Only public HTTPS MCP endpoints are accepted. Plugins install disabled; tools are deny-by-default; secrets are masked.</p><div class="plugin-form">
      <label>Name<input id="plugin-name" maxlength="80"></label><label>MCP URL<input id="plugin-url" type="url" placeholder="https://mcp.example.com/mcp"></label><label>Bearer token (optional)<input id="plugin-token" type="password" autocomplete="new-password"></label><button id="install-plugin" type="button">Validate and Install</button><span id="plugin-state" role="status"></span>
    </div></div><div class="plugin-card"><h2>INSTALLED PLUGINS</h2><p>Only tools declared read-only by the MCP server can be enabled in v0.10.0.</p><div id="plugin-list" class="muted">No plugins loaded.</div></div>
  </div></section>
''', 'panel')
    text = before(text, '</script>', r'''
const pluginsTab=document.getElementById("plugins-tab"),pluginsPanel=document.getElementById("plugins-panel"),pluginList=document.getElementById("plugin-list"),pluginName=document.getElementById("plugin-name"),pluginUrl=document.getElementById("plugin-url"),pluginToken=document.getElementById("plugin-token"),installPlugin=document.getElementById("install-plugin"),pluginState=document.getElementById("plugin-state");
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"})[c]);
async function pApi(path,options={}){const r=await fetch(path,options),d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||`HTTP ${r.status}`);return d}
async function loadPlugins(){pluginList.innerHTML='<div class="muted">Loading…</div>';try{const ps=(await pApi("api/plugins")).plugins||[];if(!ps.length){pluginList.innerHTML='<div class="muted">No plugins installed.</div>';return}pluginList.innerHTML="";for(const p of ps){const row=document.createElement("div");row.className="plugin-row";const tools=(p.tools||[]).map(t=>`<label class="plugin-tool"><input type="checkbox" data-p="${esc(p.id)}" data-t="${esc(t.name)}" ${t.enabled?"checked":""} ${t.permission!=="read_only"?"disabled":""}><span><strong>${esc(t.name)}</strong><small>${esc(t.description||"No description")}</small></span><span class="plugin-badge ${esc(t.permission)}">${esc(t.permission)}</span></label>`).join("");row.innerHTML=`<div class="plugin-head"><div><strong>${esc(p.name)}</strong><span class="plugin-meta">${esc(p.url)}</span><span class="plugin-meta">${p.enabled?"Enabled":"Disabled"} · ${p.healthy?"Healthy":"Unhealthy"} · token ${p.has_secret?"stored":"not set"}</span></div><div class="plugin-actions"><button data-a="toggle" data-id="${esc(p.id)}">${p.enabled?"Disable":"Enable"}</button><button data-a="refresh" data-id="${esc(p.id)}">Refresh</button><button data-a="remove" data-id="${esc(p.id)}">Remove</button></div></div>${tools||'<div class="muted">No tools discovered.</div>'}`;pluginList.appendChild(row)}}catch(e){pluginList.textContent=`Could not load plugins: ${e.message||e}`}}
installPlugin.addEventListener("click",async()=>{installPlugin.disabled=true;pluginState.textContent="Validating…";try{await pApi("api/plugins",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:pluginName.value.trim(),url:pluginUrl.value.trim(),bearer_token:pluginToken.value})});pluginName.value=pluginUrl.value=pluginToken.value="";pluginState.textContent="Installed disabled. Review tools, then enable.";await loadPlugins()}catch(e){pluginState.textContent=`Install failed: ${e.message||e}`}finally{installPlugin.disabled=false}});
pluginList.addEventListener("click",async e=>{const b=e.target.closest("button[data-a]");if(!b)return;try{if(b.dataset.a==="remove"&&!confirm("Remove this plugin and stored secret?"))return;await pApi(`api/plugins/${encodeURIComponent(b.dataset.id)}${b.dataset.a==="toggle"?"/toggle":b.dataset.a==="refresh"?"/refresh":""}`,{method:b.dataset.a==="remove"?"DELETE":"POST"});await loadPlugins()}catch(x){pluginState.textContent=`Plugin action failed: ${x.message||x}`}});
pluginList.addEventListener("change",async e=>{const c=e.target.closest("input[data-t]");if(!c)return;c.disabled=true;try{await pApi(`api/plugins/${encodeURIComponent(c.dataset.p)}/tools/${encodeURIComponent(c.dataset.t)}`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({enabled:c.checked,permission:"read_only"})})}catch(x){c.checked=!c.checked;pluginState.textContent=`Tool update failed: ${x.message||x}`}finally{c.disabled=false}});
pluginsTab.addEventListener("click",async()=>{showPanel("plugins");await loadPlugins()});
''', 'script')
    text = req(text, '  const showSettings = panel === "settings";', '  const showSettings = panel === "settings";\n  const showPlugins = panel === "plugins";', 'panel state')
    text = req(text, '  settingsPanel.classList.toggle("hidden", !showSettings);', '  settingsPanel.classList.toggle("hidden", !showSettings);\n  pluginsPanel.classList.toggle("hidden", !showPlugins);', 'panel visibility')
    text = req(text, '  settingsTab.classList.toggle("active", showSettings);', '  settingsTab.classList.toggle("active", showSettings);\n  pluginsTab.classList.toggle("active", showPlugins);', 'tab state')
    text = text.replace('HUD 0.9.0','HUD 0.10.0').replace('HUD 0.9.1','HUD 0.10.0')
    INDEX.write_text(text, encoding='utf-8')


def patch_main():
    text = MAIN.read_text(encoding='utf-8')
    text = req(text, 'import json\n', 'import ipaddress\nimport json\nimport socket\n', 'imports')
    text = req(text, 'class SettingsRestoreRequest(BaseModel):', '''class PluginInstallRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    url: str = Field(min_length=8, max_length=500)
    bearer_token: str = Field(default="", max_length=4000)


class PluginToolUpdate(BaseModel):
    enabled: bool = False
    permission: str = Field(default="blocked", pattern="^(blocked|read_only|write)$")


class SettingsRestoreRequest(BaseModel):''', 'models')
    backend = r'''
PLUGIN_REGISTRY_PATH=Path("/data/plugins/registry.json")
PLUGIN_SECRETS_PATH=Path("/data/plugins/secrets.json")
PLUGIN_TIMEOUT=httpx.Timeout(15.0,connect=4.0)

def _plugin_load(path):
    if not path.exists(): return {}
    try: value=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError): return {}
    return value if isinstance(value,dict) else {}

def _plugin_save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(".tmp");tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8");tmp.chmod(0o600);tmp.replace(path);path.chmod(0o600)

def plugin_registry(): return _plugin_load(PLUGIN_REGISTRY_PATH)
def plugin_secrets(): return _plugin_load(PLUGIN_SECRETS_PATH)

def validate_plugin_url(raw):
    from urllib.parse import urlparse
    url=raw.strip();p=urlparse(url)
    if p.scheme!="https" or not p.hostname or p.username or p.password: raise ValueError("Only credential-free public HTTPS URLs are accepted")
    host=p.hostname.rstrip(".").lower()
    if host in {"localhost","localhost.localdomain"} or host.endswith(".local"): raise ValueError("Local MCP endpoints are blocked")
    try: addresses=socket.getaddrinfo(host,p.port or 443,type=socket.SOCK_STREAM)
    except socket.gaierror as exc: raise ValueError("MCP hostname could not be resolved") from exc
    if any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses): raise ValueError("MCP endpoint resolves to a private, loopback, reserved, or link-local address")
    return url

def plugin_public(pid,p):
    return {"id":pid,"name":p.get("name",pid),"url":p.get("url",""),"enabled":bool(p.get("enabled")),"healthy":bool(p.get("healthy")),"last_error":p.get("last_error"),"last_checked":p.get("last_checked"),"has_secret":bool(plugin_secrets().get(pid)),"tools":list(p.get("tools") or [])}

async def discover_plugin_tools(url,token=""):
    headers={"Accept":"application/json","Content-Type":"application/json"}
    if token: headers["Authorization"]=f"Bearer {token}"
    async with httpx.AsyncClient(timeout=PLUGIN_TIMEOUT,follow_redirects=False) as client:
        r=await client.post(url,headers=headers,json={"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"Jarvis Plugin Manager","version":"0.10.0"}}})
        if r.is_redirect: raise ValueError("MCP redirects are blocked")
        if r.is_error: raise ValueError(f"MCP initialize returned HTTP {r.status_code}")
        sid=r.headers.get("mcp-session-id")
        if sid: headers["mcp-session-id"]=sid
        await client.post(url,headers=headers,json={"jsonrpc":"2.0","method":"notifications/initialized"})
        r=await client.post(url,headers=headers,json={"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}})
        if r.is_redirect: raise ValueError("MCP redirects are blocked")
        if r.is_error: raise ValueError(f"MCP tools/list returned HTTP {r.status_code}")
        try: tools=r.json().get("result",{}).get("tools",[])
        except (ValueError,TypeError): raise ValueError("MCP server did not return JSON tool metadata")
    result=[]
    for tool in tools[:100]:
        name=str(tool.get("name") or "").strip()
        if name: result.append({"name":name[:128],"description":str(tool.get("description") or "")[:1000],"permission":"read_only" if (tool.get("annotations") or {}).get("readOnlyHint") is True else "blocked","enabled":False})
    return result

def active_mcp_tools():
    active=[];secrets=plugin_secrets()
    for pid,p in plugin_registry().items():
        allowed=[t.get("name") for t in p.get("tools",[]) if t.get("enabled") and t.get("permission")=="read_only"]
        if not p.get("enabled") or not allowed: continue
        item={"type":"mcp","server_label":f"plugin_{pid}"[:64],"server_url":p["url"],"server_description":str(p.get("name") or pid)[:200],"allowed_tools":allowed,"require_approval":"never"}
        if secrets.get(pid): item["authorization"]=secrets[pid]
        active.append(item)
    return active

@app.get("/api/plugins")
async def list_plugins():
    return {"plugins":[plugin_public(pid,p) for pid,p in plugin_registry().items()]}

@app.post("/api/plugins")
async def install_plugin(request:PluginInstallRequest):
    import hashlib
    registry=plugin_registry()
    if len(registry)>=20: raise HTTPException(status_code=400,detail="Plugin limit reached (20)")
    try: url=validate_plugin_url(request.url);tools=await discover_plugin_tools(url,request.bearer_token)
    except ValueError as exc: raise HTTPException(status_code=400,detail=str(exc)) from exc
    pid=hashlib.sha256(url.encode()).hexdigest()[:16];registry[pid]={"name":" ".join(request.name.strip().split()),"url":url,"enabled":False,"healthy":True,"last_error":None,"last_checked":time.time(),"tools":tools};_plugin_save(PLUGIN_REGISTRY_PATH,registry)
    secrets=plugin_secrets()
    if request.bearer_token: secrets[pid]=request.bearer_token
    else: secrets.pop(pid,None)
    _plugin_save(PLUGIN_SECRETS_PATH,secrets)
    return {"installed":True,"plugin":plugin_public(pid,registry[pid])}

@app.post("/api/plugins/{plugin_id}/toggle")
async def toggle_plugin(plugin_id:str):
    registry=plugin_registry();p=registry.get(plugin_id)
    if not p: raise HTTPException(status_code=404,detail="Plugin not found")
    if not p.get("healthy") and not p.get("enabled"): raise HTTPException(status_code=400,detail="Refresh and validate before enabling")
    p["enabled"]=not bool(p.get("enabled"));_plugin_save(PLUGIN_REGISTRY_PATH,registry);return {"saved":True,"plugin":plugin_public(plugin_id,p)}

@app.post("/api/plugins/{plugin_id}/refresh")
async def refresh_plugin(plugin_id:str):
    registry=plugin_registry();p=registry.get(plugin_id)
    if not p: raise HTTPException(status_code=404,detail="Plugin not found")
    old={t.get("name"):t for t in p.get("tools",[])}
    try:
        tools=await discover_plugin_tools(p["url"],str(plugin_secrets().get(plugin_id) or ""))
        for t in tools:
            previous=old.get(t["name"],{})
            if previous.get("permission")=="read_only": t["permission"]="read_only";t["enabled"]=bool(previous.get("enabled"))
        p.update({"tools":tools,"healthy":True,"last_error":None,"last_checked":time.time()})
    except ValueError as exc: p.update({"healthy":False,"enabled":False,"last_error":str(exc),"last_checked":time.time()})
    _plugin_save(PLUGIN_REGISTRY_PATH,registry);return {"plugin":plugin_public(plugin_id,p)}

@app.put("/api/plugins/{plugin_id}/tools/{tool_name}")
async def update_plugin_tool(plugin_id:str,tool_name:str,request:PluginToolUpdate):
    registry=plugin_registry();p=registry.get(plugin_id)
    if not p: raise HTTPException(status_code=404,detail="Plugin not found")
    tool=next((t for t in p.get("tools",[]) if t.get("name")==tool_name),None)
    if not tool: raise HTTPException(status_code=404,detail="Tool not found")
    if request.permission!="read_only" or tool.get("permission")!="read_only": raise HTTPException(status_code=400,detail="Only MCP-declared read-only tools can be enabled")
    tool["enabled"]=bool(request.enabled);_plugin_save(PLUGIN_REGISTRY_PATH,registry);return {"saved":True,"tool":tool}

@app.delete("/api/plugins/{plugin_id}")
async def remove_plugin(plugin_id:str):
    registry=plugin_registry()
    if plugin_id not in registry: raise HTTPException(status_code=404,detail="Plugin not found")
    registry.pop(plugin_id);_plugin_save(PLUGIN_REGISTRY_PATH,registry);secrets=plugin_secrets();secrets.pop(plugin_id,None);_plugin_save(PLUGIN_SECRETS_PATH,secrets);return {"removed":True}
'''
    text = before(text, '@app.get("/api/settings")', backend + '\n\n', 'routes')
    text = text.replace('"tools": WORKSHOP_TOOLS,','"tools": WORKSHOP_TOOLS + active_mcp_tools(),')
    for old in ('0.9.0','0.9.1'):
        text=text.replace(f'version="{old}"','version="0.10.0"').replace(f'"version": "{old}"','"version": "0.10.0"')
    MAIN.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    patch_index();patch_main()
