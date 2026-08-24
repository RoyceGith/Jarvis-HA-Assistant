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

(() => {
  const shell = document.querySelector(".chat-shell");
  const sidebar = document.querySelector(".chat-sidebar");
  const toggle = document.getElementById("conversations-toggle");
  if (!shell || !sidebar || !toggle) return;
  const storageKey = "zbrano_conversations_collapsed";
  const applyCollapsed = collapsed => {
    shell.classList.toggle("conversations-collapsed", collapsed);
    sidebar.classList.toggle("conversations-collapsed", collapsed);
    toggle.textContent = collapsed ? ">" : "<";
    toggle.setAttribute("aria-expanded", String(!collapsed));
    toggle.setAttribute("aria-label", collapsed ? "Show conversations" : "Hide conversations");
  };
  const savedCollapse = localStorage.getItem(storageKey);
  const phoneDefault = window.matchMedia("(max-width: 760px)").matches;
  applyCollapsed(savedCollapse === null ? phoneDefault : savedCollapse === "1");
  toggle.addEventListener("click", () => {
    const collapsed = !sidebar.classList.contains("conversations-collapsed");
    localStorage.setItem(storageKey, collapsed ? "1" : "0");
    applyCollapsed(collapsed);
  });
})();
