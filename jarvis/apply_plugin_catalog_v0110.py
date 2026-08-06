from pathlib import Path

ROOT = Path("/opt/jarvis")
INDEX = ROOT / "app/static/index.html"
MAIN = ROOT / "app/main.py"


def required(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"Jarvis v0.11.0 patch missing: {label}")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    required(text, "</style>", "style close")
    styles = r'''
    .catalog-toolbar{display:grid;grid-template-columns:minmax(220px,1fr) auto auto;gap:.55rem;align-items:center;margin:.7rem 0}
    .catalog-toolbar input,.catalog-toolbar select{padding:.65rem;border:1px solid var(--line);background:var(--surface-strong);color:inherit}
    .catalog-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:.7rem}
    .catalog-card{border:1px solid var(--line);border-radius:8px;padding:.85rem;background:var(--surface)}
    .catalog-card h3{margin:.1rem 0 .35rem;color:inherit}
    .catalog-meta{display:flex;gap:.35rem;flex-wrap:wrap;margin:.45rem 0}
    .catalog-pill{font-size:.68rem;border:1px solid var(--line);border-radius:999px;padding:.14rem .42rem}
    .catalog-actions{display:flex;gap:.4rem;align-items:center;margin-top:.7rem}
    .catalog-empty{padding:1rem;border:1px dashed var(--line);color:var(--text-muted)}
    .catalog-details{font-size:.8rem;color:var(--text-muted);overflow-wrap:anywhere}
    details.custom-plugin{margin-top:1rem}
    @media(max-width:760px){.catalog-toolbar{grid-template-columns:1fr}}
'''
    text = text.replace("</style>", styles + "\n</style>", 1)

    old_heading = '<div class="plugin-card"><h2>INSTALL MCP PLUGIN</h2>'
    required(text, old_heading, "custom plugin card")
    replacement = '''<div class="plugin-card" style="grid-column:1/-1"><h2>DISCOVER MCP PLUGINS</h2>
      <p class="security-note">Catalog results are remote HTTPS MCP servers only. Installations remain disabled until reviewed.</p>
      <div class="catalog-toolbar">
        <input id="catalog-search" type="search" placeholder="Search plugins, for example GitHub">
        <select id="catalog-category"><option value="">All categories</option><option value="developer-tools">Developer tools</option><option value="productivity">Productivity</option><option value="data">Data</option></select>
        <button id="catalog-refresh" type="button">Refresh Catalog</button>
      </div>
      <div id="catalog-status" role="status"></div>
      <div id="catalog-results" class="catalog-grid"></div>
    </div>
    <details class="custom-plugin" style="grid-column:1/-1"><summary>Advanced · Install custom MCP server</summary>
    <div class="plugin-card"><h2>INSTALL CUSTOM MCP PLUGIN</h2>'''
    text = text.replace(old_heading, replacement, 1)

    marker = '</div></div><div class="plugin-card"><h2>INSTALLED PLUGINS</h2>'
    required(text, marker, "custom plugin close")
    text = text.replace(
        marker,
        '</div></div></details><div class="plugin-card" style="grid-column:1/-1"><h2>INSTALLED PLUGINS</h2>',
        1,
    )

    required(text, "</script>", "script close")
    script = r'''
const catalogSearch=document.getElementById("catalog-search");
const catalogCategory=document.getElementById("catalog-category");
const catalogRefresh=document.getElementById("catalog-refresh");
const catalogStatus=document.getElementById("catalog-status");
const catalogResults=document.getElementById("catalog-results");
let catalogTimer=null;

function catalogCard(item){
  const card=document.createElement("article");
  card.className="catalog-card";
  const verified=item.verified?'<span class="catalog-pill">Verified publisher</span>':'';
  const auth=item.auth_required?'<span class="catalog-pill">Authentication required</span>':'<span class="catalog-pill">No authentication</span>';
  card.innerHTML=`<h3>${esc(item.title||item.name)}</h3>
    <div class="catalog-details">${esc(item.description||"No description available.")}</div>
    <div class="catalog-meta">${verified}${auth}<span class="catalog-pill">${esc(item.category||"other")}</span></div>
    <div class="catalog-details">${esc(item.url||"")}</div>
    <div class="catalog-actions"><button type="button" data-catalog-install="${esc(item.id)}">Install</button></div>`;
  return card;
}

async function loadCatalog(force=false){
  if(!catalogResults)return;
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
    catalogStatus.textContent=`${items.length} plugin${items.length===1?"":"s"} found${data.cached?" · cached":""}.`;
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
    await loadPlugins();
  }catch(error){
    catalogStatus.textContent=`Install failed: ${error.message||error}`;
  }finally{
    button.disabled=false;
  }
});
'''
    text = text.replace("</script>", script + "\n</script>", 1)

    text = text.replace(
        'pluginsTab.addEventListener("click",async()=>{showPanel("plugins");await loadPlugins()});',
        'pluginsTab.addEventListener("click",async()=>{showPanel("plugins");await Promise.all([loadPlugins(),loadCatalog(false)])});',
        1,
    )
    text = text.replace("HUD 0.10.2", "HUD 0.11.0")
    INDEX.write_text(text, encoding="utf-8")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    required(text, 'class PluginInstallRequest(BaseModel):', "plugin request model")
    text = text.replace(
        'class PluginInstallRequest(BaseModel):',
        '''class CatalogInstallRequest(BaseModel):
    bearer_token: str = Field(default="", max_length=4000)


class PluginInstallRequest(BaseModel):''',
        1,
    )

    required(text, '@app.get("/api/plugins")', "plugins API marker")
    backend = r'''
PLUGIN_CATALOG_CACHE_PATH = Path("/data/plugins/catalog-cache.json")
PLUGIN_CATALOG_TTL = 3600
MCP_REGISTRY_API = "https://registry.modelcontextprotocol.io/v0/servers"

FEATURED_REMOTE_PLUGINS = [
    {
        "id": "github-official",
        "name": "io.github.github/github-mcp-server",
        "title": "GitHub",
        "description": "Official GitHub MCP server for repositories, code, issues, pull requests, users, and workflows.",
        "url": "https://api.githubcopilot.com/mcp/",
        "category": "developer-tools",
        "verified": True,
        "auth_required": True,
        "publisher": "GitHub",
    }
]


def _catalog_cache_read():
    data = _plugin_load(PLUGIN_CATALOG_CACHE_PATH)
    if not data:
        return None
    saved_at = float(data.get("saved_at") or 0)
    if time.time() - saved_at > PLUGIN_CATALOG_TTL:
        return None
    plugins = data.get("plugins")
    return plugins if isinstance(plugins, list) else None


def _catalog_remote_entry(server):
    if not isinstance(server, dict):
        return None
    name = str(server.get("name") or "").strip()
    description = str(server.get("description") or "").strip()
    version = str(server.get("version") or "").strip()
    remotes = server.get("remotes") or server.get("remote") or []
    if isinstance(remotes, dict):
        remotes = [remotes]
    url = ""
    for remote in remotes:
        if not isinstance(remote, dict):
            continue
        candidate = str(remote.get("url") or remote.get("endpoint") or "").strip()
        if candidate.startswith("https://"):
            url = candidate
            break
    if not name or not url:
        return None
    try:
        validate_plugin_url(url)
    except ValueError:
        return None
    lower = f"{name} {description}".lower()
    category = "developer-tools" if any(word in lower for word in ("github", "gitlab", "code", "developer", "repository")) else "other"
    return {
        "id": hashlib.sha256(f"{name}|{version}|{url}".encode()).hexdigest()[:20],
        "name": name,
        "title": str(server.get("title") or name).strip()[:120],
        "description": description[:1000],
        "version": version[:80],
        "url": url,
        "category": category,
        "verified": bool(server.get("verified") or server.get("official")),
        "auth_required": bool(server.get("auth_required") or server.get("authentication")),
        "publisher": str(server.get("publisher") or "")[:120],
    }


async def _fetch_plugin_catalog(force=False):
    if not force:
        cached = _catalog_cache_read()
        if cached is not None:
            return cached, True
    plugins = list(FEATURED_REMOTE_PLUGINS)
    try:
        async with httpx.AsyncClient(timeout=PLUGIN_TIMEOUT, follow_redirects=False) as client:
            response = await client.get(MCP_REGISTRY_API, params={"limit": 100})
            if response.is_redirect:
                raise ValueError("Registry redirects are blocked")
            response.raise_for_status()
            payload = response.json()
        servers = payload.get("servers") or payload.get("items") or []
        for server in servers:
            entry = _catalog_remote_entry(server)
            if entry and not any(item["url"] == entry["url"] for item in plugins):
                plugins.append(entry)
    except Exception:
        cached = _catalog_cache_read()
        if cached is not None:
            return cached, True
    _plugin_save(PLUGIN_CATALOG_CACHE_PATH, {"saved_at": time.time(), "plugins": plugins})
    return plugins, False


@app.get("/api/plugin-catalog")
async def plugin_catalog(q: str = "", category: str = "", refresh: bool = False):
    plugins, cached = await _fetch_plugin_catalog(force=refresh)
    query = q.strip().lower()
    result = []
    for plugin in plugins:
        haystack = " ".join(str(plugin.get(key) or "") for key in ("name", "title", "description", "publisher")).lower()
        if query and query not in haystack:
            continue
        if category and plugin.get("category") != category:
            continue
        result.append(plugin)
    result.sort(key=lambda item: (not bool(item.get("verified")), str(item.get("title") or item.get("name")).lower()))
    return {"plugins": result[:100], "cached": cached}


@app.post("/api/plugin-catalog/{catalog_id}/install")
async def install_catalog_plugin(catalog_id: str, request: CatalogInstallRequest):
    plugins, _ = await _fetch_plugin_catalog(force=False)
    entry = next((plugin for plugin in plugins if plugin.get("id") == catalog_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Catalog plugin not found")
    install = PluginInstallRequest(
        name=str(entry.get("title") or entry.get("name") or "MCP Plugin"),
        url=str(entry.get("url") or ""),
        bearer_token=request.bearer_token,
    )
    return await install_plugin(install)


'''
    text = text.replace('@app.get("/api/plugins")', backend + '@app.get("/api/plugins")', 1)

    if "import hashlib\n" not in text:
        required(text, "import ipaddress\n", "imports")
        text = text.replace("import ipaddress\n", "import hashlib\nimport ipaddress\n", 1)

    text = text.replace('version="0.10.2"', 'version="0.11.0"')
    text = text.replace('"version": "0.10.2"', '"version": "0.11.0"')
    MAIN.write_text(text, encoding="utf-8")


def verify() -> None:
    index = INDEX.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")
    required_index = (
        'id="catalog-search"',
        'id="catalog-results"',
        'loadCatalog(false)',
        'Advanced · Install custom MCP server',
    )
    required_main = (
        '@app.get("/api/plugin-catalog")',
        '@app.post("/api/plugin-catalog/{catalog_id}/install")',
        'https://api.githubcopilot.com/mcp/',
        'MCP_REGISTRY_API',
    )
    missing = [item for item in required_index if item not in index]
    missing += [item for item in required_main if item not in main]
    if missing:
        raise RuntimeError("Jarvis v0.11.0 verification failed: " + ", ".join(missing))


if __name__ == "__main__":
    patch_index()
    patch_main()
    verify()
