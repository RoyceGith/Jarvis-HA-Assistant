from pathlib import Path

ROOT=Path('/opt/jarvis')
MAIN=ROOT/'app/main.py'
INDEX=ROOT/'app/static/index.html'

def must(text, marker, label):
    if marker not in text:
        raise RuntimeError(f'Jarvis v0.11.20 patch missing: {label}')

def patch_main():
    text=MAIN.read_text(encoding='utf-8')
    text=text.replace('version="0.11.19"','version="0.11.20"',1)
    text=text.replace('"version": "0.11.19"','"version": "0.11.20"',1)

    old='headers={"Accept":"application/json","Content-Type":"application/json"}'
    must(text, old, 'MCP request headers')
    text=text.replace(old,'headers={"Accept":"application/json, text/event-stream","Content-Type":"application/json"}',1)

    marker='async def discover_plugin_tools(url,token=""):'
    must(text, marker, 'discover_plugin_tools')
    helper='''def _mcp_response_json(response):\n    content_type=str(response.headers.get("content-type") or "").lower()\n    if "text/event-stream" not in content_type:\n        return response.json()\n    for line in response.text.splitlines():\n        if not line.startswith("data:"):\n            continue\n        payload=line[5:].strip()\n        if not payload or payload=="[DONE]":\n            continue\n        return json.loads(payload)\n    raise ValueError("MCP server returned no JSON event data")\n\n\nGITHUB_MCP_URL="https://api.githubcopilot.com/mcp/"\n\n\ndef _plugin_url_key(url):\n    return str(url or "").strip().rstrip("/").lower()\n\n\n'''
    text=text.replace(marker, helper+marker,1)

    old='tools=r.json().get("result",{}).get("tools",[])'
    must(text, old, 'MCP tools JSON parser')
    text=text.replace(old,'tools=_mcp_response_json(r).get("result",{}).get("tools",[])',1)

    old='''installed_by_url={str(p.get("url") or ""):p for p in plugin_registry().values()}\n    for item in result:\n        installed=installed_by_url.get(str(item.get("url") or "")); item["installed"]=bool(installed); item["installed_enabled"]=bool(installed and installed.get("enabled"))'''
    if old in text:
        new='''installed_by_url={_plugin_url_key(p.get("url")):p for p in plugin_registry().values()}\n    installed_plugins=list(plugin_registry().values())\n    for item in result:\n        installed=installed_by_url.get(_plugin_url_key(item.get("url")))\n        if not installed and "github" in f"{item.get('name','')} {item.get('title','')} {item.get('url','')}".lower():\n            installed=next((p for p in installed_plugins if "github" in f"{p.get('name','')} {p.get('url','')}".lower()),None)\n        item["installed"]=bool(installed); item["installed_enabled"]=bool(installed and installed.get("enabled"))'''
        text=text.replace(old,new,1)

    old='''        PluginInstallRequest(\n            name=str(entry.get("title") or entry.get("name") or "GitHub"),\n            url=str(entry.get("url") or ""),\n            bearer_token=access_token,\n        )'''
    if old in text:
        new='''        PluginInstallRequest(\n            name=str(entry.get("title") or entry.get("name") or "GitHub"),\n            url=GITHUB_MCP_URL,\n            bearer_token=access_token,\n        )'''
        text=text.replace(old,new,1)

    MAIN.write_text(text,encoding='utf-8')

def patch_index():
    text=INDEX.read_text(encoding='utf-8')
    text=text.replace('HUD 0.11.19','HUD 0.11.20',1)

    current_new_chat="""async function createNewChat() {
  if (activeRequest) return;
  jarvisChatSessionId = createSessionId();
  updateSessionDisplay();
  showPanel("chat");
  showChatWelcome();
  input.value = "";
  input.dispatchEvent(new Event("input", {bubbles: true}));
  input.focus();
  await refreshChatList();
}"""
    replacement_new_chat="""async function createNewChat() {
  if (activeRequest) return;
  const sessionId = createSessionId();
  const response = await fetch("api/chats", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({session_id: sessionId}),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  showPanel("chat");
  await openChat(sessionId);
}"""
    must(text,current_new_chat,'current New Chat lifecycle')
    text=text.replace(current_new_chat,replacement_new_chat,1)

    text=text.replace(
        '<select id="attachment-scope"><option value="chat">This chat</option><option value="shared">Shared files</option></select>',
        '<select id="attachment-scope" title="Choose where this upload is stored"><option value="chat">Attach to this chat</option><option value="shared">Add to Shared Files</option></select>',1)

    old='async function list(){let d=await pApi(`api/files/shared?sort=${sort.value}&order=${order.value}`);'
    if old in text:
        text=text.replace(old,'async function list(){let d=await pApi(`api/files/shared?sort=${sort.value}&order=${order.value}&_=${Date.now()}`);',1)

    if 'state.textContent="Ready"' in text:
        text=text.replace('state.textContent="Ready"','state.textContent=scope.value==="shared"?"Uploaded to Shared Files":"Uploaded to this chat"',1)

    needle='order?.addEventListener("change",list);'
    if needle in text and 'Destination: Shared Files' not in text:
        text=text.replace(needle,needle+'scope?.addEventListener("change",()=>{state.textContent=scope.value==="shared"?"Destination: Shared Files":"Destination: This chat"});',1)

    old='''          if (typeof loadPlugins === "function") await loadPlugins();\n          return;'''
    if old in text:
        text=text.replace(old,'''          if (typeof loadPlugins === "function") await loadPlugins();\n          if (typeof loadCatalog === "function") await loadCatalog(true);\n          return;''',1)

    INDEX.write_text(text,encoding='utf-8')

def verify():
    m=MAIN.read_text(encoding='utf-8'); i=INDEX.read_text(encoding='utf-8')
    for marker in ('version="0.11.20"','application/json, text/event-stream','GITHUB_MCP_URL="https://api.githubcopilot.com/mcp/"','_plugin_url_key'):
        must(m,marker,marker)
    for marker in ('HUD 0.11.20','Add to Shared Files','Uploaded to Shared Files','Destination: Shared Files'):
        must(i,marker,marker)
    must(i,'body: JSON.stringify({session_id: sessionId})','persistent New Chat creation')

if __name__=='__main__':
    patch_main(); patch_index(); verify()
