import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.37 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.37 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        'INTERNAL_CHAT_SESSION_PREFIXES = ("zbrano-diagnostic-",)',
        'INTERNAL_CHAT_SESSION_PREFIXES = ("zbrano-diagnostic-", "zbrano-playwright-")',
        "internal Playwright chat prefix",
    )
    backend = replace_once(
        backend,
        '''    url = _playwright_local_url(path)
    normalized_surface = str(surface or "chat").strip().lower()''',
        '''    url = _playwright_local_url(path)
    inspection_url = f"{url}?zbrano_inspection=1"
    normalized_surface = str(surface or "chat").strip().lower()''',
        "inspection URL marker",
    )
    backend = replace_once(
        backend,
        '{"name": "browser_navigate", "arguments": {"url": url}},',
        '{"name": "browser_navigate", "arguments": {"url": inspection_url}},',
        "isolated Playwright navigation",
    )

    frontend = replace_once(
        frontend,
        '''let jarvisChatSessionId =
  localStorage.getItem("jarvis_chat_session_id") ||
  (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`);
localStorage.setItem("jarvis_chat_session_id", jarvisChatSessionId);''',
        '''const zbranoInspectionSession =
  new URLSearchParams(window.location.search).get("zbrano_inspection") === "1";
let jarvisChatSessionId = zbranoInspectionSession
  ? "zbrano-playwright-inspection"
  : localStorage.getItem("jarvis_chat_session_id") ||
    (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`);
if (!zbranoInspectionSession) {
  localStorage.setItem("jarvis_chat_session_id", jarvisChatSessionId);
}''',
        "inspection chat identity",
    )

    status_start = frontend.find('    <div class="runtime-status-stack">')
    status_end = frontend.find("    </div>", status_start)
    if status_start < 0 or status_end < 0:
        raise RuntimeError("ZBRANO v0.12.37 patch could not locate the runtime status stack")
    status_block = frontend[status_start:status_end]
    status_lines = status_block.splitlines()
    health_line = next((line for line in status_lines if 'id="health"' in line), "")
    developer_line = next((line for line in status_lines if 'id="developer-mode-indicator"' in line), "")
    if not health_line or not developer_line:
        raise RuntimeError("ZBRANO v0.12.37 patch could not locate both runtime indicators")
    status_block = status_block.replace(
        f"{health_line}\n{developer_line}",
        f"{developer_line}\n{health_line}",
        1,
    )
    frontend = frontend[:status_start] + status_block + frontend[status_end:]

    frontend = replace_once(
        frontend,
        '''        <div class="chat-sidebar-header">
          <h2>CONVERSATIONS</h2>
          <button id="new-chat-button" type="button" aria-label="Start new chat">＋</button>
        </div>''',
        '''        <div class="chat-sidebar-header">
          <button id="conversations-toggle" type="button" aria-label="Hide conversations" aria-expanded="true">&lt;</button>
          <h2>CONVERSATIONS</h2>
          <button id="new-chat-button" type="button" aria-label="Start new chat">＋</button>
        </div>''',
        "conversation collapse control",
    )

    style_close = frontend.find("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.37 patch could not locate the stylesheet")
    conversation_css = r'''
    #conversations-toggle, #new-chat-button, .chat-rename, .chat-delete {
      width: 1.8rem;
      height: 1.8rem;
      min-width: 1.8rem;
      padding: 0;
      display: inline-grid;
      place-items: center;
      font-size: .76rem;
      line-height: 1;
    }
    #conversations-toggle { color: var(--text-muted); }
    .chat-sidebar-header h2 { flex: 1; min-width: 0; }
    .chat-shell.conversations-collapsed { grid-template-columns: 2.7rem minmax(0, 1fr); }
    .chat-sidebar.conversations-collapsed { padding: .45rem; }
    .chat-sidebar.conversations-collapsed .chat-sidebar-header { justify-content: center; margin: 0; }
    .chat-sidebar.conversations-collapsed .chat-sidebar-header h2,
    .chat-sidebar.conversations-collapsed #new-chat-button,
    .chat-sidebar.conversations-collapsed #chat-list { display: none; }
    @media (max-width: 900px) {
      .chat-shell.conversations-collapsed { grid-template-columns: 1fr; }
      .chat-sidebar.conversations-collapsed { min-height: 2.7rem; max-height: 2.7rem; }
      .chat-sidebar.conversations-collapsed .chat-sidebar-header { justify-content: flex-start; }
    }
'''
    frontend = frontend[:style_close] + conversation_css + frontend[style_close:]

    script_close = frontend.rfind("</script>")
    if script_close < 0:
        raise RuntimeError("ZBRANO v0.12.37 patch could not locate the application script")
    conversation_controller = r'''
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
  applyCollapsed(localStorage.getItem(storageKey) === "1");
  toggle.addEventListener("click", () => {
    const collapsed = !sidebar.classList.contains("conversations-collapsed");
    localStorage.setItem(storageKey, collapsed ? "1" : "0");
    applyCollapsed(collapsed);
  });
})();
'''
    frontend = frontend[:script_close] + conversation_controller + frontend[script_close:]

    backend = backend.replace('version="0.12.36"', 'version="0.12.37"')
    backend = backend.replace('"version": "0.12.36"', '"version": "0.12.37"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.36"', '"X-ZBRANO-Frontend-Version": "0.12.37"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.36"', '"name": "ZBRANO Developer Mode", "version": "0.12.37"')
    frontend = frontend.replace("HUD 0.12.36", "HUD 0.12.37")

    require(backend, '"zbrano-playwright-"', "internal Playwright prefix")
    require(backend, 'inspection_url = f"{url}?zbrano_inspection=1"', "inspection navigation marker")
    require(backend, '"url": inspection_url', "isolated browser destination")
    require(frontend, 'new URLSearchParams(window.location.search)', "inspection marker detection")
    require(frontend, '? "zbrano-playwright-inspection"', "internal inspection session")
    require(frontend, 'id="conversations-toggle"', "conversation collapse control")
    require(frontend, 'zbrano_conversations_collapsed', "persisted conversation collapse preference")
    require(frontend, '.chat-shell.conversations-collapsed', "collapsed conversation layout")
    if frontend.find('id="developer-mode-indicator"') > frontend.find('id="health"'):
        raise RuntimeError("ZBRANO v0.12.37 patch failed to place Developer Mode above Online/version")
    require(backend, 'version="0.12.37"', "backend version")
    require(frontend, "HUD 0.12.37", "HUD version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
