from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import httpx


HA_API_BASE = "http://supervisor/core/api"
SUPERVISOR_TOKEN = ""
_ha_client: Any = None
_ensure_read_allowed: Callable[[str], None] = lambda entity_id: None
_ensure_control_allowed: Callable[[str], str] = lambda entity_id: entity_id.split(".", 1)[0]


def configure_ha_control_service(
    *,
    ha_client: Any,
    supervisor_token: str,
    ha_api_base: str,
    ensure_read_allowed_fn: Callable[[str], None],
    ensure_control_allowed_fn: Callable[[str], str],
) -> None:
    global _ha_client, SUPERVISOR_TOKEN, HA_API_BASE
    global _ensure_read_allowed, _ensure_control_allowed
    _ha_client = ha_client
    SUPERVISOR_TOKEN = supervisor_token
    HA_API_BASE = ha_api_base
    _ensure_read_allowed = ensure_read_allowed_fn
    _ensure_control_allowed = ensure_control_allowed_fn


async def ha_get_state_rest(entity_id: str) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{HA_API_BASE}/states/{entity_id}",
            headers=headers,
        )
    if response.status_code == 404:
        raise RuntimeError(f"Home Assistant entity not found: {entity_id}")
    if response.is_error:
        raise RuntimeError(f"Home Assistant returned HTTP {response.status_code}")
    return response.json()


def normalize_ha_state(state: dict[str, Any]) -> dict[str, Any]:
    attributes = state.get("attributes") or {}
    return {
        "entity_id": state.get("entity_id"),
        "state": state.get("state"),
        "friendly_name": attributes.get("friendly_name"),
        "attributes": attributes,
        "last_changed": state.get("last_changed"),
        "last_updated": state.get("last_updated"),
    }


async def ha_get_state(entity_id: str) -> dict[str, Any]:
    _ensure_read_allowed(entity_id)
    if not SUPERVISOR_TOKEN:
        raise RuntimeError("Home Assistant API token unavailable")

    try:
        state = await _ha_client.get_state(entity_id)
        if state is None:
            raise RuntimeError(f"Home Assistant entity not found: {entity_id}")
        return normalize_ha_state(state)
    except RuntimeError:
        return normalize_ha_state(await ha_get_state_rest(entity_id))


def _ha_power_state_matches(domain: str, state: Any, turn_on: bool) -> bool:
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
        latest = _ha_client.state_cache.get(entity_id)
        if latest and _ha_power_state_matches(domain, latest.get("state"), turn_on):
            return latest
        await asyncio.sleep(0.05)
    return latest


async def ha_set_power(entity_id: str, turn_on: bool) -> dict[str, Any]:
    domain = _ensure_control_allowed(entity_id)
    if not SUPERVISOR_TOKEN:
        raise RuntimeError("Home Assistant API token unavailable")

    service = "turn_on" if turn_on else "turn_off"
    transport = "websocket"

    try:
        await _ha_client.call_service(
            domain,
            service,
            {"entity_id": entity_id},
        )
        verified_raw = await _wait_for_ha_power_state(entity_id, domain, turn_on, timeout=5.0)
        if verified_raw is None:
            raise RuntimeError(f"No state received for {entity_id}")
        verified = normalize_ha_state(verified_raw)
    except RuntimeError:
        transport = "rest_fallback"
        headers = {
            "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{HA_API_BASE}/services/{domain}/{service}",
                headers=headers,
                json={"entity_id": entity_id},
            )
        if response.is_error:
            raise RuntimeError(
                f"Home Assistant action failed with HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )
        verified = normalize_ha_state(await ha_get_state_rest(entity_id))

    return {
        "success": _ha_power_state_matches(domain, verified.get("state"), turn_on),
        "requested_action": f"{domain}.{service}",
        "entity_id": entity_id,
        "verified_state": verified.get("state"),
        "friendly_name": verified.get("friendly_name"),
        "transport": transport,
    }
