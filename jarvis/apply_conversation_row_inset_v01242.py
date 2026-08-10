import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.42 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    css = r'''
    /* v0.12.42 inset compact controls inside the active conversation frame. */
    .chat-list-item {
      box-sizing: border-box;
      min-height: 2rem;
      max-height: 2rem;
      padding: 2px;
      overflow: hidden;
    }
    .chat-list-item .chat-open,
    .chat-list-item .chat-title-editor,
    .chat-list-item .chat-actions,
    .chat-list-item .chat-rename,
    .chat-list-item .chat-delete {
      height: 1.7rem !important;
      min-height: 1.7rem !important;
      max-height: 1.7rem !important;
    }
    .chat-list-item .chat-open,
    .chat-list-item .chat-title-editor {
      font-size: .78rem;
      font-weight: 550;
    }
    @media (max-width: 760px) {
      .chat-list-item { min-height: 1.85rem; max-height: 1.85rem; }
      .chat-list-item .chat-open,
      .chat-list-item .chat-title-editor,
      .chat-list-item .chat-actions,
      .chat-list-item .chat-rename,
      .chat-list-item .chat-delete {
        height: 1.55rem !important;
        min-height: 1.55rem !important;
        max-height: 1.55rem !important;
      }
      .chat-list-item .chat-open,
      .chat-list-item .chat-title-editor { font-size: .72rem; }
    }
'''
    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.42 patch could not locate the final stylesheet")
    frontend = frontend[:style_close] + css + frontend[style_close:]

    backend = backend.replace('version="0.12.41"', 'version="0.12.42"')
    backend = backend.replace('"version": "0.12.41"', '"version": "0.12.42"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.41"', '"X-ZBRANO-Frontend-Version": "0.12.42"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.41"', '"name": "ZBRANO Developer Mode", "version": "0.12.42"')
    frontend = frontend.replace("HUD 0.12.41", "HUD 0.12.42")

    require(frontend, "padding: 2px", "conversation frame inset")
    require(frontend, "height: 1.7rem !important", "inset desktop controls")
    require(frontend, "height: 1.55rem !important", "inset phone controls")
    require(frontend, "font-size: .78rem", "smaller conversation name")
    require(backend, 'version="0.12.42"', "backend version")
    require(frontend, "HUD 0.12.42", "HUD version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
