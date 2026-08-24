(() => {
  const statusNode=()=>document.getElementById("catalog-status")||document.getElementById("plugin-state");
  const callbackUrl=()=>new URL("api/plugin-oauth/callback",window.location.href).href;

  async function startPluginOAuth(endpoint){
    const popup=window.open("about:blank","zbrano-plugin-oauth","popup,width=680,height=760");
    if(!popup){throw new Error("Allow pop-ups for ZBRANO, then press Connect again")}
    // Home Assistant Ingress uses a SameSite session cookie. An OAuth redirect
    // arriving from another site can therefore receive one Supervisor 401 before
    // the browser is back in the Home Assistant site context. Detect only that
    // exact callback failure and repeat it once as a same-site navigation.
    let ingressCallbackRetryUsed=false;
    const ingressCallbackMonitor=window.setInterval(()=>{
      if(popup.closed){window.clearInterval(ingressCallbackMonitor);return;}
      try{
        const popupUrl=new URL(popup.location.href);
        const callbackPath=popupUrl.pathname.endsWith("/api/plugin-oauth/callback");
        const callbackState=popupUrl.searchParams.has("state");
        if(popupUrl.origin!==window.location.origin||!callbackPath||!callbackState)return;
        const pageText=`${popup.document.title||""} ${popup.document.body?.textContent||""}`;
        if(!ingressCallbackRetryUsed&&/\b401\b[\s\S]*unauthorized/i.test(pageText)){
          ingressCallbackRetryUsed=true;
          const status=statusNode();
          if(status)status.textContent="Completing authorization through Home Assistantâ€¦";
          if(popup.document.body){
            popup.document.title="Completing authorization";
            popup.document.body.style.cssText="font:16px system-ui;background:#071015;color:#d9fbff;padding:2rem";
            popup.document.body.innerHTML="<h1>Completing authorization</h1><p>Returning securely through Home Assistantâ€¦</p>";
          }
          popup.location.replace(popupUrl.href);
        }
      }catch(_error){/* The popup is on Cloudflare; cross-origin access is expected. */}
    },250);
    window.setTimeout(()=>window.clearInterval(ingressCallbackMonitor),600000);
    const status=statusNode();
    try{
      if(status)status.textContent="Preparing secure authorization…";
      const result=await pApi(endpoint,{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({redirect_uri:callbackUrl()})
      });
      popup.location.replace(result.authorization_url);
      if(status)status.textContent="Complete authorization in the provider window.";
    }catch(error){
      popup.close();
      throw error;
    }
  }

  window.zbranoStartPluginOAuth = startPluginOAuth;

  document.addEventListener("click",async event=>{
    const catalogButton=event.target.closest?.("button[data-oauth-connect]");
    const installedButton=event.target.closest?.('button[data-a="oauth"]');
    const disconnectButton=event.target.closest?.('button[data-a="oauth-disconnect"]');
    if(!catalogButton&&!installedButton&&!disconnectButton)return;
    event.preventDefault();event.stopImmediatePropagation();
    const button=catalogButton||installedButton||disconnectButton;
    button.disabled=true;
    try{
      if(disconnectButton){
        if(!window.confirm("Sign out and remove this plugin's stored OAuth tokens?"))return;
        await pApi(`api/plugins/${encodeURIComponent(disconnectButton.dataset.id)}/oauth/disconnect`,{method:"POST"});
        const status=statusNode();if(status)status.textContent="OAuth disconnected.";
        await Promise.all([loadPlugins(),loadCatalog(false)]);
      }else if(catalogButton){
        await startPluginOAuth(`api/plugin-catalog/${encodeURIComponent(catalogButton.dataset.oauthConnect)}/oauth/start`);
      }else{
        await startPluginOAuth(`api/plugins/${encodeURIComponent(installedButton.dataset.id)}/oauth/start`);
      }
    }catch(error){
      const status=statusNode();if(status)status.textContent=`OAuth failed: ${error.message||error}`;
    }finally{button.disabled=false}
  },true);

  window.addEventListener("message",async event=>{
    if(event.origin!==window.location.origin||event.data?.type!=="zbrano-plugin-oauth")return;
    const status=statusNode();
    if(status)status.textContent=event.data.success
      ?"Authorized and connected. Tools are enabled with write actions approval-gated."
      :`Authorization failed: ${event.data.message||"Unknown error"}`;
    await Promise.all([loadPlugins(),loadCatalog(false)]);
  });
})();
