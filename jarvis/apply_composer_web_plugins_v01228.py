import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"ZBRANO v0.12.28 patch expected one {label} marker; found {count}"
        )
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.28 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    search_selector = '''<select id="web-search-mode" title="Choose how this message may use the public web"><option value="auto">Web · Auto</option><option value="search">Search Web</option><option value="off">Web Off</option></select>'''
    frontend = replace_once(
        frontend,
        search_selector,
        "",
        "old composer search selector",
    )
    frontend = replace_once(
        frontend,
        '''        </form>
        <div class="voice-bar">''',
        '''        </form>
        <div class="composer-context-row" aria-label="Message tools">
          <label class="composer-web-control" for="web-search-mode"><span aria-hidden="true">◎</span><span>Web</span><select id="web-search-mode" title="Choose how this message may use the public web"><option value="auto">Auto</option><option value="search">On</option><option value="off">Off</option></select></label>
          <div class="composer-plugin-context"><span class="composer-context-label">Plugins</span><div id="composer-plugin-icons" class="composer-plugin-icons" role="list" aria-label="Enabled plugins"><span class="composer-plugin-empty">Loading…</span></div></div>
        </div>
        <div class="voice-bar">''',
        "composer context row",
    )

    frontend = replace_once(
        frontend,
        '''  #web-search-mode { min-width: 7.5rem; }''',
        '''  #web-search-mode { min-width: 4.4rem; }
  .composer-context-row {
    display: flex;
    align-items: center;
    gap: .75rem;
    min-height: 2.25rem;
    padding: .35rem .15rem .2rem;
    color: var(--text-muted);
  }
  .composer-web-control,.composer-plugin-context {
    display: inline-flex;
    align-items: center;
    gap: .4rem;
    min-width: 0;
    font-size: .72rem;
    letter-spacing: .04em;
  }
  .composer-web-control {
    flex: 0 0 auto;
    padding-right: .75rem;
    border-right: 1px solid var(--line);
  }
  .composer-web-control select {
    min-height: 1.9rem;
    padding: .25rem 1.7rem .25rem .55rem;
    border-radius: 999px;
    font-size: .72rem;
  }
  .composer-plugin-context { flex: 1 1 auto; overflow: hidden; }
  .composer-context-label { flex: 0 0 auto; }
  .composer-plugin-icons { display: flex; align-items: center; gap: .3rem; min-width: 0; }
  .composer-plugin-button,.composer-plugin-overflow {
    position: relative;
    display: inline-grid;
    place-items: center;
    flex: 0 0 auto;
    width: 1.8rem;
    height: 1.8rem;
    min-height: 0;
    padding: 0;
    border: 1px solid var(--line);
    border-radius: 50%;
    background: color-mix(in srgb, var(--surface-strong) 82%, transparent);
  }
  .composer-plugin-button:hover,.composer-plugin-button:focus-visible { border-color: var(--cyan); transform: translateY(-1px); }
  .composer-plugin-button img { width: 1rem; height: 1rem; object-fit: contain; }
  .composer-plugin-fallback { font-size: .68rem; font-weight: 650; color: var(--cyan); }
  .composer-plugin-status {
    position: absolute;
    right: -.08rem;
    bottom: -.08rem;
    width: .45rem;
    height: .45rem;
    border: 2px solid var(--surface-strong);
    border-radius: 50%;
    background: #d29a32;
  }
  .composer-plugin-button.available .composer-plugin-status { background: #2faa76; }
  .composer-plugin-button.unhealthy .composer-plugin-status { background: #d35d62; }
  .composer-plugin-overflow { width: auto; min-width: 1.8rem; padding: 0 .38rem; border-radius: 999px; font-size: .66rem; }
  .composer-plugin-empty { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: .7rem; }
  @media (max-width: 680px) {
    .composer-context-row { align-items: flex-start; flex-wrap: wrap; }
    .composer-plugin-context { flex-basis: 100%; }
    .composer-web-control { border-right: 0; padding-right: 0; }
  }''',
        "composer context styling",
    )

    frontend = replace_once(
        frontend,
        '''    const ps=(await pApi("api/plugins")).plugins||[];
    if(!ps.length){listNode.innerHTML='<div class="muted">No plugins installed.</div>';return}''',
        '''    const ps=(await pApi("api/plugins")).plugins||[];
    if(typeof window.renderComposerPluginIndicators==="function")window.renderComposerPluginIndicators(ps);
    if(!ps.length){listNode.innerHTML='<div class="muted">No plugins installed.</div>';return}''',
        "plugin workspace synchronization",
    )

    composer_script = r'''
<script id="zbrano-v01228-composer-context">
(() => {
  const root=document.getElementById("composer-plugin-icons");
  if(!root)return;
  const esc=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"})[char]);
  const visibleLimit=7;

  function stateLabel(plugin){
    if(!plugin.healthy)return "unhealthy";
    if(plugin.available_to_chat)return `${plugin.enabled_tool_count||0} enabled tool${Number(plugin.enabled_tool_count||0)===1?"":"s"} · available to chat`;
    return plugin.builtin?"enabled · Developer Mode only":"enabled · no tools available to chat";
  }

  function iconButton(plugin){
    const name=String(plugin.name||"Plugin");
    const fallback=esc(name.trim().charAt(0).toUpperCase()||"P");
    const icon=plugin.icon_url
      ?`<img src="${esc(plugin.icon_url)}" alt="" loading="lazy" referrerpolicy="no-referrer"><span class="composer-plugin-fallback" hidden>${fallback}</span>`
      :`<span class="composer-plugin-fallback">${fallback}</span>`;
    const status=!plugin.healthy?"unhealthy":plugin.available_to_chat?"available":"enabled";
    const title=`${name} · ${stateLabel(plugin)}`;
    return `<button type="button" class="composer-plugin-button ${status}" data-composer-plugin="${esc(plugin.id||"")}" title="${esc(title)}" aria-label="${esc(title)}" role="listitem">${icon}<span class="composer-plugin-status" aria-hidden="true"></span></button>`;
  }

  window.renderComposerPluginIndicators=plugins=>{
    const enabled=(plugins||[]).filter(plugin=>plugin&&plugin.enabled);
    if(!enabled.length){root.innerHTML='<span class="composer-plugin-empty">None enabled</span>';return}
    const visible=enabled.slice(0,visibleLimit);
    const overflow=enabled.length-visible.length;
    root.innerHTML=visible.map(iconButton).join("")+(overflow?`<span class="composer-plugin-overflow" title="${overflow} more enabled plugin${overflow===1?"":"s"}">+${overflow}</span>`:"");
    for(const image of root.querySelectorAll("img"))image.addEventListener("error",()=>{image.hidden=true;if(image.nextElementSibling)image.nextElementSibling.hidden=false},{once:true});
  };

  async function refresh(){
    try{
      const response=await fetch("api/plugins",{cache:"no-store"});
      const data=await response.json().catch(()=>({}));
      if(!response.ok)throw new Error(data.detail||`HTTP ${response.status}`);
      window.renderComposerPluginIndicators(data.plugins||[]);
    }catch(error){root.innerHTML='<span class="composer-plugin-empty">Plugins unavailable</span>'}
  }

  root.addEventListener("click",event=>{
    if(!event.target.closest("[data-composer-plugin]"))return;
    document.getElementById("plugins-tab")?.click();
  });
  document.getElementById("chat-tab")?.addEventListener("click",refresh);
  refresh();
})();
</script>
'''
    frontend = replace_once(
        frontend,
        "\n</body>",
        composer_script + "\n</body>",
        "composer plugin runtime",
    )

    backend = backend.replace('version="0.12.27"', 'version="0.12.28"')
    backend = backend.replace('"version": "0.12.27"', '"version": "0.12.28"')
    frontend = frontend.replace("HUD 0.12.27", "HUD 0.12.28")

    require(frontend, 'id="composer-plugin-icons"', "enabled plugin indicators")
    require(frontend, 'id="web-search-mode"', "relocated Web selector")
    require(frontend, "window.renderComposerPluginIndicators", "plugin indicator refresh")
    require(backend, 'version="0.12.28"', "backend version")
    require(frontend, "HUD 0.12.28", "HUD version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
