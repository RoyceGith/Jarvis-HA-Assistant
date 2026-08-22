from pathlib import Path

ROOT = Path('/opt/jarvis')
MAIN = ROOT / 'app/main.py'
INDEX = ROOT / 'app/static/index.html'


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f'Jarvis v0.11.16 patch missing: {label}')


def patch_main() -> None:
    text = MAIN.read_text(encoding='utf-8')
    start = text.index('@app.get("/api/ha/entities")')
    end = text.index('\n\n@app.', start + 10)
    old = text[start:end]
    require(old, 'response = await client.get(f"{HA_API_BASE}/states", headers=headers)', 'REST-only entity inventory')
    new = '''@app.get("/api/ha/entities")
async def list_ha_entities() -> dict[str, Any]:
    """Return normalized Home Assistant entity inventory with WS-first discovery."""
    if not SUPERVISOR_TOKEN:
        raise HTTPException(status_code=503, detail="Home Assistant API token unavailable")

    raw_states: list[dict[str, Any]] = []
    inventory_source = "none"
    diagnostics: dict[str, Any] = {
        "websocket_connected": ha_ws.connected,
        "websocket_cached_entities": len(ha_ws.state_cache),
        "websocket_error": ha_ws.last_error,
        "rest_error": None,
    }

    try:
        if not ha_ws.connected:
            await ha_ws.connect()
        if ha_ws.state_cache:
            raw_states = list(ha_ws.state_cache.values())
            inventory_source = "websocket"
    except Exception as exc:
        diagnostics["websocket_error"] = str(exc)

    if not raw_states:
        headers = {
            "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(f"{HA_API_BASE}/states", headers=headers)
            if response.is_error:
                diagnostics["rest_error"] = f"HTTP {response.status_code}"
            else:
                payload = response.json()
                if isinstance(payload, list):
                    raw_states = [item for item in payload if isinstance(item, dict)]
                    inventory_source = "rest"
                else:
                    diagnostics["rest_error"] = "Home Assistant states response was not a list"
        except Exception as exc:
            diagnostics["rest_error"] = str(exc)

    if not raw_states:
        detail = "Home Assistant returned no entity inventory"
        errors = [
            value for value in (diagnostics.get("websocket_error"), diagnostics.get("rest_error"))
            if value
        ]
        if errors:
            detail += ": " + " | ".join(errors)
        raise HTTPException(status_code=502, detail=detail)

    entities: list[dict[str, Any]] = []
    for item in raw_states:
        entity_id = item.get("entity_id", "")
        if "." not in entity_id:
            continue
        domain = entity_id.split(".", 1)[0]
        attributes = item.get("attributes") or {}
        state = item.get("state")
        device_class = attributes.get("device_class")
        friendly_name = attributes.get("friendly_name") or entity_id
        risk = classify_entity_risk(
            domain,
            device_class,
            entity_id=entity_id,
            friendly_name=friendly_name,
        )
        entities.append({
            "entity_id": entity_id,
            "friendly_name": friendly_name,
            "domain": domain,
            "state": state,
            "available": state not in {"unavailable", "unknown", None},
            "device_class": device_class,
            "unit": attributes.get("unit_of_measurement"),
            "icon": attributes.get("icon"),
            "risk": risk,
            "auto_approved": risk == "low_risk_control_proposed",
            "last_changed": item.get("last_changed"),
            "last_updated": item.get("last_updated"),
        })

    policy = load_entity_policy()
    policy_changed = False
    for entity in entities:
        if not entity["auto_approved"]:
            continue
        existing = policy.get(entity["entity_id"], {})
        updated = {
            **existing,
            "enabled": True,
            "friendly_name": entity["friendly_name"],
            "domain": entity["domain"],
            "device_class": entity["device_class"],
            "unit": entity["unit"],
            "access": "low_risk_control_proposed",
            "aliases": existing.get("aliases", []),
            "auto_approved": True,
        }
        if existing != updated:
            policy[entity["entity_id"]] = updated
            policy_changed = True
    if policy_changed:
        save_entity_policy(policy)

    entities.sort(key=lambda entity: (
        str(entity.get("domain", "")).lower(),
        str(entity.get("friendly_name", "")).lower(),
        str(entity.get("entity_id", "")).lower(),
    ))
    domains = sorted({entity["domain"] for entity in entities})
    diagnostics["websocket_connected"] = ha_ws.connected
    diagnostics["websocket_cached_entities"] = len(ha_ws.state_cache)
    diagnostics["websocket_error"] = ha_ws.last_error or diagnostics.get("websocket_error")
    return {
        "count": len(entities),
        "domains": domains,
        "entities": entities,
        "source": inventory_source,
        "diagnostics": diagnostics,
        "note": "States are live Home Assistant data. Only stable metadata should later be proposed for Workshop Memory.",
    }'''
    text = text[:start] + new + text[end:]
    text = text.replace('version="0.11.15"', 'version="0.11.16"')
    text = text.replace('"version": "0.11.15"', '"version": "0.11.16"')
    MAIN.write_text(text, encoding='utf-8')


def patch_index() -> None:
    text = INDEX.read_text(encoding='utf-8')
    require(text, '.jarvis::before { content: "JARVIS";', 'chat assistant label')
    text = text.replace('.jarvis::before { content: "JARVIS";', '.jarvis::before { content: "ZBRANO";', 1)
    require(text, 'HUD 0.11.15', 'HUD version')
    text = text.replace('HUD 0.11.15', 'HUD 0.11.16')

    old = '''    entityInventory = data.entities || [];

    const approvedResponse = await fetch("api/ha/approved");'''
    new = '''    entityInventory = data.entities || [];
    if (!entityInventory.length) {
      throw new Error("Home Assistant returned an empty entity inventory");
    }
    const inventorySource = data.source ? ` · source: ${data.source}` : "";

    const approvedResponse = await fetch("api/ha/approved");'''
    require(text, old, 'entity load assignment')
    text = text.replace(old, new, 1)

    old2 = '''    renderEntities();
  } catch (error) {'''
    new2 = '''    renderEntities();
    entitySummary.textContent += inventorySource;
  } catch (error) {'''
    require(text, old2, 'entity load completion')
    text = text.replace(old2, new2, 1)
    INDEX.write_text(text, encoding='utf-8')


def verify() -> None:
    main = MAIN.read_text(encoding='utf-8')
    index = INDEX.read_text(encoding='utf-8')
    required = (
        'version="0.11.16"',
        'inventory_source = "websocket"',
        'inventory_source = "rest"',
        '"diagnostics": diagnostics',
        'content: "ZBRANO"',
        'HUD 0.11.16',
        'source: ${data.source}',
    )
    missing = [marker for marker in required if marker not in main and marker not in index]
    if missing:
        raise RuntimeError('Jarvis v0.11.16 verification failed: ' + ', '.join(missing))


if __name__ == '__main__':
    patch_main()
    patch_index()
    verify()
