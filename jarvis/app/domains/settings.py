from __future__ import annotations

import json
import os
from pathlib import Path
import re
import time
from typing import Any


OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5").strip()

SETTINGS_STORAGE_PATH = Path("/data/jarvis_settings.json")

GENERAL_INSTRUCTIONS_MAX_CHARS = 12000

ELEVENLABS_VOICE_DEFAULTS = {
    "stability": 0.55,
    "similarity": 0.75,
    "style": 0.15,
    "speed": 0.96,
}

JARVIS_PREFERENCE_DEFAULTS: dict[str, Any] = {
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
    preferences = dict(JARVIS_PREFERENCE_DEFAULTS)
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
