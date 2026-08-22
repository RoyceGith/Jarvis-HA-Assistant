import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.75 compact header expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    frontend = replace_once(
        frontend,
        '''    <div>
      <h1>ZBRANO</h1>
      <div class="status">Workshop Intelligence Interface · HUD 0.12.74</div>
    </div>''',
        '''    <div class="brand-line">
      <h1>ZBRANO</h1>
      <div class="status hud-version-label">Workshop Intelligence Interface · HUD 0.12.75</div>
    </div>''',
        "brand and HUD line",
    )

    frontend = replace_once(
        frontend,
        '''        <form id="chat-form">
          <div class="composer-input-stack">
          <textarea id="message" rows="1" autocomplete="off" placeholder="Enter command…" aria-label="Message ZBRANO" required></textarea>
            <div class="composer-context-row" aria-label="Message tools">
              <label class="composer-web-control" for="web-search-mode"><span aria-hidden="true">◎</span><span>Web</span><select id="web-search-mode" title="Choose how this message may use the public web"><option value="auto">Auto</option><option value="search">On</option><option value="off">Off</option></select></label>
              <div class="composer-plugin-context"><span class="composer-context-label">Plugins</span><div id="composer-plugin-icons" class="composer-plugin-icons" role="list" aria-label="Enabled plugins"><span class="composer-plugin-empty">Loading…</span></div></div>
            </div>
          </div>
          <button id="mic-button"''',
        '''        <form id="chat-form">
          <textarea id="message" rows="1" autocomplete="off" placeholder="Enter command…" aria-label="Message ZBRANO" required></textarea>
          <button id="mic-button"''',
        "single-row prompt controls",
    )
    frontend = replace_once(
        frontend,
        '''        <div class="voice-bar">
          <span id="voice-state" role="status" aria-live="polite">VOICE READY</span>
          <span class="voice-settings">''',
        '''        <div class="voice-bar">
          <span id="voice-state" role="status" aria-live="polite" hidden>VOICE READY</span>
          <div class="composer-context-row" aria-label="Message tools">
            <label class="composer-web-control" for="web-search-mode"><span aria-hidden="true">◎</span><span>Web</span><select id="web-search-mode" title="Choose how this message may use the public web"><option value="auto">Auto</option><option value="search">On</option><option value="off">Off</option></select></label>
            <div class="composer-plugin-context"><span class="composer-context-label">Plugins</span><div id="composer-plugin-icons" class="composer-plugin-icons" role="list" aria-label="Enabled plugins"><span class="composer-plugin-empty">Loading…</span></div></div>
          </div>
          <span class="voice-settings">''',
        "Web and Plugins in the voice settings row",
    )

    css = r'''
    /* v0.12.75 compact application header and primary navigation. */
    header { align-items:center; gap:.7rem; }
    .brand-line { display:flex; align-items:baseline; gap:.75rem; min-width:0; }
    .brand-line h1 { flex:0 0 auto; margin:0; font-size:1.42rem; line-height:1.15; }
    .hud-version-label { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:.75rem; }
    .runtime-status-stack {
      display:flex; flex-direction:row; flex-wrap:wrap; align-items:center;
      justify-content:flex-end; gap:.36rem;
    }
    .runtime-status-stack #health { padding:.28rem .55rem; font-size:.7rem; white-space:nowrap; }
    .runtime-status-stack .developer-mode-indicator { padding:.22rem .48rem; font-size:.62rem; }
    .runtime-status-stack .calendar-quick-open { width:1.8rem; min-width:1.8rem; height:1.8rem; }
    .runtime-status-stack .grinder-connection-indicator { min-height:1.35rem; padding:.16rem .48rem; font-size:.64rem; }
    nav { gap:.34rem; margin:.4rem 0; }
    nav button { min-height:2rem; padding:.36rem .6rem; font-size:.76rem; line-height:1.1; }
    nav .primary-icon-tab { width:2rem; min-width:2rem; height:2rem; padding:.34rem; }
    nav .primary-icon-tab svg { width:1rem; height:1rem; }
    #chat-form {
      display:grid; grid-template-columns:minmax(0,1fr) auto auto auto;
      align-items:stretch; gap:.38rem;
    }
    #chat-form > #message { box-sizing:border-box; width:100%; min-width:0; align-self:stretch; }
    #chat-form > button { align-self:stretch; min-height:2.45rem; }
    #voice-state { display:none !important; }
    .voice-bar { display:flex; align-items:center; flex-wrap:wrap; gap:.38rem .65rem; }
    .voice-bar .composer-context-row {
      display:inline-flex; flex:0 1 auto; align-items:center; flex-wrap:nowrap;
      min-height:0; margin:0; padding:0 .65rem 0 0; gap:.45rem;
      border-right:1px solid var(--line);
    }
    .voice-bar .composer-web-control { padding-right:.55rem; }
    .voice-bar .composer-plugin-context { flex:0 1 auto; }
    .voice-bar .voice-settings { display:flex; flex:1 1 auto; align-items:center; flex-wrap:wrap; gap:.35rem .6rem; }
    @media(max-width:760px) {
      header { align-items:flex-start; }
      .brand-line { align-items:center; }
      .brand-line h1 { font-size:1.18rem; }
      .runtime-status-stack { gap:.25rem; }
      nav button { min-height:1.95rem; padding:.34rem .52rem; font-size:.71rem; }
      nav .primary-icon-tab { width:1.95rem; min-width:1.95rem; height:1.95rem; }
      #chat-form { grid-template-columns:minmax(0,1fr) auto auto auto; gap:.28rem; }
      #chat-form > button { min-height:2.25rem; padding:.38rem .5rem; font-size:.7rem; }
      .voice-bar .composer-context-row { border-right:0; padding-right:0; }
    }
    @media(max-width:520px) {
      header { gap:.4rem; }
      .hud-version-label { display:none; }
      .runtime-status-stack { margin-left:auto; }
      .runtime-status-stack .grinder-connection-indicator { font-size:.58rem; }
      nav { gap:.25rem; }
      nav button { padding:.32rem .45rem; font-size:.68rem; }
      #developer-tab::before { margin-right:.24rem; }
      #chat-form > button { padding:.34rem .4rem; }
      .voice-bar .composer-plugin-context { display:inline-flex; }
      .voice-bar .composer-context-label { display:none; }
    }
'''
    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.75 compact header could not locate the stylesheet close")
    frontend = frontend[:style_close] + css + frontend[style_close:]

    backend = backend.replace('version="0.12.74"', 'version="0.12.75"')
    backend = backend.replace('"version": "0.12.74"', '"version": "0.12.75"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.74"', '"X-ZBRANO-Frontend-Version": "0.12.75"')
    backend = backend.replace(
        '"name": "ZBRANO Developer Mode", "version": "0.12.74"',
        '"name": "ZBRANO Developer Mode", "version": "0.12.75"',
    )

    required_frontend = (
        "HUD 0.12.75",
        'class="brand-line"',
        'class="status hud-version-label"',
        ".runtime-status-stack {",
        "display:flex; flex-direction:row; flex-wrap:wrap; align-items:center;",
        "nav button { min-height:2rem;",
        'id="voice-state" role="status" aria-live="polite" hidden',
        '.voice-bar .composer-context-row',
        "grid-template-columns:minmax(0,1fr) auto auto auto",
    )
    missing = [marker for marker in required_frontend if marker not in frontend]
    if missing or 'version="0.12.75"' not in backend:
        raise RuntimeError("ZBRANO v0.12.75 compact header verification failed: " + ", ".join(missing))

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
