import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.93 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.93 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        '''@app.get("/api/ha/live-events")
async def api_home_assistant_live_events(limit: int = 100) -> dict[str, Any]:
    bounded = max(1, min(300, int(limit or 100)))
    events = [dict(item) for item in list(HA_LIVE_EVENTS)[:bounded]]
    return {"read_only": True, "events": events, "count": len(events), "connected": ha_ws.connected}''',
        '''@app.get("/api/ha/live-events")
async def api_home_assistant_live_events(limit: int = 100) -> dict[str, Any]:
    """Return approved live changes plus current-state evidence for reliable History startup."""
    bounded = max(1, min(300, int(limit or 100)))
    journal = [
        dict(item) for item in HA_LIVE_EVENTS
        if effective_entity_access(str(item.get("entity_id") or ""))
    ]
    evidence = list(journal)
    journal_entities = {str(item.get("entity_id") or "") for item in journal}
    for entity_id, state in ha_ws.state_cache.items():
        clean_id = str(entity_id or "").lower()
        if not clean_id or clean_id in journal_entities or not effective_entity_access(clean_id):
            continue
        attributes = state.get("attributes") if isinstance(state.get("attributes"), dict) else {}
        current = str(state.get("state") or "")
        evidence.append({
            "when": str(state.get("last_updated") or state.get("last_changed") or ""),
            "entity_id": clean_id,
            "name": str(attributes.get("friendly_name") or clean_id),
            "old_state": None,
            "state": current,
            "message": f"current state is {current or 'unknown'}",
            "source": "current",
            "context_id": str((state.get("context") or {}).get("id") or ""),
        })
    evidence.sort(key=lambda item: str(item.get("when") or ""), reverse=True)
    events = evidence[:bounded]
    return {
        "read_only": True,
        "events": events,
        "count": len(events),
        "journal_count": len(journal),
        "current_state_count": max(0, len(events) - min(len(journal), len(events))),
        "connected": ha_ws.connected,
    }''',
        "live History evidence endpoint",
    )

    backend = replace_once(
        backend,
        '''async def ha_set_power(entity_id: str, turn_on: bool) -> dict[str, Any]:''',
        '''def _ha_power_state_matches(domain: str, state: Any, turn_on: bool) -> bool:
    value = str(state or "").strip().lower()
    if not turn_on:
        return value == "off"
    if domain == "climate":
        return value not in {"", "off", "unknown", "unavailable"}
    return value == "on"


async def _wait_for_ha_power_state(
    entity_id: str,
    domain: str,
    turn_on: bool,
    timeout: float = 5.0,
) -> dict[str, Any] | None:
    deadline = asyncio.get_running_loop().time() + timeout
    latest: dict[str, Any] | None = None
    while asyncio.get_running_loop().time() < deadline:
        latest = ha_ws.state_cache.get(entity_id)
        if latest and _ha_power_state_matches(domain, latest.get("state"), turn_on):
            return latest
        await asyncio.sleep(0.05)
    return latest


async def ha_set_power(entity_id: str, turn_on: bool) -> dict[str, Any]:''',
        "domain-aware power verifier",
    )
    backend = replace_once(
        backend,
        '''        verified_raw = await ha_ws.wait_for_state(entity_id, expected, timeout=5.0)''',
        '''        verified_raw = await _wait_for_ha_power_state(entity_id, domain, turn_on, timeout=5.0)''',
        "power-state wait",
    )
    backend = replace_once(
        backend,
        '''        "success": verified.get("state") == expected,''',
        '''        "success": _ha_power_state_matches(domain, verified.get("state"), turn_on),''',
        "power success result",
    )

    frontend = replace_once(
        frontend,
        "journal ${Number(live.count||0)}",
        "evidence ${Number(live.count||0)} · live changes ${Number(live.journal_count||0)}",
        "History evidence status",
    )
    backend = backend.replace('version="0.12.92"', 'version="0.12.93"')
    backend = backend.replace('"version": "0.12.92"', '"version": "0.12.93"')
    frontend = frontend.replace("HUD 0.12.92", "HUD 0.12.93")

    for marker, location in [
        ('version="0.12.93"', backend),
        ('def _ha_power_state_matches(', backend),
        ('domain == "climate"', backend),
        ('"source": "current"', backend),
        ('"journal_count": len(journal)', backend),
        ('live changes ${Number(live.journal_count||0)}', frontend),
        ('HUD 0.12.93', frontend),
    ]:
        require(location, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
