from __future__ import annotations

import contextlib
import json
import os
import re
from pathlib import Path
from collections.abc import Callable
from typing import Any


HA_READ_ENTITIES_RAW = os.getenv("HA_READ_ENTITIES", "")
HA_CONTROL_ENTITIES_RAW = os.getenv("HA_CONTROL_ENTITIES", "")
SAFE_CONTROL_DOMAINS = {"light", "switch", "fan", "input_boolean", "climate"}


def parse_entity_list(raw: str) -> set[str]:
    return {
        item.strip()
        for item in raw.replace("\n", ",").split(",")
        if item.strip()
    }


HA_READ_ENTITIES = parse_entity_list(HA_READ_ENTITIES_RAW)
HA_CONTROL_ENTITIES = parse_entity_list(HA_CONTROL_ENTITIES_RAW)

DATA_DIR = Path("/data")
ENTITY_POLICY_PATH = DATA_DIR / "entity_policy.json"
V063_ENTITY_POLICY_PATH = Path("/share/jarvis/entity_policy.json")
V063_MIGRATION_MARKER = DATA_DIR / ".entity_policy_v063_migrated"

_automation_store: Callable[[], dict[str, Any]] = lambda: {}


def configure_entity_policy_service(
    *, automation_store_fn: Callable[[], dict[str, Any]],
) -> None:
    global _automation_store
    _automation_store = automation_store_fn


def load_entity_policy() -> dict[str, dict[str, Any]]:
    # Home Assistant preserves /data as the add-on's persistent storage. v0.6.3
    # mistakenly used /share without declaring a share mount, so recover that
    # policy once when it is still available. Merge it over any older /data
    # policy because v0.6.3 aliases are the newest records.
    if V063_ENTITY_POLICY_PATH.exists() and not V063_MIGRATION_MARKER.exists():
        try:
            v063_payload = json.loads(
                V063_ENTITY_POLICY_PATH.read_text(encoding="utf-8")
            )
            v063_entities = v063_payload.get("entities", {})
            current_entities: dict[str, dict[str, Any]] = {}
            if ENTITY_POLICY_PATH.exists():
                current_payload = json.loads(
                    ENTITY_POLICY_PATH.read_text(encoding="utf-8")
                )
                candidate = current_payload.get("entities", {})
                if isinstance(candidate, dict):
                    current_entities = candidate
            if isinstance(v063_entities, dict):
                save_entity_policy({**current_entities, **v063_entities})
                V063_MIGRATION_MARKER.write_text("migrated\n", encoding="utf-8")
        except (OSError, json.JSONDecodeError):
            pass

    if not ENTITY_POLICY_PATH.exists():
        return {}
    try:
        payload = json.loads(ENTITY_POLICY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    entities = payload.get("entities", {})
    return entities if isinstance(entities, dict) else {}


def save_entity_policy(policy: dict[str, dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary = ENTITY_POLICY_PATH.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"version": 1, "entities": policy}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(ENTITY_POLICY_PATH)


def effective_entity_access(entity_id: str) -> str | None:
    record = load_entity_policy().get(entity_id)
    if record and record.get("enabled"):
        return str(record.get("access") or "")
    if entity_id in HA_CONTROL_ENTITIES:
        return "low_risk_control_proposed"
    if entity_id in HA_READ_ENTITIES:
        return "read_only"
    return None


def entity_domain(entity_id: str) -> str:
    if "." not in entity_id:
        raise ValueError("Invalid Home Assistant entity ID")
    return entity_id.split(".", 1)[0]


def ensure_read_allowed(entity_id: str) -> None:
    access = effective_entity_access(entity_id)
    if access not in {"read_only", "state_only", "low_risk_control_proposed"}:
        raise PermissionError(f"Entity is not approved for ZBRANO access: {entity_id}")


def ensure_control_allowed(entity_id: str) -> str:
    access = effective_entity_access(entity_id)
    if access != "low_risk_control_proposed":
        raise PermissionError(f"Entity is not approved for ZBRANO control: {entity_id}")
    domain = entity_domain(entity_id)
    if domain not in SAFE_CONTROL_DOMAINS:
        raise PermissionError(
            f"Control blocked for domain '{domain}'. "
            "Only light, switch, fan, input_boolean, and climate are allowed."
        )
    return domain


def _search_tokens(value: str) -> set[str]:
    stop_words = {
        "the", "a", "an", "in", "on", "at", "of", "to", "my",
        "workshop", "workstation", "device", "socket", "switch",
        "light", "turn", "please",
    }
    return {
        token for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) >= 3 and token not in stop_words
    }


def find_approved_entities(query: str) -> dict[str, Any]:
    normalized = " ".join(query.lower().split())
    query_tokens = _search_tokens(normalized)
    policy = load_entity_policy()
    matches: list[dict[str, Any]] = []
    remembered_aliases: dict[str, list[str]] = {}
    with contextlib.suppress(Exception):
        for memory in _automation_store().get("entity_memory", []):
            remembered_aliases.setdefault(str(memory.get("entity_id") or ""), []).append(str(memory.get("alias") or ""))

    all_ids = set(policy) | HA_READ_ENTITIES | HA_CONTROL_ENTITIES

    for entity_id in sorted(all_ids):
        record = policy.get(entity_id, {})
        access = effective_entity_access(entity_id)
        if not access:
            continue

        friendly_name = str(record.get("friendly_name") or entity_id)
        aliases = [
            str(alias) for alias in record.get("aliases", [])
            if str(alias).strip()
        ]
        aliases = list(dict.fromkeys([*aliases, *remembered_aliases.get(entity_id, [])]))
        haystacks = [entity_id.replace("_", " "), friendly_name, *aliases]
        normalized_haystacks = [" ".join(value.lower().split()) for value in haystacks]

        exact = normalized in normalized_haystacks
        phrase_partial = any(normalized in value or value in normalized for value in normalized_haystacks)
        candidate_tokens = set().union(*(_search_tokens(value) for value in normalized_haystacks))
        overlap = query_tokens & candidate_tokens
        token_score = len(overlap) / max(len(query_tokens), 1)

        if not (exact or phrase_partial or overlap):
            continue

        score = 100 if exact else 80 if phrase_partial else int(token_score * 60)
        matches.append(
            {
                "entity_id": entity_id,
                "friendly_name": friendly_name,
                "aliases": aliases,
                "access": access,
                "control_approved": access == "low_risk_control_proposed",
                "domain": record.get("domain") or entity_domain(entity_id),
                "match_quality": "exact" if exact else "partial" if phrase_partial else "word",
                "matched_words": sorted(overlap),
                "score": score,
            }
        )

    matches.sort(key=lambda item: (-item["score"], item["friendly_name"].lower()))
    limited = matches[:20]
    recommended = None
    if limited:
        top_score = limited[0]["score"]
        tied = [item for item in limited if item["score"] == top_score]
        if len(tied) == 1:
            recommended = tied[0]

    return {
        "query": query,
        "count": len(matches),
        "matches": limited,
        "recommended_unique_match": recommended,
        "instruction": (
            "Use recommended_unique_match immediately when present; do not ask the user for search terms."
        ),
    }

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
