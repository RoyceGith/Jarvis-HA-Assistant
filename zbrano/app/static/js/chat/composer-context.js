(() => {
  const root=document.getElementById("composer-plugin-icons");
  if(!root)return;
  const count=document.getElementById("composer-plugin-count");
  const open=document.getElementById("composer-plugins-open");
  const esc=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"})[char]);

  function stateLabel(plugin){
    if(!plugin.enabled)return "installed · disabled";
    if(!plugin.healthy)return "unhealthy";
    if(plugin.available_to_chat)return `${plugin.enabled_tool_count||0} enabled tool${Number(plugin.enabled_tool_count||0)===1?"":"s"} · available to chat`;
    return plugin.builtin?"enabled · Developer Mode only":"enabled · no tools available to chat";
  }

  function iconButton(plugin){
    const name=String(plugin.name||"Plugin");
    const fallback=esc(name.trim().charAt(0).toUpperCase()||"P");
    const githubIcon=String(plugin.icon_url||"").toLowerCase().endsWith("plugin-icons/github.svg");
    const icon=githubIcon
      ?'<svg class="composer-plugin-inline-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 .3a12 12 0 0 0-3.8 23.4c.6.1.8-.3.8-.6v-2.1c-3.3.7-4-1.6-4-1.6-.6-1.4-1.4-1.8-1.4-1.8-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1.1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.8-1.6-2.7-.3-5.5-1.3-5.5-5.9 0-1.3.5-2.4 1.2-3.2-.1-.3-.5-1.5.1-3.2 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0c2.3-1.5 3.3-1.2 3.3-1.2.6 1.7.2 2.9.1 3.2.8.8 1.2 1.9 1.2 3.2 0 4.6-2.8 5.6-5.5 5.9.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A12 12 0 0 0 12 .3Z"/></svg>'
      :plugin.icon_url
      ?`<img data-plugin-icon-src="${esc(plugin.icon_url)}" alt="" referrerpolicy="no-referrer"><span class="composer-plugin-fallback" hidden>${fallback}</span>`
      :`<span class="composer-plugin-fallback">${fallback}</span>`;
    const status=!plugin.enabled?"disabled":!plugin.healthy?"unhealthy":plugin.available_to_chat?"available":"enabled";
    const title=`${name} · ${stateLabel(plugin)}`;
    return `<button type="button" class="composer-plugin-button ${status}" data-composer-plugin="${esc(plugin.id||"")}" title="${esc(title)}" aria-label="${esc(title)}" role="listitem">${icon}<span class="composer-plugin-status" aria-hidden="true"></span></button>`;
  }

  window.renderComposerPluginIndicators=plugins=>{
    const installed=(plugins||[]).filter(Boolean);
    if(count){count.textContent=String(installed.length);count.setAttribute("aria-label",`${installed.length} installed plugin${installed.length===1?"":"s"}`)}
    if(!installed.length){root.innerHTML='<span class="composer-plugin-empty">None installed</span>';return}
    root.innerHTML=installed.map(iconButton).join("");
    for(const image of root.querySelectorAll("img[data-plugin-icon-src]")){
      image.addEventListener("error",()=>{image.hidden=true;if(image.nextElementSibling)image.nextElementSibling.hidden=false},{once:true});
      image.addEventListener("load",()=>image.classList.add("loaded"),{once:true});
      image.src=image.dataset.pluginIconSrc;
    }
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
  open?.addEventListener("click",()=>document.getElementById("plugins-tab")?.click());
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
