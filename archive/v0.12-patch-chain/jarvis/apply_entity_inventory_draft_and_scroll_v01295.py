import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.95 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.95 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    endpoint_start = backend.find('@app.post("/api/memory/entity-catalog-draft")')
    endpoint_end = backend.find('\n\n@app.get("/api/ha/states/{entity_id}")', endpoint_start)
    if endpoint_start < 0 or endpoint_end < 0:
        raise RuntimeError("ZBRANO v0.12.95 could not locate the obsolete entity draft endpoint")
    replacement = '''@app.post("/api/memory/entity-catalog-draft")
async def prepare_entity_catalog_draft(
    request: EntityCatalogDraftRequest,
) -> dict[str, Any]:
    """Prepare a reviewable inventory without bypassing Workshop Memory approval."""
    markdown = entity_catalog_markdown(request.entities)
    return {
        "prepared": True,
        "saved": False,
        "project": request.project,
        "entity_count": len(request.entities),
        "catalog_markdown": markdown,
        "filename": "HA OS Entities Update Draft.md",
        "permanent_project_notes_changed": False,
        "review_required": True,
        "next_step": "Attach this draft in chat and ask ZBRANO to reconcile it with the existing Workshop Memory entity note.",
    }
'''
    backend = backend[:endpoint_start] + replacement + backend[endpoint_end:]

    frontend = replace_once(
        frontend,
        '<button id="save-memory-draft">Optional Memory Draft</button>',
        '<button id="save-memory-draft" title="Download selected stable entity metadata for a later approved Workshop Memory update">Prepare Entity Inventory Update</button>',
        "entity inventory action label",
    )
    handler_start = frontend.find('saveMemoryDraft.addEventListener("click", async () => {')
    handler_end = frontend.find('\n\nshowApproved.addEventListener("click", async () => {', handler_start)
    if handler_start < 0 or handler_end < 0:
        raise RuntimeError("ZBRANO v0.12.95 could not locate the entity draft frontend handler")
    handler = r'''saveMemoryDraft.addEventListener("click", async () => {
  const entities = selectedCatalog();
  if (!entities.length) {
    entitySummary.textContent = "Select at least one entity before preparing an inventory update.";
    return;
  }

  saveMemoryDraft.disabled = true;
  entitySummary.textContent = `Preparing a reviewable update for ${entities.length} selected entities…`;
  try {
    const response = await fetch("api/memory/entity-catalog-draft", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({project: "ZBRANO Workshop Assistant", entities}),
    });
    const responseText = await response.text();
    let data = {};
    try { data = responseText ? JSON.parse(responseText) : {}; }
    catch { data = {detail: responseText.slice(0, 500) || `HTTP ${response.status}`}; }
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    if (!data.catalog_markdown) throw new Error("The server returned no entity inventory content");

    const blob = new Blob([data.catalog_markdown], {type: "text/markdown;charset=utf-8"});
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = data.filename || "HA OS Entities Update Draft.md";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    entitySummary.textContent = `Prepared ${entities.length} entities as ${link.download}. No Workshop Memory note was changed; attach the draft in chat when you want an approved reconciliation.`;
  } catch (error) {
    entitySummary.textContent = `Could not prepare entity inventory update: ${error.message || error}`;
  } finally {
    saveMemoryDraft.disabled = false;
  }
});'''
    frontend = frontend[:handler_start] + handler + frontend[handler_end:]

    frontend = replace_once(
        frontend,
        '''  const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;
  const SEEN_KEY="zbrano_spoken_suggestions_v1";''',
        '''  const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;
  const braveBrowser=Boolean(navigator.brave)||Boolean(navigator.userAgentData?.brands?.some(item=>String(item.brand||"").toLowerCase().includes("brave")));
  const SEEN_KEY="zbrano_spoken_suggestions_v1";''',
        "Brave wake compatibility detection",
    )
    frontend = replace_once(
        frontend,
        '''  function wakeCanRun(){return Boolean(wakeEnabled.checked&&Recognition&&!document.hidden&&!pendingSuggestion&&!activeAudio&&!speechQueueRunning&&!mediaRecorder&&!activeRequest)}''',
        '''  function wakeCanRun(){return Boolean(wakeEnabled.checked&&Recognition&&!braveBrowser&&!document.hidden&&!pendingSuggestion&&!activeAudio&&!speechQueueRunning&&!mediaRecorder&&!activeRequest)}
  function showWakeCompatibility(){
    if(braveBrowser){wakeEnabled.checked=false;stopWake();status("Browser wake phrase is unavailable in Brave. Use Chrome or Edge, or connect a local Home Assistant voice satellite. Push-to-talk still works.","error");return false}
    if(!Recognition){wakeEnabled.checked=false;stopWake();status("Wake phrase is unavailable in this browser. Use current Chrome or Edge, or connect a local Home Assistant voice satellite.","error");return false}
    return true;
  }''',
        "wake compatibility guard",
    )
    frontend = replace_once(
        frontend,
        '''  wakeEnabled.addEventListener("change",()=>{if(wakeEnabled.checked){if(!Recognition){wakeEnabled.checked=false;status("Wake phrase is not supported by this browser. Use current Chrome or Edge, or a Home Assistant voice satellite.","error")}else startWake()}else{stopWake();status("Wake listening is off. It works only while this page is open and microphone permission is granted.")}});''',
        '''  wakeEnabled.addEventListener("change",()=>{if(wakeEnabled.checked){if(showWakeCompatibility())startWake()}else{stopWake();status(braveBrowser?"Browser wake phrase is unavailable in Brave. Use Chrome or Edge, or connect a local Home Assistant voice satellite. Push-to-talk still works.":"Wake listening is off. It works only while this page is open and microphone permission is granted.",braveBrowser?"error":"")}});''',
        "wake toggle compatibility behavior",
    )
    frontend = replace_once(
        frontend,
        '''  window.addEventListener("zbrano-voice-preferences-loaded",()=>{if(wakeEnabled.checked)startWake();else status("Wake listening is off. It works only while this page is open and microphone permission is granted.")});''',
        '''  window.addEventListener("zbrano-voice-preferences-loaded",()=>{if(wakeEnabled.checked){if(showWakeCompatibility())startWake()}else if(braveBrowser)showWakeCompatibility();else status("Wake listening is off. It works only while this page is open and microphone permission is granted.")});''',
        "loaded wake compatibility behavior",
    )

    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.95 could not locate stylesheet")
    styles = r'''
    /* v0.12.95 reliable Entities viewport scrolling. */
    #entities-panel { display:flex; flex-direction:column; min-height:0; overflow:hidden; }
    #entities-panel .toolbar, #entities-panel .summary { flex:0 0 auto; }
    #entities-panel .table-wrap { flex:1 1 auto; min-height:0; height:auto; max-height:none; overflow:auto; overscroll-behavior:contain; -webkit-overflow-scrolling:touch; scrollbar-gutter:stable; }
    #entities-panel .table-wrap table { margin:0; }
'''
    frontend = frontend[:style_close] + styles + frontend[style_close:]

    backend = backend.replace('version="0.12.94"', 'version="0.12.95"')
    backend = backend.replace('"version": "0.12.94"', '"version": "0.12.95"')
    frontend = frontend.replace("HUD 0.12.94", "HUD 0.12.95")

    for marker, location in [
        ('version="0.12.95"', backend),
        ('async def prepare_entity_catalog_draft(', backend),
        ('"saved": False', backend),
        ('Prepare Entity Inventory Update', frontend),
        ('const responseText = await response.text()', frontend),
        ('#entities-panel .table-wrap { flex:1 1 auto', frontend),
        ('const braveBrowser=Boolean(navigator.brave)', frontend),
        ('Browser wake phrase is unavailable in Brave', frontend),
        ('HUD 0.12.95', frontend),
    ]:
        require(location, marker, marker)
    if '"save_session_draft"' in backend:
        raise RuntimeError("ZBRANO v0.12.95 still contains the obsolete save_session_draft call")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
