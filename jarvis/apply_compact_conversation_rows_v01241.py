import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.41 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    css = r'''
    /* v0.12.41 one compact height for every conversation-row control. */
    .chat-list-item {
      min-height: 1.8rem;
      max-height: 1.8rem;
      align-items: center;
    }
    .chat-list-item .chat-open,
    .chat-list-item .chat-title-editor,
    .chat-list-item .chat-actions,
    .chat-list-item .chat-rename,
    .chat-list-item .chat-delete {
      box-sizing: border-box !important;
      height: 1.8rem !important;
      min-height: 1.8rem !important;
      max-height: 1.8rem !important;
      align-self: center;
    }
    .chat-list-item .chat-open {
      display: flex;
      align-items: center;
      padding: 0 .55rem !important;
      line-height: normal;
    }
    .chat-list-item .chat-actions { display: inline-flex; align-items: center; }
    @media (max-width: 760px) {
      .chat-list-item { min-height: 1.65rem; max-height: 1.65rem; }
      .chat-list-item .chat-open,
      .chat-list-item .chat-title-editor,
      .chat-list-item .chat-actions,
      .chat-list-item .chat-rename,
      .chat-list-item .chat-delete {
        height: 1.65rem !important;
        min-height: 1.65rem !important;
        max-height: 1.65rem !important;
      }
    }
'''
    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.41 patch could not locate the final stylesheet")
    frontend = frontend[:style_close] + css + frontend[style_close:]

    backend = backend.replace('version="0.12.40"', 'version="0.12.41"')
    backend = backend.replace('"version": "0.12.40"', '"version": "0.12.41"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.40"', '"X-ZBRANO-Frontend-Version": "0.12.41"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.40"', '"name": "ZBRANO Developer Mode", "version": "0.12.41"')
    frontend = frontend.replace("HUD 0.12.40", "HUD 0.12.41")

    require(frontend, ".chat-list-item .chat-open", "conversation name control")
    require(frontend, ".chat-list-item .chat-actions", "conversation action group")
    require(frontend, "max-height: 1.8rem !important", "desktop compact height")
    require(frontend, "max-height: 1.65rem !important", "phone compact height")
    require(backend, 'version="0.12.41"', "backend version")
    require(frontend, "HUD 0.12.41", "HUD version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
