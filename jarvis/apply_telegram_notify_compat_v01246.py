import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.46 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.46 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    old_payload = '''    body = {
        "entity_id": request.target,
        "title": title,
        "message": request.message.strip(),
    }
'''
    new_payload = '''    message = request.message.strip()
    if channel["platform"] == "telegram":
        # Home Assistant's Telegram notify entity can return HTTP 500 when the
        # generic notify.send_message action includes its optional title key.
        # Preserve the visible heading while using the proven message-only shape.
        body = {
            "entity_id": request.target,
            "message": f"{title}\\n{message}" if title else message,
        }
    else:
        body = {
            "entity_id": request.target,
            "title": title,
            "message": message,
        }
'''
    backend = replace_once(backend, old_payload, new_payload, "Telegram-compatible notify payload")

    old_detail = '''            title=title, status="delivered", detail=f"Sent through {channel['platform']} via Home Assistant",
'''
    new_detail = '''            title=title, status="delivered",
            detail=(
                "Sent through telegram via Home Assistant using message-only compatibility"
                if channel["platform"] == "telegram"
                else f"Sent through {channel['platform']} via Home Assistant"
            ),
'''
    backend = replace_once(backend, old_detail, new_detail, "Telegram delivery evidence")

    backend = backend.replace('version="0.12.45"', 'version="0.12.46"')
    backend = backend.replace('"version": "0.12.45"', '"version": "0.12.46"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.45"', '"X-ZBRANO-Frontend-Version": "0.12.46"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.45"', '"name": "ZBRANO Developer Mode", "version": "0.12.46"')
    frontend = frontend.replace("HUD 0.12.45", "HUD 0.12.46")

    required_backend = (
        'version="0.12.46"',
        'if channel["platform"] == "telegram":',
        '"message": f"{title}\\n{message}" if title else message',
        "message-only compatibility",
    )
    required_frontend = ("HUD 0.12.46", "Notification Center", "Notification Watchlist")
    for marker in required_backend:
        require(backend, marker, marker)
    for marker in required_frontend:
        require(frontend, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
