from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.8 patch missing: {label}")


def replace_block(text: str, start_marker: str, end_marker: str, replacement: str, label: str) -> str:
    start = text.find(start_marker)
    end = text.find(end_marker, start)
    if start < 0 or end < 0:
        raise RuntimeError(f"ZBRANO v0.12.8 patch missing: {label}")
    return text[:start] + replacement + text[end:]


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")

    public_marker = "def plugin_public(pid,p):\n"
    require(text, public_marker, "plugin public response")
    icon_helpers = r'''PLUGIN_ICON_RULES = (
    (("gmail", "gmailmcp.googleapis.com"), "https://cdn.simpleicons.org/gmail/EA4335"),
    (("google drive", "drivemcp.googleapis.com"), "https://cdn.simpleicons.org/googledrive/4285F4"),
    (("google calendar", "calendarmcp.googleapis.com"), "https://cdn.simpleicons.org/googlecalendar/4285F4"),
    (("google chat", "chatmcp.googleapis.com"), "https://cdn.simpleicons.org/googlechat/00AC47"),
    (("google people", "people.googleapis.com/mcp"), "https://cdn.simpleicons.org/googlecontacts/4285F4"),
    (("google workspace", "workspacemcp.googleapis.com"), "https://cdn.simpleicons.org/googleworkspace/4285F4"),
    (("github", "githubcopilot.com/mcp"), "https://cdn.simpleicons.org/github/181717"),
    (("canva", "mcp.canva.com"), "https://cdn.simpleicons.org/canva/00C4CC"),
    (("cloudflare", "mcp.cloudflare.com"), "https://cdn.simpleicons.org/cloudflare/F38020"),
    (("adobe", "aa-mcp.adobe.io"), "https://cdn.simpleicons.org/adobe/FF0000"),
)


def plugin_icon_url(name: str = "", url: str = "") -> str:
    identity = f"{name} {url}".lower()
    for terms, icon_url in PLUGIN_ICON_RULES:
        if any(term in identity for term in terms):
            return icon_url
    return ""


'''
    text = text.replace(public_marker, icon_helpers + public_marker, 1)

    public_url = '        "url": p.get("url", ""),'
    require(text, public_url, "installed plugin URL")
    text = text.replace(
        public_url,
        '''        "url": p.get("url", ""),
        "icon_url": plugin_icon_url(str(p.get("name") or pid), str(p.get("url") or "")),''',
        1,
    )

    featured_start = "FEATURED_REMOTE_PLUGINS = [\n"
    featured_end = "\n\n\ndef _catalog_cache_read():"
    curated = r'''FEATURED_REMOTE_PLUGINS = [
    {
        "id": "github-official", "name": "io.github.github/github-mcp-server", "title": "GitHub",
        "description": "Official GitHub MCP server for repositories, code, issues, pull requests, users, and workflows.",
        "url": "https://api.githubcopilot.com/mcp/", "category": "developer-tools", "verified": True,
        "auth_required": True, "auth_mode": "github-oauth", "installable": True, "publisher": "GitHub",
        "icon_url": "https://cdn.simpleicons.org/github/181717", "docs_url": "https://docs.github.com/en/copilot/customizing-copilot/extending-copilot-chat-with-mcp",
    },
    {
        "id": "gmail-official", "name": "com.google.workspace/gmail", "title": "Gmail",
        "description": "Official Gmail remote MCP server for searching mail, reading threads, labels, and creating drafts.",
        "url": "https://gmailmcp.googleapis.com/mcp/v1", "category": "productivity", "verified": True,
        "auth_required": True, "auth_mode": "oauth", "installable": False, "publisher": "Google",
        "setup_label": "OAuth setup required", "availability": "Developer Preview",
        "icon_url": "https://cdn.simpleicons.org/gmail/EA4335", "docs_url": "https://developers.google.com/workspace/gmail/api/guides/configure-mcp-server",
    },
    {
        "id": "google-drive-official", "name": "com.google.workspace/drive", "title": "Google Drive",
        "description": "Official Google Drive remote MCP server for file search, metadata, reading, downloads, and file creation.",
        "url": "https://drivemcp.googleapis.com/mcp/v1", "category": "productivity", "verified": True,
        "auth_required": True, "auth_mode": "oauth", "installable": False, "publisher": "Google",
        "setup_label": "OAuth setup required", "availability": "Developer Preview",
        "icon_url": "https://cdn.simpleicons.org/googledrive/4285F4", "docs_url": "https://developers.google.com/workspace/drive/api/guides/configure-mcp-server",
    },
    {
        "id": "google-calendar-official", "name": "com.google.workspace/calendar", "title": "Google Calendar",
        "description": "Official Google Calendar remote MCP server for calendars, events, scheduling, and responses.",
        "url": "https://calendarmcp.googleapis.com/mcp/v1", "category": "productivity", "verified": True,
        "auth_required": True, "auth_mode": "oauth", "installable": False, "publisher": "Google",
        "setup_label": "OAuth setup required", "availability": "Developer Preview",
        "icon_url": "https://cdn.simpleicons.org/googlecalendar/4285F4", "docs_url": "https://developers.google.com/workspace/calendar/api/guides/configure-mcp-server",
    },
    {
        "id": "google-chat-official", "name": "com.google.workspace/chat", "title": "Google Chat",
        "description": "Official Google Chat remote MCP server for conversations, messages, search, and sending messages.",
        "url": "https://chatmcp.googleapis.com/mcp/v1", "category": "productivity", "verified": True,
        "auth_required": True, "auth_mode": "oauth", "installable": False, "publisher": "Google",
        "setup_label": "OAuth setup required", "availability": "Developer Preview",
        "icon_url": "https://cdn.simpleicons.org/googlechat/00AC47", "docs_url": "https://developers.google.com/workspace/guides/configure-mcp-servers",
    },
    {
        "id": "google-people-official", "name": "com.google.workspace/people", "title": "Google People",
        "description": "Official People API remote MCP server for user profiles, contacts, and directory search.",
        "url": "https://people.googleapis.com/mcp/v1", "category": "productivity", "verified": True,
        "auth_required": True, "auth_mode": "oauth", "installable": False, "publisher": "Google",
        "setup_label": "OAuth setup required", "availability": "Developer Preview",
        "icon_url": "https://cdn.simpleicons.org/googlecontacts/4285F4", "docs_url": "https://developers.google.com/people/v1/configure-mcp-server",
    },
    {
        "id": "google-workspace-search-official", "name": "com.google.workspace/search", "title": "Google Workspace Search",
        "description": "Official universal search MCP server across Gmail, Drive, Calendar, and Google Chat.",
        "url": "https://workspacemcp.googleapis.com/mcp/v1", "category": "productivity", "verified": True,
        "auth_required": True, "auth_mode": "oauth", "installable": False, "publisher": "Google",
        "setup_label": "OAuth setup required", "availability": "Developer Preview",
        "icon_url": "https://cdn.simpleicons.org/googleworkspace/4285F4", "docs_url": "https://developers.google.com/workspace/guides/universal-search-mcp",
    },
    {
        "id": "canva-official", "name": "com.canva/mcp", "title": "Canva",
        "description": "Official Canva remote MCP server for designs, assets, brand resources, exports, and collaboration.",
        "url": "https://mcp.canva.com/mcp", "category": "creative", "verified": True,
        "auth_required": True, "auth_mode": "oauth", "installable": False, "publisher": "Canva",
        "setup_label": "OAuth setup required", "availability": "Access may require approval",
        "icon_url": "https://cdn.simpleicons.org/canva/00C4CC", "docs_url": "https://www.canva.dev/docs/mcp/",
    },
    {
        "id": "cloudflare-official", "name": "com.cloudflare/api-mcp", "title": "Cloudflare",
        "description": "Official Cloudflare API MCP server for Workers, DNS, R2, Zero Trust, security, and account configuration.",
        "url": "https://mcp.cloudflare.com/mcp", "category": "infrastructure", "verified": True,
        "auth_required": True, "auth_mode": "oauth", "installable": False, "publisher": "Cloudflare",
        "setup_label": "OAuth setup required",
        "icon_url": "https://cdn.simpleicons.org/cloudflare/F38020", "docs_url": "https://developers.cloudflare.com/agents/model-context-protocol/cloudflare/servers-for-cloudflare/",
    },
    {
        "id": "adobe-analytics-official", "name": "com.adobe/analytics-mcp", "title": "Adobe Analytics",
        "description": "Official Adobe Analytics remote MCP server for report suites, metrics, dimensions, segments, and reports.",
        "url": "https://aa-mcp.adobe.io/mcp", "category": "data", "verified": True,
        "auth_required": True, "auth_mode": "oauth", "installable": False, "publisher": "Adobe",
        "setup_label": "OAuth setup required",
        "icon_url": "https://cdn.simpleicons.org/adobe/FF0000", "docs_url": "https://developer.adobe.com/analytics-mcp/docs/aa/",
    },
]'''
    text = replace_block(text, featured_start, featured_end, curated, "featured plugin catalog")

    catalog_entry_return = '''        "publisher": str(server.get("publisher") or "")[:120],
    }'''
    require(text, catalog_entry_return, "registry catalog entry")
    text = text.replace(
        catalog_entry_return,
        '''        "publisher": str(server.get("publisher") or "")[:120],
        "icon_url": plugin_icon_url(title, url),
        "docs_url": str((server.get("repository") or {}).get("url") or "")[:500] if isinstance(server.get("repository"), dict) else "",
    }''',
        1,
    )

    active_catalog_return = '''        "auth_required": auth_required,
        "publisher": str(server.get("publisher") or "")[:120],
    }


def _catalog_with_featured(items):'''
    require(text, active_catalog_return, "active registry catalog entry")
    text = text.replace(
        active_catalog_return,
        '''        "auth_required": auth_required,
        "publisher": str(server.get("publisher") or "")[:120],
        "icon_url": plugin_icon_url(title, url),
        "docs_url": str((server.get("repository") or {}).get("url") or "")[:500] if isinstance(server.get("repository"), dict) else "",
    }


def _catalog_with_featured(items):''',
        1,
    )

    require(text, "            while pages < 3:", "registry page limit")
    text = text.replace("            while pages < 3:", "            while pages < 10:", 1)
    require(text, 'return {"plugins": result[:100], "cached": cached, "registry_error": registry_error}', "catalog result cap")
    text = text.replace(
        'return {"plugins": result[:100], "cached": cached, "registry_error": registry_error}',
        'return {"plugins": result[:500], "cached": cached, "registry_error": registry_error, "source": "Official MCP Registry plus curated official remote connectors"}',
        1,
    )

    old_auth = '''        if item.get("id") == "github-official":
            item["auth_mode"] = "github-oauth"
            item["oauth_available"] = oauth_available
        else:
            item["auth_mode"] = "bearer" if item.get("auth_required") else "none"
            item["oauth_available"] = False'''
    new_auth = '''        if item.get("id") == "github-official":
            item["auth_mode"] = "github-oauth"
            item["oauth_available"] = oauth_available
        elif item.get("auth_mode") == "oauth":
            item["oauth_available"] = False
        else:
            item["auth_mode"] = "bearer" if item.get("auth_required") else "none"
            item["oauth_available"] = False'''
    require(text, old_auth, "catalog authentication classification")
    text = text.replace(old_auth, new_auth, 1)

    install_entry = '''    if not entry:
        raise HTTPException(status_code=404, detail="Catalog plugin not found")
    install = PluginInstallRequest('''
    require(text, install_entry, "catalog install guard")
    text = text.replace(
        install_entry,
        '''    if not entry:
        raise HTTPException(status_code=404, detail="Catalog plugin not found")
    if entry.get("installable") is False:
        raise HTTPException(status_code=409, detail=entry.get("setup_label") or "This connector requires an OAuth setup workflow")
    install = PluginInstallRequest(''',
        1,
    )

    text = text.replace('version="0.12.7"', 'version="0.12.8"')
    text = text.replace('"version": "0.12.7"', '"version": "0.12.8"')
    MAIN.write_text(text, encoding="utf-8")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    panel_start = '  <section id="plugins-panel" class="panel hidden">'
    panel_end = "\n</main>"
    plugin_panel = r'''  <section id="plugins-panel" class="panel hidden">
    <div class="plugin-workspace">
      <div class="plugin-subtabs" role="tablist" aria-label="Plugin views">
        <button id="plugins-installed-tab" class="active" type="button" role="tab" aria-selected="true" aria-controls="plugins-installed-view">Installed Plugins</button>
        <button id="plugins-browse-tab" type="button" role="tab" aria-selected="false" aria-controls="plugins-browse-view">Browse Plugins</button>
      </div>
      <section id="plugins-installed-view" class="plugin-subview" role="tabpanel" aria-labelledby="plugins-installed-tab">
        <div class="plugin-card"><h2>INSTALLED PLUGINS</h2><p>Read-only tools run automatically. Tools that can change data remain approval-gated.</p><div id="plugin-list" class="muted">No plugins loaded.</div></div>
      </section>
      <section id="plugins-browse-view" class="plugin-subview hidden" role="tabpanel" aria-labelledby="plugins-browse-tab">
        <div class="plugin-card"><h2>BROWSE PLUGINS</h2>
          <p class="security-note">Official curated connectors and compatible remote HTTPS MCP servers from the Official MCP Registry. OAuth-only connectors are listed with setup guidance and cannot be installed until ZBRANO supports their authorization flow.</p>
          <div class="catalog-toolbar">
            <input id="catalog-search" type="search" placeholder="Search Gmail, Drive, Canva, Cloudflare, Adobe…">
            <select id="catalog-category"><option value="">All categories</option><option value="developer-tools">Developer tools</option><option value="productivity">Productivity</option><option value="creative">Creative</option><option value="infrastructure">Infrastructure</option><option value="data">Data</option><option value="other">Other</option></select>
            <button id="catalog-refresh" type="button">Refresh Catalog</button>
          </div>
          <div id="catalog-status" role="status"></div>
          <div id="catalog-results" class="catalog-grid"></div>
        </div>
        <details class="custom-plugin"><summary>Advanced · Install custom MCP server</summary>
          <div class="plugin-card"><h2>INSTALL CUSTOM MCP PLUGIN</h2><p class="security-note">Only public HTTPS MCP endpoints are accepted. Plugins install disabled; tools are deny-by-default; secrets are masked.</p><form id="plugin-install-form" class="plugin-form">
            <label>Name<input id="plugin-name" maxlength="80"></label><label>MCP URL<input id="plugin-url" type="url" placeholder="https://mcp.example.com/mcp"></label><label>Bearer token (optional)<input id="plugin-token" type="password" autocomplete="new-password"></label><button id="install-plugin" type="button">Validate and Install</button><span id="plugin-state" role="status"></span>
          </form></div>
        </details>
      </section>
    </div>
  </section>'''
    text = replace_block(text, panel_start, panel_end, plugin_panel, "Plugins workspace")

    style_close = text.find("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.8 patch missing: style close")
    css = r'''
    .plugin-workspace{display:grid;gap:.8rem;min-height:0}
    .plugin-subtabs{display:flex;gap:.4rem;border-bottom:1px solid var(--line);padding-bottom:.55rem}
    .plugin-subtabs button.active{border-color:var(--cyan);color:var(--cyan);box-shadow:0 0 12px rgba(92,236,255,.1)}
    .plugin-subview{min-height:0}.plugin-subview.hidden{display:none}
    .plugin-identity,.catalog-title{display:flex;align-items:center;gap:.65rem;min-width:0}
    .plugin-icon-wrap{width:2.25rem;height:2.25rem;display:grid;place-items:center;flex:0 0 auto;border:1px solid var(--line);border-radius:8px;background:rgba(255,255,255,.92);overflow:hidden}
    .plugin-icon{width:1.55rem;height:1.55rem;object-fit:contain}.plugin-icon-fallback{font-weight:800;color:#263238}
    .catalog-card.installed{border-color:color-mix(in srgb,var(--phosphor) 55%,var(--line))}
    .catalog-card h3{margin:0}.catalog-actions a{display:inline-flex;align-items:center;padding:.5rem .65rem;border:1px solid var(--line);border-radius:4px;color:var(--cyan);text-decoration:none}
    .catalog-actions button[disabled]{opacity:.68;cursor:not-allowed}.catalog-availability{color:var(--text-muted);font-size:.72rem}
    details.custom-plugin{margin-top:.8rem}
'''
    text = text[:style_close] + css + text[style_close:]

    load_start = "async function loadPlugins(){\n"
    load_end = "installPlugin.addEventListener"
    new_loader = r'''function pluginIconMarkup(item){
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
    if(!ps.length){listNode.innerHTML='<div class="muted">No plugins installed.</div>';return}
    listNode.innerHTML="";
    for(const p of ps){
      const row=document.createElement("div");
      row.className="plugin-row";
      const tools=(p.tools||[]).map(t=>`<label class="plugin-tool"><input type="checkbox" data-p="${esc(p.id)}" data-t="${esc(t.name)}" data-permission="${esc(t.permission)}" ${t.enabled?"checked":""} ${t.permission==="blocked"?"disabled":""}><span><strong>${esc(t.name)}</strong><small>${esc(t.description||"No description")}</small></span><span class="plugin-badge ${esc(t.permission)}">${t.permission==="write"?"approval required":esc(t.permission)}</span></label>`).join("");
      row.innerHTML=`<div class="plugin-head"><div class="plugin-identity">${pluginIconMarkup(p)}<div><strong>${esc(p.name)}</strong><span class="plugin-meta">${esc(p.url)}</span><span class="plugin-meta">${p.enabled?"Enabled":"Installed · disabled"} · ${p.available_to_chat?"Available to chat":"Not available to chat"} · ${p.enabled_tool_count||0} tool${(p.enabled_tool_count||0)===1?"":"s"} enabled · ${p.approval_tool_count||0} require approval · ${p.healthy?"Healthy":"Unhealthy"} · token ${p.has_secret?"stored":"not set"}</span></div></div><div class="plugin-actions"><button data-a="toggle" data-id="${esc(p.id)}">${p.enabled?"Disable":"Enable"}</button><button data-a="refresh" data-id="${esc(p.id)}">Refresh</button><button data-a="remove" data-id="${esc(p.id)}">Remove</button></div></div>${tools||'<div class="muted">No tools discovered.</div>'}`;
      listNode.appendChild(row);
      activateIconFallbacks(row);
    }
  }catch(e){listNode.textContent=`Could not load plugins: ${e.message||e}`}
}
'''
    text = replace_block(text, load_start, load_end, new_loader, "installed plugin renderer")

    card_start = "function catalogCard(item){\n"
    card_end = "\n\nasync function loadCatalog"
    new_card = r'''function catalogCard(item){
  const card=document.createElement("article");
  card.className=`catalog-card${item.installed?" installed":""}`;
  const verified=item.verified?'<span class="catalog-pill">Verified publisher</span>':'';
  const auth=item.auth_required?'<span class="catalog-pill">Authentication required</span>':'<span class="catalog-pill">No authentication</span>';
  const availability=item.availability?`<div class="catalog-availability">${catalogEsc(item.availability)}</div>`:"";
  let actions="";
  if(item.installed){
    actions=`<button type="button" disabled>${item.installed_enabled?"Installed · enabled":"Installed · disabled"}</button>`;
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
}'''
    text = replace_block(text, card_start, card_end, new_card, "catalog card renderer")

    old_status = 'catalogStatus.textContent=`${items.length} plugin${items.length===1?"":"s"} found${data.cached?" · cached":""}${registryNote}.`;'
    new_status = 'catalogStatus.textContent=`${items.length} compatible remote plugin${items.length===1?"":"s"}${data.cached?" · cached":""}${registryNote} · ${data.source||"Official MCP Registry"}.`;'
    require(text, old_status, "catalog result summary")
    text = text.replace(old_status, new_status, 1)

    old_reload = "    await loadPlugins();\n  }catch(error){"
    require(text, old_reload, "post-install reload")
    text = text.replace(old_reload, "    await Promise.all([loadPlugins(),loadCatalog(false)]);\n  }catch(error){", 1)

    runtime = r'''
<script id="zbrano-v0128-plugin-workspace">
(() => {
  const installedTab=document.getElementById("plugins-installed-tab");
  const browseTab=document.getElementById("plugins-browse-tab");
  const installedView=document.getElementById("plugins-installed-view");
  const browseView=document.getElementById("plugins-browse-view");
  if(!installedTab||!browseTab||!installedView||!browseView)return;

  function showPluginView(view){
    const browse=view==="browse";
    installedView.classList.toggle("hidden",browse);
    browseView.classList.toggle("hidden",!browse);
    installedTab.classList.toggle("active",!browse);
    browseTab.classList.toggle("active",browse);
    installedTab.setAttribute("aria-selected",String(!browse));
    browseTab.setAttribute("aria-selected",String(browse));
    if(browse&&typeof loadCatalog==="function")loadCatalog(false);
    if(!browse&&typeof loadPlugins==="function")loadPlugins();
  }

  installedTab.addEventListener("click",()=>showPluginView("installed"));
  browseTab.addEventListener("click",()=>showPluginView("browse"));
  showPluginView("installed");
})();
</script>
'''
    body_close = text.rfind("</body>")
    if body_close < 0:
        raise RuntimeError("ZBRANO v0.12.8 patch missing: body close")
    text = text[:body_close] + runtime + text[body_close:]

    text = text.replace("HUD 0.12.7", "HUD 0.12.8")
    INDEX.write_text(text, encoding="utf-8")


def verify() -> None:
    main = MAIN.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    required_main = (
        'version="0.12.8"', "def plugin_icon_url(", '"id": "gmail-official"',
        '"id": "google-drive-official"', '"id": "canva-official"',
        '"id": "cloudflare-official"', '"id": "adobe-analytics-official"',
        "while pages < 10", 'result[:500]', 'entry.get("installable") is False',
    )
    required_index = (
        'id="plugins-installed-tab"', 'id="plugins-browse-tab"',
        'id="plugins-installed-view"', 'id="plugins-browse-view"',
        "function pluginIconMarkup(", "item.installed", "item.setup_label",
        'id="zbrano-v0128-plugin-workspace"', "HUD 0.12.8",
    )
    missing = [marker for marker in required_main if marker not in main]
    missing += [marker for marker in required_index if marker not in index]
    if index.find('id="plugins-installed-view"') > index.find('id="plugins-browse-view"'):
        missing.append("Installed Plugins is not first")
    if missing:
        raise RuntimeError("ZBRANO v0.12.8 verification failed: " + ", ".join(missing))


if __name__ == "__main__":
    patch_main()
    patch_index()
    verify()
