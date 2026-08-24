(() => {
  document.addEventListener("click", async event => {
    const button = event.target.closest?.("button[data-copy-google-callback]");
    if (!button) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const callback = new URL("api/plugin-oauth/callback", window.location.href).href;
    const status = document.getElementById("catalog-status") || document.getElementById("plugin-state");
    try {
      await navigator.clipboard.writeText(callback);
      if (status) status.textContent = "OAuth callback copied. Add it as an authorized redirect URI in Google Cloud.";
    } catch (_) {
      if (status) status.textContent = `Google OAuth callback: ${callback}`;
    }
  }, true);
})();
