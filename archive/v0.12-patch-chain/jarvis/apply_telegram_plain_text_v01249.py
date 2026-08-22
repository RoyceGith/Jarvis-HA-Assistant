import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.49 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.49 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    old = '''        body = {
            "entity_id": request.target,
            "message": message,
        }
'''
    new = '''        body = {
            "entity_id": request.target,
            "message": message,
            # Generated notification text must not be interpreted as Markdown.
            # This prevents Telegram "Can't parse entities" failures.
            "parse_mode": "plain_text",
        }
'''
    backend = replace_once(backend, old, new, "Telegram plain-text payload")

    backend = backend.replace('version="0.12.48"', 'version="0.12.49"')
    backend = backend.replace('"version": "0.12.48"', '"version": "0.12.49"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.48"', '"X-ZBRANO-Frontend-Version": "0.12.49"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.48"', '"name": "ZBRANO Developer Mode", "version": "0.12.49"')
    frontend = frontend.replace("HUD 0.12.48", "HUD 0.12.49")

    for marker in (
        'version="0.12.49"',
        '"parse_mode": "plain_text"',
        'await ha_ws.call_service("notify", "send_message", body)',
    ):
        require(backend, marker, marker)
    require(frontend, "HUD 0.12.49", "HUD 0.12.49")

    telegram_branch = backend.split('if channel["platform"] == "telegram":', 1)[1].split("    else:", 1)[0]
    if telegram_branch.count('"parse_mode": "plain_text"') != 1:
        raise RuntimeError("ZBRANO v0.12.49 Telegram branch does not contain exactly one plain-text override")
    non_telegram_branch = backend.split("    else:", 1)[1].split("    try:", 1)[0]
    if '"parse_mode"' in non_telegram_branch:
        raise RuntimeError("ZBRANO v0.12.49 changed parse mode for non-Telegram channels")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
