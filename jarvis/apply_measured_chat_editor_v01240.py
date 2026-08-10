import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.40 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.40 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    frontend = replace_once(
        frontend,
        "beginChatRename(row, openButton, chat);",
        "beginChatRename(row, openButton, chat, renameButton, deleteButton);",
        "rename action controls",
    )
    frontend = replace_once(
        frontend,
        "function beginChatRename(row, openButton, chat) {",
        "function beginChatRename(row, openButton, chat, renameButton, deleteButton) {",
        "rename function controls",
    )
    frontend = replace_once(
        frontend,
        '''  openButton.replaceWith(editor);
  editor.focus();
  editor.select();''',
        '''  openButton.replaceWith(editor);
  const actionHeight = Math.max(
    renameButton?.getBoundingClientRect().height || 0,
    deleteButton?.getBoundingClientRect().height || 0,
  );
  if (actionHeight > 0) {
    const measuredHeight = `${actionHeight}px`;
    editor.style.setProperty("height", measuredHeight, "important");
    editor.style.setProperty("min-height", measuredHeight, "important");
    editor.style.setProperty("max-height", measuredHeight, "important");
  }
  editor.focus();
  editor.select();''',
        "measured rename editor height",
    )

    backend = backend.replace('version="0.12.39"', 'version="0.12.40"')
    backend = backend.replace('"version": "0.12.39"', '"version": "0.12.40"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.39"', '"X-ZBRANO-Frontend-Version": "0.12.40"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.39"', '"name": "ZBRANO Developer Mode", "version": "0.12.40"')
    frontend = frontend.replace("HUD 0.12.39", "HUD 0.12.40")

    require(frontend, "renameButton?.getBoundingClientRect().height", "measured Edit height")
    require(frontend, "deleteButton?.getBoundingClientRect().height", "measured Delete height")
    require(frontend, 'editor.style.setProperty("height", measuredHeight, "important")', "inline exact height")
    require(backend, 'version="0.12.40"', "backend version")
    require(frontend, "HUD 0.12.40", "HUD version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
