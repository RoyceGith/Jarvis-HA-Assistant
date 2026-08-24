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
