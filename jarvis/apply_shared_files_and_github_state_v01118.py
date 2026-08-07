from pathlib import Path
R=Path('/opt/jarvis'); M=R/'app/main.py'; I=R/'app/static/index.html'
def need(t,s):
    if s not in t: raise RuntimeError('v0.11.18 marker missing: '+s[:60])
def rep(t,a,b): need(t,a); return t.replace(a,b,1)
def main():
    t=M.read_text(); t=rep(t,'import re\nimport time\n','import re\nimport shutil\nimport time\n'); t=t.replace('version="0.11.17"','version="0.11.18"',1).replace('"version": "0.11.17"','"version": "0.11.18"',1)
    t=rep(t,'    message: str = Field(min_length=1, max_length=4000)\n','    message: str = Field(min_length=1, max_length=4000)\n    attachment_ids: list[str] = Field(default_factory=list, max_length=20)\n')
    t=rep(t,'SETTINGS_STORAGE_PATH = Path("/data/jarvis_settings.json")\n','SETTINGS_STORAGE_PATH = Path("/data/jarvis_settings.json")\nCHAT_UPLOAD_ROOT=Path("/data/uploads")\nSHARED_FILE_ROOT=Path("/data/shared_files")\nFILE_UPLOAD_MAX_BYTES=25*1024*1024\nFILE_TEXT_MAX_CHARS=200000\nFILE_ID_RE=re.compile(r"^[a-f0-9]{24}$")\n')
    old='''def clear_chat_history(session_id: str) -> None:\n    CHAT_SESSIONS.pop(session_id, None)\n    LAST_ENTITY_BY_SESSION.pop(session_id, None)\n    CHAT_SESSION_META.pop(session_id, None)\n    try:\n        CHAT_SESSION_ORDER.remove(session_id)\n    except ValueError:\n        pass\n    persist_chat_sessions()\n'''; new=old.replace('    persist_chat_sessions()\n','    shutil.rmtree(CHAT_UPLOAD_ROOT / re.sub(r"[^A-Za-z0-9_.-]", "_", session_id)[:128], ignore_errors=True)\n    persist_chat_sessions()\n'); t=rep(t,old,new)
    t=rep(t,'    CHAT_SESSION_META.clear()\n    persist_chat_sessions()\n    return {"deleted": count}\n','    CHAT_SESSION_META.clear()\n    shutil.rmtree(CHAT_UPLOAD_ROOT, ignore_errors=True)\n    persist_chat_sessions()\n    return {"deleted": count}\n')
    api=r'''
TEXT_FILE_EXTENSIONS={".txt",".md",".json",".csv",".tsv",".yaml",".yml",".xml",".log",".py",".js",".ts",".css",".html",".ini",".cfg"}
class SharedFilesDeleteRequest(BaseModel): file_ids:list[str]=Field(default_factory=list,max_length=100)
def _sid(s): return re.sub(r"[^A-Za-z0-9_.-]","_",s)[:128] or "default"
def _fid(): return hashlib.sha256(f"{time.time_ns()}:{os.urandom(16).hex()}".encode()).hexdigest()[:24]
def _meta(p):
    try:
        x=json.loads((p/"metadata.json").read_text()); return x if isinstance(x,dict) else None
    except (OSError,json.JSONDecodeError): return None
async def _store(u,root,scope,session_id=""):
    root.mkdir(parents=True,exist_ok=True); name=Path(u.filename or "upload.bin").name[:240] or "upload.bin"; ext=Path(name).suffix.lower()[:20]; fid=_fid(); d=root/fid; d.mkdir(); dst=d/("original"+ext); size=0; h=hashlib.sha256()
    try:
        with dst.open("wb") as f:
            while True:
                c=await u.read(1024*1024)
                if not c: break
                size+=len(c)
                if size>FILE_UPLOAD_MAX_BYTES: raise HTTPException(413,"File exceeds 25 MB upload limit")
                h.update(c); f.write(c)
    except Exception: shutil.rmtree(d,ignore_errors=True); raise
    finally: await u.close()
    if not size: shutil.rmtree(d,ignore_errors=True); raise HTTPException(400,"Uploaded file is empty")
    mime=(u.content_type or "application/octet-stream").lower()[:160]; text=False
    if mime.startswith("text/") or ext in TEXT_FILE_EXTENSIONS:
        try: (d/"extracted.txt").write_text(dst.read_text(errors="replace")[:FILE_TEXT_MAX_CHARS]); text=True
        except OSError: pass
    m={"file_id":fid,"name":name,"scope":scope,"session_id":session_id if scope=="chat" else None,"mime_type":mime,"size":size,"sha256":h.hexdigest(),"created_at":time.time(),"stored_name":dst.name,"text_available":text}; (d/"metadata.json").write_text(json.dumps(m,indent=2)); return m
def _list(root):
    return [m for p in root.iterdir() if p.is_dir() and (m:=_meta(p))] if root.exists() else []
def attachment_context(session_id,ids):
    out=[]
    for fid in ids[:20]:
        if not FILE_ID_RE.fullmatch(fid): continue
        d=next((p for p in (SHARED_FILE_ROOT/fid,CHAT_UPLOAD_ROOT/_sid(session_id)/fid) if p.is_dir()),None)
        if not d or not (m:=_meta(d)): continue
        head=f"File: {m.get('name')} (id={fid}, scope={m.get('scope')}, type={m.get('mime_type')}, bytes={m.get('size')})"; x=d/"extracted.txt"
        out.append(head+"\n"+(x.read_text(errors="replace")[:FILE_TEXT_MAX_CHARS] if x.exists() else "[Stored safely; text extraction is not available for this file type yet.]"))
    return "\n\n--- Attached file context ---\n"+"\n\n".join(out) if out else ""
@app.post("/api/files/chat/{session_id}")
async def upload_chat_file(session_id:str,file:UploadFile=File(...)): return await _store(file,CHAT_UPLOAD_ROOT/_sid(session_id),"chat",session_id)
@app.get("/api/files/chat/{session_id}")
async def list_chat_files(session_id:str): return {"files":_list(CHAT_UPLOAD_ROOT/_sid(session_id))}
@app.post("/api/files/shared")
async def upload_shared_file(file:UploadFile=File(...)): return await _store(file,SHARED_FILE_ROOT,"shared")
@app.get("/api/files/shared")
async def list_shared_files(sort:str="date",order:str="desc"):
    x=_list(SHARED_FILE_ROOT); rev=order.lower()!="asc"; x.sort(key=(lambda a:str(a.get("name") or "").lower()) if sort.lower()=="name" else (lambda a:float(a.get("created_at") or 0)),reverse=rev); return {"files":x}
@app.delete("/api/files/shared")
async def delete_shared_files(r:SharedFilesDeleteRequest):
    done=[]
    for fid in r.file_ids:
        if FILE_ID_RE.fullmatch(fid) and (p:=SHARED_FILE_ROOT/fid).is_dir(): shutil.rmtree(p,ignore_errors=True); done.append(fid)
    return {"deleted":done,"count":len(done)}
'''
    t=rep(t,'@app.get("/api/ha/websocket-status")\n',api+'\n@app.get("/api/ha/websocket-status")\n')
    t=rep(t,'            async for event_bytes in run_jarvis_stream(request.message, request.session_id):\n','            effective_message=request.message+attachment_context(request.session_id,request.attachment_ids)\n            async for event_bytes in run_jarvis_stream(effective_message, request.session_id):\n')
    t=rep(t,'            async for event in run_jarvis_stream(request.message, request.session_id):\n','            effective_message=request.message+attachment_context(request.session_id,request.attachment_ids)\n            async for event in run_jarvis_stream(effective_message, request.session_id):\n')
    t=rep(t,'    oauth_available = bool(_github_oauth_client_id())\n    for item in result:\n','    oauth_available = bool(_github_oauth_client_id())\n    installed_by_url={str(p.get("url") or ""):p for p in plugin_registry().values()}\n    for item in result:\n        installed=installed_by_url.get(str(item.get("url") or "")); item["installed"]=bool(installed); item["installed_enabled"]=bool(installed and installed.get("enabled"))\n')
    M.write_text(t)
