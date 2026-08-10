import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.38 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.38 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    mobile_css = r'''
    /* v0.12.38 compact phone layout keeps the conversation viewport usable. */
    #automations-panel::before { display: none; }
    #autonomy-settings-form,
    #automation-draft-form {
      display: block;
      min-width: 0;
      margin-top: .65rem;
    }
    .autonomy-safety-grid > .autonomy-card,
    .autonomy-form-grid,
    .autonomy-form-grid label { min-width: 0; }
    .autonomy-form-grid input,
    .autonomy-form-grid select,
    .autonomy-form-grid textarea {
      display: block;
      width: 100%;
      max-width: 100%;
      min-width: 0;
    }
    .autonomy-form-actions { flex-wrap: wrap; }
    #autonomy-settings-state { min-width: 0; overflow-wrap: anywhere; }
    .chat-title-editor {
      height: 1.8rem;
      min-height: 1.8rem;
      padding: 0 .45rem;
      line-height: 1.8rem;
    }
    @media (max-width: 760px) {
      main {
        padding: .28rem;
        grid-template-rows: auto auto minmax(0, 1fr);
      }
      header { min-height: 1.9rem; gap: .4rem; }
      header h1 { margin: 0; font-size: 1rem; letter-spacing: .14em; }
      .developer-mode-indicator { padding: .2rem .35rem; font-size: .55rem; letter-spacing: .04em; }
      nav {
        flex-wrap: nowrap;
        gap: .24rem;
        margin: .24rem 0;
        overflow-x: auto;
        overscroll-behavior-x: contain;
        scrollbar-width: none;
      }
      nav::-webkit-scrollbar { display: none; }
      nav button {
        flex: 0 0 auto;
        padding: .4rem .52rem;
        font-size: .7rem;
        line-height: 1.1;
      }
      #developer-tab { margin-left: 0; }
      #developer-tab::before { margin-right: .22rem; }
      .panel { padding: .32rem; border-radius: 5px; }
      .panel::before { display: none; }
      .chat-shell { gap: .32rem; }
      .chat-sidebar {
        padding: .38rem;
        max-height: min(28dvh, 10rem);
        border-radius: 7px;
      }
      .chat-sidebar-header { margin-bottom: .32rem; gap: .3rem; }
      .chat-sidebar.conversations-collapsed {
        min-height: 2.25rem;
        max-height: 2.25rem;
        padding: .2rem .35rem;
      }
      #conversations-toggle, #new-chat-button, .chat-rename, .chat-delete {
        width: 1.65rem;
        height: 1.65rem;
        min-width: 1.65rem;
      }
      .chat-title-editor {
        height: 1.65rem;
        min-height: 1.65rem;
        line-height: 1.65rem;
        font-size: .75rem;
      }
      #chat-list { gap: .15rem; }
      .chat-open { padding: .38rem .42rem; font-size: .75rem; }
      .hud-layout, .core-stage { min-height: 0; }
      #messages { min-height: 5rem; padding: .2rem; }
      .message {
        padding: .42rem .45rem .42rem 3.25rem;
        margin: .18rem 0;
        font-size: .86rem;
        line-height: 1.42;
      }
      .message::before { left: .42rem; top: .58rem; font-size: .58rem; }
      .message h2 { font-size: 1.06rem; }
      .message h3 { font-size: .98rem; }
      .message h4 { font-size: .92rem; }
      .attachment-strip { margin-top: .2rem; }
      .attachment-controls { gap: .28rem; margin-top: .22rem; }
      .attachment-controls button,
      .attachment-controls select { min-height: 1.9rem; padding: .3rem .42rem; font-size: .68rem; }
      #chat-form {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: .28rem;
        margin-top: .32rem;
      }
      .composer-input-stack { grid-column: 1 / -1; width: 100%; }
      .composer-input-stack #message { min-height: 2.7rem; max-height: 8rem; padding: .58rem .68rem; }
      .composer-context-row { gap: .3rem; padding-top: .32rem; }
      .composer-plugin-context { display: none; }
      #chat-form > button { padding: .42rem .58rem; font-size: .72rem; min-height: 2rem; }
      .voice-bar { margin-top: .2rem; min-height: 1rem; }
      .voice-settings { display: none; }
      #voice-state { font-size: .58rem; }
    }
    @media (max-width: 760px) and (max-height: 560px) {
      header h1 { font-size: .86rem; }
      .chat-sidebar.conversations-collapsed { min-height: 2rem; max-height: 2rem; }
      #messages { min-height: 3.5rem; }
      .voice-bar { display: none; }
    }
'''
    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.38 patch could not locate the final stylesheet")
    frontend = frontend[:style_close] + mobile_css + frontend[style_close:]

    frontend = replace_once(
        frontend,
        '  applyCollapsed(localStorage.getItem(storageKey) === "1");',
        '''  const savedCollapse = localStorage.getItem(storageKey);
  const phoneDefault = window.matchMedia("(max-width: 760px)").matches;
  applyCollapsed(savedCollapse === null ? phoneDefault : savedCollapse === "1");''',
        "phone conversation default",
    )

    backend = backend.replace('version="0.12.37"', 'version="0.12.38"')
    backend = backend.replace('"version": "0.12.37"', '"version": "0.12.38"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.37"', '"X-ZBRANO-Frontend-Version": "0.12.38"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.37"', '"name": "ZBRANO Developer Mode", "version": "0.12.38"')
    frontend = frontend.replace("HUD 0.12.37", "HUD 0.12.38")

    require(frontend, "compact phone layout", "mobile layout stylesheet")
    require(frontend, "overflow-x: auto", "single-row mobile navigation")
    require(frontend, ".voice-settings { display: none; }", "compact mobile voice row")
    require(frontend, ".chat-title-editor", "compact conversation title editor")
    require(frontend, "#automations-panel::before { display: none; }", "Automation panel label removal")
    require(frontend, "#autonomy-settings-form", "isolated authority form layout")
    require(frontend, ".autonomy-form-grid textarea", "bounded Automation form controls")
    require(frontend, 'window.matchMedia("(max-width: 760px)")', "collapsed phone default")
    require(frontend, "grid-template-columns: repeat(3, minmax(0, 1fr))", "compact composer action row")
    require(backend, 'version="0.12.38"', "backend version")
    require(frontend, "HUD 0.12.38", "HUD version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
