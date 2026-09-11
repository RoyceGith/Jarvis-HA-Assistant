from __future__ import annotations

import json
import os
from pathlib import Path
import re
import time
from typing import Any


OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5").strip()

SETTINGS_STORAGE_PATH = Path("/data/zbrano_settings.json")

GENERAL_INSTRUCTIONS_MAX_CHARS = 12000

ELEVENLABS_VOICE_DEFAULTS = {
    "stability": 0.55,
    "similarity": 0.75,
    "style": 0.15,
    "speed": 0.96,
}

ZBRANO_PREFERENCE_DEFAULTS: dict[str, Any] = {
    "elevenlabs_model": (
        ELEVENLABS_MODEL_ID
        if ELEVENLABS_MODEL_ID in {
            "eleven_flash_v2_5", "eleven_turbo_v2_5", "eleven_multilingual_v2"
        }
        else "eleven_flash_v2_5"
    ),
    "elevenlabs_speaker_boost": False,
    "agent_model": OPENAI_MODEL,
    "reasoning_effort": "medium",
    "auto_speak": True,
    "proactive_voice_enabled": True,
    "voice_approval_enabled": True,
    "wake_word_enabled": False,
    "wake_phrase": "hey zbrano",
    "response_length": "balanced",
    "confirmation_strictness": "standard",
    "context_messages": 20,
    "retention_days": 90,
    "preferred_language": "auto",
    "pronunciation_dictionary": "",
    "theme": "dark",
    "neural_style": "constellation",
    "neural_scale": 1.0,
    "neural_node_size": 1.0,
    "neural_opacity": 0.38,
    "reduced_motion": False,
    "text_size": "medium",
    "interface_density": "comfortable",
    "quiet_hours_enabled": False,
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "07:00",
    "voice_volume": 0.9,
    "auto_sync_releases_to_workshop_memory": True,
    "web_search_enabled": True,
    "web_search_context_size": "medium",
    "fast_memory_enabled": True,
    "fast_memory_auto_capture": True,
    "fast_memory_context_items": 10,
}

ELEVENLABS_MODELS = {
    "eleven_flash_v2_5",
    "eleven_turbo_v2_5",
    "eleven_multilingual_v2",
}

ONBOARDING_VERSION = 1
ONBOARDING_STEP_IDS = frozenset({
    "home_assistant",
    "model",
    "entities",
    "voice",
    "memory",
    "plugins",
    "notifications",
})
ONBOARDING_STEP_ORDER = (
    "home_assistant",
    "model",
    "entities",
    "voice",
    "memory",
    "plugins",
    "notifications",
)
ONBOARDING_OPTIONAL_STEP_IDS = frozenset(ONBOARDING_STEP_ORDER[2:])
ONBOARDING_CHECK_DETAIL_MAX_CHARS = 500

