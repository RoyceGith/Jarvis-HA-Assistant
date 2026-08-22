import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.52 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    start = backend.find("async def _create_notification_watch(")
    end = backend.find("\ndef _watch_time_active(", start)
    if start < 0 or end < 0:
        raise RuntimeError("ZBRANO v0.12.52 could not locate notification watch creation")

    replacement = '''def _notification_watch_key(watch: dict[str, Any]) -> tuple[str, str, str, str, str, bool]:
    return (
        str(watch.get("trigger_entity") or "").strip().lower(),
        str(watch.get("trigger_state") or "").strip().lower(),
        str(watch.get("destination") or "").strip().lower(),
        str(watch.get("active_start") or ""),
        str(watch.get("active_end") or ""),
        bool(watch.get("one_shot")),
    )


async def _create_notification_watch(request: NotificationWatchRequest, source: str = "interface") -> dict[str, Any]:
    import secrets

    data = automation_store()
    entity_id = request.entity_id.strip().lower()
    try:
        entity = await ha_ws.get_state(entity_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not entity:
        raise HTTPException(status_code=404, detail=f"Home Assistant entity not found: {entity_id}")
    channels = await notification_channels()
    destination = request.destination.strip().lower() or str(notification_store()["settings"].get("default_channel") or "")
    if not any(item["entity_id"] == destination for item in channels):
        raise HTTPException(status_code=400, detail="Notification destination is unavailable")

    now = time.time()
    payload = _notification_watch_payload(request)
    key = _notification_watch_key(payload)
    matches = [item for item in notification_watches(data) if _notification_watch_key(item) == key]
    if matches:
        watch = matches[0]
        runtime = {
            "id": watch.get("id") or secrets.token_hex(12),
            "created_at": float(watch.get("created_at") or now),
            "last_observed_state": watch.get("last_observed_state"),
            "last_triggered_at": float(watch.get("last_triggered_at") or 0.0),
            "trigger_count": int(watch.get("trigger_count") or 0),
        }
        watch.update(payload)
        watch.update(runtime)
        watch["updated_at"] = now
        watch["source"] = source
        data["automations"] = [
            item for item in data.get("automations", [])
            if item.get("kind") != "notification_watch" or _notification_watch_key(item) != key
        ]
        data["automations"].insert(0, watch)
        _automation_event(
            data, "notification_watch", f"Notification watch refreshed: {watch['name']}",
            f"Moved to first position; retained one rule and removed {max(0, len(matches) - 1)} older duplicate(s).",
        )
        _automation_save(data)
        return {"created": False, "deduplicated": len(matches), "watch": watch}

    if len(data["automations"]) >= 100:
        raise HTTPException(status_code=400, detail="Automation limit reached (100)")
    watch = {
        "id": secrets.token_hex(12),
        "created_at": now,
        "updated_at": now,
        "source": source,
        **payload,
    }
    data["automations"].insert(0, watch)
    _automation_event(data, "notification_watch", f"Notification watch armed: {watch['name']}", watch["objective"])
    _automation_save(data)
    return {"created": True, "deduplicated": 0, "watch": watch}

'''
    backend = backend[:start] + replacement + backend[end + 1:]

    backend = backend.replace('version="0.12.51"', 'version="0.12.52"')
    backend = backend.replace('"version": "0.12.51"', '"version": "0.12.52"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.51"', '"X-ZBRANO-Frontend-Version": "0.12.52"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.51"', '"name": "ZBRANO Developer Mode", "version": "0.12.52"')
    frontend = frontend.replace("HUD 0.12.51", "HUD 0.12.52")

    for marker in (
        'version="0.12.52"',
        "def _notification_watch_key(",
        "if matches:",
        'data["automations"].insert(0, watch)',
        '"deduplicated": len(matches)',
        '"last_triggered_at"',
        '"trigger_count"',
        'service_domain = "telegram_bot" if channel["platform"] == "telegram" else "notify"',
    ):
        require(backend, marker, marker)
    require(frontend, "HUD 0.12.52", "HUD 0.12.52")

    creation_block = backend.split("async def _create_notification_watch(", 1)[1].split("\ndef _watch_time_active(", 1)[0]
    if creation_block.count('data["automations"].insert(0, watch)') != 2:
        raise RuntimeError("ZBRANO v0.12.52 does not prioritize both refreshed and new watches")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