def index():
    t=I.read_text().replace('HUD 0.11.17','HUD 0.11.18'); t=rep(t,'    <button id="settings-tab">Settings</button>\n','    <button id="settings-tab">Settings</button>\n    <button id="files-tab">Shared Files</button>\n')
    t=rep(t,'        <form id="chat-form">\n','        <div id="chat-attachments" class="attachment-strip"></div>\n        <div class="attachment-controls"><button id="attach-file" type="button">📎 Attach</button><select id="attachment-scope"><option value="chat">This chat</option><option value="shared">Shared files</option></select><input id="attachment-input" type="file" multiple hidden><span id="attachment-state" class="muted"></span></div>\n        <form id="chat-form">\n')
    panel='''  <section id="files-panel" class="panel hidden"><div class="toolbar"><select id="shared-sort"><option value="date">Sort by date</option><option value="name">Sort by name</option></select><select id="shared-order"><option value="desc">Descending</option><option value="asc">Ascending</option></select><button id="shared-refresh" type="button">Refresh</button><button id="shared-use" type="button">Attach selected to chat</button><button id="shared-delete" type="button">Delete selected</button></div><div id="shared-summary" class="summary muted">Shared files are available to every chat.</div><div class="table-wrap"><table><thead><tr><th>Select</th><th>Name</th><th>Date</th><th>Type</th><th>Size</th></tr></thead><tbody id="shared-file-rows"></tbody></table></div></section>\n\n'''; t=rep(t,'  <section id="entities-panel" class="panel hidden">\n',panel+'  <section id="entities-panel" class="panel hidden">\n')
    t=rep(t,'</style>\n','    .attachment-controls,.attachment-strip{display:flex;gap:.45rem;align-items:center;flex-wrap:wrap}.attachment-chip{border:1px solid var(--line);border-radius:999px;padding:.25rem .55rem;font-size:.72rem;color:var(--cyan)}\n</style>\n')
    t=rep(t,'  const showPlugins = panel === "plugins";\n','  const showPlugins = panel === "plugins";\n  const showFiles = panel === "files";\n'); t=rep(t,'  pluginsPanel.classList.toggle("hidden", !showPlugins);\n','  pluginsPanel.classList.toggle("hidden", !showPlugins);\n  document.getElementById("files-panel")?.classList.toggle("hidden", !showFiles);\n'); t=rep(t,'  pluginsTab.classList.toggle("active", showPlugins);\n','  pluginsTab.classList.toggle("active", showPlugins);\n  document.getElementById("files-tab")?.classList.toggle("active", showFiles);\n')
    t=rep(t,'if (typeof loadPlugins === "function") await loadPlugins();\n          return;','if (typeof loadPlugins === "function") await loadPlugins();\n          if (typeof loadCatalog === "function") await loadCatalog(false);\n          return;')
    t=rep(t,'    if (item.auth_mode === "github-oauth" && install) {\n      if (item.oauth_available) {\n','    if (item.auth_mode === "github-oauth" && install) {\n      if (item.installed) { install.disabled=true; install.textContent=item.installed_enabled?"GitHub connected · enabled":"GitHub connected · installed"; }\n      else if (item.oauth_available) {\n')
    js=r'''\n(()=>{const tab=document.getElementById("files-tab"),rows=document.getElementById("shared-file-rows"),sort=document.getElementById("shared-sort"),order=document.getElementById("shared-order"),strip=document.getElementById("chat-attachments"),pick=document.getElementById("attachment-input"),scope=document.getElementById("attachment-scope"),state=document.getElementById("attachment-state");let pending=[],shared=[];const draw=()=>{strip.replaceChildren();pending.forEach(x=>{let s=document.createElement("span");s.className="attachment-chip";s.textContent=`${x.scope==="shared"?"Shared":"Chat"}: ${x.name}`;strip.appendChild(s)})};async function list(){let d=await pApi(`api/files/shared?sort=${sort.value}&order=${order.value}`);shared=d.files||[];rows.replaceChildren();shared.forEach(x=>{let r=document.createElement("tr");r.innerHTML=`<td><input type="checkbox" data-shared-id="${esc(x.file_id)}"></td><td>${esc(x.name)}</td><td>${new Date(x.created_at*1000).toLocaleString()}</td><td>${esc(x.mime_type)}</td><td>${Math.round(x.size/1024)} KB</td>`;rows.appendChild(r)});document.getElementById("shared-summary").textContent=`${shared.length} shared files · available to every chat`}document.getElementById("attach-file")?.addEventListener("click",()=>pick.click());pick?.addEventListener("change",async()=>{state.textContent="Uploading…";try{for(const f of pick.files){let b=new FormData();b.append("file",f);let p=scope.value==="shared"?"api/files/shared":`api/files/chat/${encodeURIComponent(jarvisChatSessionId)}`,r=await fetch(p,{method:"POST",body:b}),d=await r.json();if(!r.ok)throw Error(d.detail||r.status);pending.push(d)}draw();if(scope.value==="shared")await list();state.textContent="Ready"}catch(e){state.textContent=`Upload failed: ${e.message||e}`}pick.value=""});const ids=()=>[...rows.querySelectorAll("input[data-shared-id]:checked")].map(x=>x.dataset.sharedId);document.getElementById("shared-refresh")?.addEventListener("click",list);sort?.addEventListener("change",list);order?.addEventListener("change",list);document.getElementById("shared-use")?.addEventListener("click",()=>{let s=new Set(ids());shared.filter(x=>s.has(x.file_id)).forEach(x=>{if(!pending.some(p=>p.file_id===x.file_id))pending.push(x)});draw();showPanel("chat")});document.getElementById("shared-delete")?.addEventListener("click",async()=>{let x=ids();if(!x.length||!confirm(`Delete ${x.length} shared files?`))return;await pApi("api/files/shared",{method:"DELETE",headers:{"Content-Type":"application/json"},body:JSON.stringify({file_ids:x})});pending=pending.filter(p=>!x.includes(p.file_id));draw();await list()});tab?.addEventListener("click",async()=>{showPanel("files");await list()});const W=window.WebSocket;window.WebSocket=function(...a){let w=new W(...a),send=w.send.bind(w);w.send=d=>{try{let p=JSON.parse(d);if(p?.session_id&&typeof p.message==="string"&&!p.type){p.attachment_ids=pending.map(x=>x.file_id);pending=[];draw();return send(JSON.stringify(p))}}catch{}return send(d)};return w};window.WebSocket.prototype=W.prototype})();\n'''; n=t.rfind('</script>'); t=t[:n]+js+t[n:]; I.write_text(t)
def verify():
    m=M.read_text(); i=I.read_text();
    for s in ['version="0.11.18"','Path("/data/shared_files")','@app.delete("/api/files/shared")','attachment_ids: list[str]']: need(m,s)
    for s in ['id="files-tab"','Attach selected to chat','Delete selected','GitHub connected · installed','HUD 0.11.18']: need(i,s)
if __name__=='__main__': main(); index(); verify()
