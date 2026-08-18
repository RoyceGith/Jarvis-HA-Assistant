import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.73 navigation expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    old_nav = '''  <nav aria-label="Primary navigation">
    <button id="chat-tab" class="active">Chat</button>
    <button id="files-tab">Shared Files</button>
    <button id="plugins-tab">Plugins</button>
    <button id="entities-tab">Entities</button>
    <button id="calendar-tab">Calendar</button>
    <button id="automations-tab">Automations</button>
    <button id="settings-tab">Settings</button>
    <button id="developer-tab">Developer</button>
  </nav>'''
    new_nav = '''  <nav aria-label="Primary navigation">
    <button id="chat-tab" class="active">Chat</button>
    <button id="files-tab">Shared Files</button>
    <button id="automations-tab">Automations</button>
    <button id="entities-tab">Entities</button>
    <button id="plugins-tab">Plugins</button>
    <button id="calendar-tab" class="primary-icon-tab" aria-label="Calendar" title="Calendar"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 2v3M17 2v3M3.5 9h17M5.5 4h13a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z"/><path d="M8 13h3v3H8z"/></svg></button>
    <button id="settings-tab" class="primary-icon-tab" aria-label="Settings" title="Settings"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 15.4a3.4 3.4 0 1 0 0-6.8 3.4 3.4 0 0 0 0 6.8Z"/><path d="m19.4 15 .1.1 1.4 2.4-2.4 2.4-2.4-1.4-.1-.1a8.4 8.4 0 0 1-2 .8V22H9.6v-2.8a8.4 8.4 0 0 1-2-.8l-.1.1-2.4 1.4-2.4-2.4 1.4-2.4.1-.1a8.4 8.4 0 0 1-.8-2H.6V9.6h2.8a8.4 8.4 0 0 1 .8-2l-.1-.1-1.4-2.4 2.4-2.4 2.4 1.4.1.1a8.4 8.4 0 0 1 2-.8V.6H13v2.8a8.4 8.4 0 0 1 2 .8l.1-.1 2.4-1.4 2.4 2.4-1.4 2.4-.1.1a8.4 8.4 0 0 1 .8 2H22V13h-2.8a8.4 8.4 0 0 1-.8 2Z"/></svg></button>
    <button id="developer-tab">Developer</button>
  </nav>'''
    frontend = replace_once(frontend, old_nav, new_nav, "primary navigation order and icons")

    css = r'''
    /* v0.12.73 primary navigation order and icons. */
    nav .primary-icon-tab { display:inline-grid; place-items:center; width:2.35rem; min-width:2.35rem; height:2.25rem; padding:.42rem; }
    nav .primary-icon-tab svg { width:1.08rem; height:1.08rem; fill:none; stroke:currentColor; stroke-width:1.7; stroke-linecap:round; stroke-linejoin:round; pointer-events:none; }
    @media(max-width:620px) {
      nav .primary-icon-tab { width:2.15rem; min-width:2.15rem; height:2.05rem; padding:.36rem; }
    }
'''
    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.73 navigation could not locate the stylesheet close")
    frontend = frontend[:style_close] + css + frontend[style_close:]

    backend_markers = ('version="0.12.73"', '"X-ZBRANO-Frontend-Version": "0.12.73"')
    frontend_markers = (
        "HUD 0.12.73",
        '<button id="files-tab">Shared Files</button>\n    <button id="automations-tab">Automations</button>\n    <button id="entities-tab">Entities</button>\n    <button id="plugins-tab">Plugins</button>',
        'id="calendar-tab" class="primary-icon-tab" aria-label="Calendar"',
        'id="settings-tab" class="primary-icon-tab" aria-label="Settings"',
        "nav .primary-icon-tab svg",
    )
    missing = [marker for marker in backend_markers if marker not in backend]
    missing += [marker for marker in frontend_markers if marker not in frontend]
    if missing:
        raise RuntimeError("ZBRANO v0.12.73 navigation verification failed: " + ", ".join(missing))

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