def _onboarding_checks(stored: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw_checks = stored.get("checks")
    if not isinstance(raw_checks, dict):
        return {}
    checks: dict[str, dict[str, Any]] = {}
    for step_id in ONBOARDING_STEP_IDS:
        item = raw_checks.get(step_id)
        if not isinstance(item, dict):
            continue
        checks[step_id] = {
            "ready": bool(item.get("ready")),
            "detail": str(item.get("detail") or "")[:ONBOARDING_CHECK_DETAIL_MAX_CHARS],
            "checked_at": float(item.get("checked_at") or 0),
        }
    return checks

def _onboarding_skipped_steps(stored: dict[str, Any]) -> list[str]:
    raw = stored.get("skipped_steps")
    if not isinstance(raw, list):
        return []
    selected = {str(item) for item in raw} & ONBOARDING_OPTIONAL_STEP_IDS
    return [step_id for step_id in ONBOARDING_STEP_ORDER if step_id in selected]

def load_settings_payload() -> dict[str, Any]:
    if not SETTINGS_STORAGE_PATH.exists():
        return {}
    try:
        payload = json.loads(SETTINGS_STORAGE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}

def save_settings_payload(payload: dict[str, Any]) -> None:
    SETTINGS_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = SETTINGS_STORAGE_PATH.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(SETTINGS_STORAGE_PATH)

def load_onboarding_state() -> dict[str, Any]:
    payload = load_settings_payload()
    stored = payload.get("onboarding")
    explicit = isinstance(stored, dict)
    legacy_installation = (bool(payload) or SETTINGS_STORAGE_PATH.exists()) and not explicit
    stored = stored if explicit else {}
    completed = bool(stored.get("completed")) if explicit else legacy_installation
    dismissed = bool(stored.get("dismissed")) if explicit else False
    current_step = str(stored.get("current_step") or ONBOARDING_STEP_ORDER[0])
    if current_step not in ONBOARDING_STEP_IDS:
        current_step = ONBOARDING_STEP_ORDER[0]
    return {
        "version": ONBOARDING_VERSION,
        "completed": completed,
        "dismissed": dismissed,
        "legacy_installation": legacy_installation,
        "show_on_startup": not legacy_installation and not completed and not dismissed,
        "updated_at": float(stored.get("updated_at") or 0),
        "checks": _onboarding_checks(stored),
        "current_step": current_step,
        "skipped_steps": _onboarding_skipped_steps(stored),
    }

def save_onboarding_state(*, completed: bool, dismissed: bool) -> dict[str, Any]:
    payload = load_settings_payload()
    current = load_onboarding_state()
    state = {
        "version": ONBOARDING_VERSION,
        "completed": bool(completed),
        "dismissed": bool(dismissed) and not bool(completed),
        "updated_at": time.time(),
        "checks": current["checks"],
        "current_step": current["current_step"],
        "skipped_steps": current["skipped_steps"],
    }
    payload.setdefault("version", 3)
    payload["onboarding"] = state
    save_settings_payload(payload)
    return load_onboarding_state()

def save_onboarding_check(
    step_id: str,
    *,
    ready: bool,
    detail: str,
    checked_at: float | None = None,
) -> dict[str, Any]:
    if step_id not in ONBOARDING_STEP_IDS:
        raise ValueError("Unknown onboarding step")
    payload = load_settings_payload()
    current = load_onboarding_state()
    checks = dict(current["checks"])
    checks[step_id] = {
        "ready": bool(ready),
        "detail": str(detail)[:ONBOARDING_CHECK_DETAIL_MAX_CHARS],
        "checked_at": float(checked_at or time.time()),
    }
    skipped_steps = [item for item in current["skipped_steps"] if item != step_id or not ready]
    payload.setdefault("version", 3)
    payload["onboarding"] = {
        "version": ONBOARDING_VERSION,
        "completed": bool(current["completed"]),
        "dismissed": bool(current["dismissed"]) and not bool(current["completed"]),
        "updated_at": time.time(),
        "checks": checks,
        "current_step": current["current_step"],
        "skipped_steps": skipped_steps,
    }
    save_settings_payload(payload)
    return load_onboarding_state()

def save_onboarding_progress(
    current_step: str,
    *,
    skipped_step: str | None = None,
) -> dict[str, Any]:
    if current_step not in ONBOARDING_STEP_IDS:
        raise ValueError("Unknown onboarding step")
    if skipped_step is not None and skipped_step not in ONBOARDING_OPTIONAL_STEP_IDS:
        raise ValueError("Only optional onboarding steps can be skipped")
    payload = load_settings_payload()
    current = load_onboarding_state()
    skipped_steps = set(current["skipped_steps"])
    if skipped_step:
        skipped_steps.add(skipped_step)
    payload.setdefault("version", 3)
    payload["onboarding"] = {
        "version": ONBOARDING_VERSION,
        "completed": bool(current["completed"]),
        "dismissed": bool(current["dismissed"]) and not bool(current["completed"]),
        "updated_at": time.time(),
        "checks": current["checks"],
        "current_step": current_step,
        "skipped_steps": [
            step_id for step_id in ONBOARDING_STEP_ORDER if step_id in skipped_steps
        ],
    }
    save_settings_payload(payload)
    return load_onboarding_state()

def load_general_instructions() -> str:
    payload = load_settings_payload()
    instructions = payload.get("general_instructions", "")
    return str(instructions)[:GENERAL_INSTRUCTIONS_MAX_CHARS]

def save_general_instructions(instructions: str) -> str:
    cleaned = instructions.strip()
    if len(cleaned) > GENERAL_INSTRUCTIONS_MAX_CHARS:
        raise ValueError(
            f"General instructions cannot exceed {GENERAL_INSTRUCTIONS_MAX_CHARS} characters"
        )
    payload = load_settings_payload()
    payload.update(
        {"version": 2, "general_instructions": cleaned, "updated_at": time.time()}
    )
    save_settings_payload(payload)
    return cleaned

def load_elevenlabs_voice_settings() -> dict[str, float]:
    stored = load_settings_payload().get("elevenlabs_voice_settings", {})
    if not isinstance(stored, dict):
        stored = {}
    settings = dict(ELEVENLABS_VOICE_DEFAULTS)
    ranges = {
        "stability": (0.0, 1.0),
        "similarity": (0.0, 1.0),
        "style": (0.0, 1.0),
        "speed": (0.7, 1.2),
    }
    for key, (minimum, maximum) in ranges.items():
        try:
            value = float(stored.get(key, settings[key]))
        except (TypeError, ValueError):
            continue
        if minimum <= value <= maximum:
            settings[key] = value
    return settings

def save_elevenlabs_voice_settings(settings: dict[str, float]) -> dict[str, float]:
    payload = load_settings_payload()
    payload.update(
        {
            "version": 2,
            "elevenlabs_voice_settings": settings,
            "updated_at": time.time(),
        }
    )
    save_settings_payload(payload)
    return settings

def load_preferences() -> dict[str, Any]:
    stored = load_settings_payload().get("preferences", {})
    if not isinstance(stored, dict):
        stored = {}
    preferences = dict(ZBRANO_PREFERENCE_DEFAULTS)
    preferences.update({key: stored[key] for key in preferences if key in stored})
    return preferences

def save_preferences(preferences: dict[str, Any]) -> dict[str, Any]:
    payload = load_settings_payload()
    payload.update(
        {"version": 3, "preferences": preferences, "updated_at": time.time()}
    )
    save_settings_payload(payload)
    return preferences

def apply_pronunciation_dictionary(text: str) -> str:
    rules = load_preferences().get("pronunciation_dictionary", "")
    if not isinstance(rules, str):
        return text
    replacements: list[tuple[str, str]] = []
    for line in rules.splitlines()[:100]:
        if "=" not in line:
            continue
        term, spoken = (part.strip() for part in line.split("=", 1))
        if term and spoken and len(term) <= 80 and len(spoken) <= 160:
            replacements.append((term, spoken))
    for term, spoken in sorted(replacements, key=lambda item: len(item[0]), reverse=True):
        text = re.sub(rf"(?<!\w){re.escape(term)}(?!\w)", spoken, text, flags=re.IGNORECASE)
    return text

def append_general_instruction(instruction: str) -> dict[str, Any]:
    cleaned = " ".join(instruction.strip().split())
    if not cleaned:
        raise ValueError("Instruction cannot be empty")
    current = load_general_instructions()
    existing_lines = {line.strip().lstrip("- ").casefold() for line in current.splitlines() if line.strip()}
    if cleaned.casefold() in existing_lines:
        return {"saved": False, "reason": "already_saved", "instruction": cleaned}
    updated = f"{current.rstrip()}\n- {cleaned}".strip() if current else f"- {cleaned}"
    save_general_instructions(updated)
    return {"saved": True, "instruction": cleaned}
