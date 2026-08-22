import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.50 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.50 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        '        await ha_ws.call_service("notify", "send_message", body)\n',
        '''        service_domain = "telegram_bot" if channel["platform"] == "telegram" else "notify"
        await ha_ws.call_service(service_domain, "send_message", body)
''',
        "platform-aware notification service routing",
    )

    backend = backend.replace('version="0.12.49"', 'version="0.12.50"')
    backend = backend.replace('"version": "0.12.49"', '"version": "0.12.50"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.49"', '"X-ZBRANO-Frontend-Version": "0.12.50"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.49"', '"name": "ZBRANO Developer Mode", "version": "0.12.50"')
    frontend = frontend.replace("HUD 0.12.49", "HUD 0.12.50")

    for marker in (
        'version="0.12.50"',
        'service_domain = "telegram_bot" if channel["platform"] == "telegram" else "notify"',
        'await ha_ws.call_service(service_domain, "send_message", body)',
        '"parse_mode": "plain_text"',
    ):
        require(backend, marker, marker)
    require(frontend, "HUD 0.12.50", "HUD 0.12.50")

    notification_function = backend.split('async def test_notification_channel(', 1)[1].split('\n\n@app.get("/api/settings")', 1)[0]
    if 'ha_ws.call_service("notify", "send_message", body)' in notification_function:
        raise RuntimeError("ZBRANO v0.12.50 still hard-codes the generic notify action")
    if 'HA_API_BASE}/services/notify/send_message' in notification_function:
        raise RuntimeError("ZBRANO v0.12.50 regressed to REST notification delivery")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
