from pathlib import Path

ROOT = Path("/opt/jarvis")
INDEX = ROOT / "app/static/index.html"
MAIN = ROOT / "app/main.py"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"Jarvis v0.11.9 patch missing: {label}")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")
    require(text, "</script>", "script close")

    runtime = r'''
(() => {
  const byId = id => document.getElementById(id);
  let catalogSearchTimer = null;

  document.addEventListener("input", event => {
    if (event.target?.id !== "catalog-search") return;
    clearTimeout(catalogSearchTimer);
    catalogSearchTimer = window.setTimeout(() => {
      if (typeof loadCatalog === "function") loadCatalog(false);
    }, 250);
  }, true);

  document.addEventListener("change", event => {
    if (event.target?.id !== "catalog-category") return;
    if (typeof loadCatalog === "function") loadCatalog(false);
  }, true);

  document.addEventListener("click", async event => {
    const refresh = event.target.closest?.("#catalog-refresh");
    if (refresh) {
      event.preventDefault();
      event.stopImmediatePropagation();
      if (typeof loadCatalog === "function") await loadCatalog(true);
      return;
    }

    const install = event.target.closest?.("button[data-catalog-install]");
    if (install) {
      event.preventDefault();
      event.stopImmediatePropagation();

      const status = byId("catalog-status");
      const catalogId = install.dataset.catalogInstall;
      if (!catalogId) {
        if (status) status.textContent = "Install failed: missing catalog plugin ID.";
        return;
      }

      const token = window.prompt(
        "GitHub requires a personal access token. Enter the bearer token, or leave blank for plugins that do not require authentication."
      );
      if (token === null) return;

      install.disabled = true;
      if (status) status.textContent = "Validating and installing plugin…";
      try {
        const result = await pApi(
          `api/plugin-catalog/${encodeURIComponent(catalogId)}/install`,
          {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({bearer_token: token.trim()})
          }
        );
        if (status) {
          status.textContent = result?.installed
            ? "Plugin installed disabled. Review its tools, then enable it."
            : "Plugin installation completed.";
        }
        if (typeof loadPlugins === "function") await loadPlugins();
      } catch (error) {
        if (status) status.textContent = `Install failed: ${error.message || error}`;
      } finally {
        install.disabled = false;
      }
      return;
    }

    const newChat = event.target.closest?.("#new-chat-button, #clear-chat");
    if (newChat) {
      event.preventDefault();
      event.stopImmediatePropagation();

      try {
        if (typeof stopActiveRequest === "function") stopActiveRequest();
      } catch {}

      jarvisChatSessionId = crypto.randomUUID
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random()}`;
      localStorage.setItem("jarvis_chat_session_id", jarvisChatSessionId);

      const messagesNode = byId("messages");
      if (messagesNode) {
        messagesNode.innerHTML =
          '<div class="message jarvis">Jarvis intelligence core online.</div>';
      }

      const inputNode = byId("message");
      if (inputNode) {
        inputNode.value = "";
        inputNode.focus();
        inputNode.dispatchEvent(new Event("input", {bubbles: true}));
      }

      const fragment = byId("session-fragment");
      if (fragment) fragment.textContent = "ACTIVE";

      try {
        if (typeof loadChatList === "function") await loadChatList();
        else if (typeof loadChats === "function") await loadChats();
      } catch {}
    }
  }, true);
})();
'''

    last_script = text.rfind("</script>")
    text = text[:last_script] + runtime + "\n" + text[last_script:]
    text = text.replace("HUD 0.11.8", "HUD 0.11.9")
    INDEX.write_text(text, encoding="utf-8")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    text = text.replace('version="0.11.8"', 'version="0.11.9"')
    text = text.replace('"version": "0.11.8"', '"version": "0.11.9"')
    MAIN.write_text(text, encoding="utf-8")


def verify() -> None:
    index = INDEX.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")

    required = (
        'event.target?.id !== "catalog-search"',
        'button[data-catalog-install]',
        'api/plugin-catalog/${encodeURIComponent(catalogId)}/install',
        '#new-chat-button, #clear-chat',
        'localStorage.setItem("jarvis_chat_session_id", jarvisChatSessionId)',
        'event.stopImmediatePropagation()',
    )
    missing = [marker for marker in required if marker not in index]
    if "0.11.9" not in main:
        missing.append("backend version 0.11.9")

    first_script_end = index.find("</script>")
    delegated_pos = index.find('event.target?.id !== "catalog-search"')
    if delegated_pos <= first_script_end:
        missing.append("delegated controls inserted before final DOM")

    if missing:
        raise RuntimeError(
            "Jarvis v0.11.9 verification failed: " + ", ".join(missing)
        )


if __name__ == "__main__":
    patch_index()
    patch_main()
    verify()
