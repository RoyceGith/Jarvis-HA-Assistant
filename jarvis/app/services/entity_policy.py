from __future__ import annotations

import re
from typing import Any

def should_auto_approve_entity(
    entity_id: str,
    friendly_name: str,
    domain: str,
    device_class: str | None,
) -> bool:
    """Match the socket and HVAC inventory explicitly approved by the owner."""
    searchable = f"{entity_id} {friendly_name}".lower().replace("_", " ")
    words = set(re.findall(r"[a-z0-9]+", searchable))
    is_socket = domain == "switch" and (
        (device_class or "").lower() in {"outlet", "socket"}
        or bool(words & {"socket", "outlet", "plug"})
    )
    is_thermostat = domain == "climate" or "thermostat" in words
    is_air_conditioning_status = (
        domain in {"sensor", "binary_sensor"}
        and (
            "aircondition" in searchable.replace(" ", "")
            or "air conditioning" in searchable
            or "air conditioner" in searchable
            or "hvac" in words
            or "ac" in words
        )
        and bool(words & {"status", "state", "mode", "temperature", "temp"})
    )
    return is_socket or is_thermostat or is_air_conditioning_status

def classify_entity_risk(
    domain: str,
    device_class: str | None,
    entity_id: str = "",
    friendly_name: str = "",
) -> str:
    """Conservative default classification for inventory display only."""
    if should_auto_approve_entity(entity_id, friendly_name, domain, device_class):
        return "low_risk_control_proposed"

    if domain in {"sensor", "binary_sensor"}:
        return "read_only"

    if domain in {"light", "fan", "media_player", "scene"}:
        return "state_only"

    if domain in {"lock", "cover", "climate", "switch", "button", "script", "automation"}:
        return "restricted"

    if device_class in {"smoke", "gas", "moisture", "safety", "problem"}:
        return "read_only"

    return "state_only"
