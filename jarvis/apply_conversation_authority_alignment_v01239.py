import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.39 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    css = r'''
    /* v0.12.39 exact conversation editor and authority-list alignment. */
    .chat-list-item .chat-title-editor {
      box-sizing: border-box !important;
      height: 1.8rem !important;
      min-height: 1.8rem !important;
      max-height: 1.8rem !important;
      padding: 0 .45rem !important;
      line-height: normal !important;
      align-self: center;
    }
    #autonomy-settings-form .autonomy-form-grid .check {
      grid-column: 1 / -1;
      width: 100%;
      min-width: 0;
      display: flex;
      align-items: center;
      gap: .5rem;
      margin: 0;
      padding: .2rem 0;
    }
    #autonomy-settings-form .autonomy-form-grid .check input[type="checkbox"] {
      width: auto;
      min-width: auto;
      flex: 0 0 auto;
      margin: 0;
    }
    @media (max-width: 760px) {
      .chat-list-item .chat-title-editor {
        height: 1.65rem !important;
        min-height: 1.65rem !important;
        max-height: 1.65rem !important;
      }
    }
'''
    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.39 patch could not locate the final stylesheet")
    frontend = frontend[:style_close] + css + frontend[style_close:]

    backend = backend.replace('version="0.12.38"', 'version="0.12.39"')
    backend = backend.replace('"version": "0.12.38"', '"version": "0.12.39"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.38"', '"X-ZBRANO-Frontend-Version": "0.12.39"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.38"', '"name": "ZBRANO Developer Mode", "version": "0.12.39"')
    frontend = frontend.replace("HUD 0.12.38", "HUD 0.12.39")

    require(frontend, ".chat-list-item .chat-title-editor", "exact conversation editor selector")
    require(frontend, "max-height: 1.8rem !important", "desktop editor height")
    require(frontend, "max-height: 1.65rem !important", "phone editor height")
    require(frontend, "#autonomy-settings-form .autonomy-form-grid .check", "authority checkbox rows")
    require(frontend, "grid-column: 1 / -1", "full-width authority rows")
    require(backend, 'version="0.12.39"', "backend version")
    require(frontend, "HUD 0.12.39", "HUD version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
