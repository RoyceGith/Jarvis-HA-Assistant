from __future__ import annotations

import asyncio
from collections import deque
import contextlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, AsyncIterator

from .intent_router import parse_local_ha_intent

import httpx
import websockets
from websockets.exceptions import ConnectionClosed
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"

HA_API_BASE = "http://supervisor/core/api"
HA_WS_URL = "ws://supervisor/core/websocket"
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN", "")
WORKSHOP_MEMORY_URL = os.getenv(
    "WORKSHOP_MEMORY_URL",
    "http://workshop-memory.local:3001/mcp",
).rstrip("/")
WORKSHOP_MEMORY_INTERNAL_URL = os.getenv(
    "WORKSHOP_MEMORY_INTERNAL_URL",
    "http://workshop_memory:3001/mcp",
).rstrip("/")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_TRANSCRIPTION_MODEL = os.getenv(
    "OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-transcribe"
)
OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
OPENAI_TRANSCRIPTIONS_URL = "https://api.openai.com/v1/audio/transcriptions"
OPENAI_SPEECH_URL = "https://api.openai.com/v1/audio/speech"
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
ELEVENLABS_VOICE_NAME = os.getenv("ELEVENLABS_VOICE_NAME", "ElevenLabs").strip() or "ElevenLabs"
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5").strip()
ELEVENLABS_SPEECH_URL = "https://api.elevenlabs.io/v1/text-to-speech"
SPEECH_PROVIDER = os.getenv("SPEECH_PROVIDER", "openai").strip().lower()
SPEECH_FALLBACK_TO_OPENAI = os.getenv("SPEECH_FALLBACK_TO_OPENAI", "true").strip().lower() in {
    "1", "true", "yes", "on",
}
VOICE_UPLOAD_MAX_BYTES = 12 * 1024 * 1024
TTS_VOICES = {
    "alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx",
    "sage", "shimmer", "verse", "marin", "cedar",
}

CHAT_HISTORY_MAX_MESSAGES = 200
CHAT_CONTEXT_MAX_MESSAGES = 20
CHAT_SESSIONS_MAX = 100
CHAT_SESSIONS: dict[str, deque[dict[str, Any]]] = {}
CHAT_SESSION_ORDER: deque[str] = deque(maxlen=CHAT_SESSIONS_MAX)
CHAT_SESSION_META: dict[str, dict[str, Any]] = {}
CHAT_STORAGE_PATH = Path("/data/chat_sessions.json")
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
    "auto_speak": True,
    "response_length": "balanced",
    "confirmation_strictness": "standard",
    "context_messages": 20,
    "retention_days": 90,
    "preferred_language": "auto",
    "pronunciation_dictionary": "",
    "theme": "dark",
    "reduced_motion": False,
    "text_size": "medium",
    "interface_density": "comfortable",
    "quiet_hours_enabled": False,
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "07:00",
    "voice_volume": 0.9,
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

LAST_ENTITY_BY_SESSION: dict[str, dict[str, Any]] = {}
PENDING_LOW_RISK_ACTIONS: dict[str, dict[str, Any]] = {}


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


def remember_session_entity(
    session_id: str,
    entity_id: str,
    friendly_name: str | None,
    state: str | None,
) -> None:
    LAST_ENTITY_BY_SESSION[session_id or "default"] = {
        "entity_id": entity_id,
        "friendly_name": friendly_name or entity_id,
        "state": state,
        "updated_at": time.time(),
    }


def get_session_entity(session_id: str) -> dict[str, Any] | None:
    return LAST_ENTITY_BY_SESSION.get(session_id or "default")


def is_entity_followup(message: str) -> bool:
    normalized = " ".join(message.lower().strip().split())
    return normalized in {
        "is it on",
        "is it off",
        "is that on",
        "is that off",
        "turn it on",
        "turn it off",
        "switch it on",
        "switch it off",
        "now turn it on",
        "now turn it off",
        "now turn on",
        "now turn off",
        "what state is it in",
        "what is its state",
    }


def chat_title(messages: deque[dict[str, Any]]) -> str:
    for message in messages:
        if message.get("role") == "user" and message.get("content"):
            title = " ".join(str(message["content"]).split())
            return title[:48] + ("…" if len(title) > 48 else "")
    return "New chat"


def persist_chat_sessions() -> None:
    CHAT_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "sessions": {
            session_id: {
                "title": CHAT_SESSION_META.get(session_id, {}).get("title")
                or chat_title(messages),
                "updated_at": CHAT_SESSION_META.get(session_id, {}).get("updated_at", 0),
                "messages": list(messages),
            }
            for session_id, messages in CHAT_SESSIONS.items()
        },
    }
    temporary = CHAT_STORAGE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(CHAT_STORAGE_PATH)


def load_chat_sessions() -> None:
    if not CHAT_STORAGE_PATH.exists():
        return
    try:
        payload = json.loads(CHAT_STORAGE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    sessions = payload.get("sessions", {})
    if not isinstance(sessions, dict):
        return
    ordered = sorted(
        sessions.items(),
        key=lambda item: float(item[1].get("updated_at", 0)) if isinstance(item[1], dict) else 0,
    )[-CHAT_SESSIONS_MAX:]
    CHAT_SESSIONS.clear()
    CHAT_SESSION_ORDER.clear()
    CHAT_SESSION_META.clear()
    for session_id, record in ordered:
        if not isinstance(record, dict):
            continue
        clean_messages = [
            {"role": item.get("role"), "content": str(item.get("content", ""))}
            for item in record.get("messages", [])
            if isinstance(item, dict)
            and item.get("role") in {"user", "assistant"}
            and item.get("content")
        ]
        CHAT_SESSIONS[session_id] = deque(clean_messages, maxlen=CHAT_HISTORY_MAX_MESSAGES)
        CHAT_SESSION_ORDER.append(session_id)
        CHAT_SESSION_META[session_id] = {
            "title": str(record.get("title") or chat_title(CHAT_SESSIONS[session_id])),
            "updated_at": float(record.get("updated_at", 0)),
        }


def prune_expired_chats() -> int:
    retention_days = int(load_preferences().get("retention_days", 90) or 0)
    if retention_days <= 0:
        return 0
    cutoff = time.time() - retention_days * 86400
    expired = [
        session_id for session_id, meta in CHAT_SESSION_META.items()
        if float(meta.get("updated_at", 0)) and float(meta.get("updated_at", 0)) < cutoff
    ]
    for session_id in expired:
        CHAT_SESSIONS.pop(session_id, None)
        CHAT_SESSION_META.pop(session_id, None)
        with contextlib.suppress(ValueError):
            CHAT_SESSION_ORDER.remove(session_id)
    if expired:
        persist_chat_sessions()
    return len(expired)


def get_chat_history(session_id: str) -> deque[dict[str, Any]]:
    session_id = session_id.strip() or "default"
    if session_id not in CHAT_SESSIONS:
        if len(CHAT_SESSIONS) >= CHAT_SESSIONS_MAX and CHAT_SESSION_ORDER:
            oldest = CHAT_SESSION_ORDER.popleft()
            CHAT_SESSIONS.pop(oldest, None)
            CHAT_SESSION_META.pop(oldest, None)
        CHAT_SESSIONS[session_id] = deque(maxlen=CHAT_HISTORY_MAX_MESSAGES)
        CHAT_SESSION_ORDER.append(session_id)
        CHAT_SESSION_META[session_id] = {"title": "New chat", "updated_at": time.time()}
    return CHAT_SESSIONS[session_id]


def append_chat_message(session_id: str, role: str, content: str) -> None:
    if not content:
        return
    history = get_chat_history(session_id)
    history.append({"role": role, "content": content})
    CHAT_SESSION_META[session_id] = {
        "title": chat_title(history),
        "updated_at": time.time(),
    }
    persist_chat_sessions()


def clear_chat_history(session_id: str) -> None:
    CHAT_SESSIONS.pop(session_id, None)
    LAST_ENTITY_BY_SESSION.pop(session_id, None)
    CHAT_SESSION_META.pop(session_id, None)
    try:
        CHAT_SESSION_ORDER.remove(session_id)
    except ValueError:
        pass
    persist_chat_sessions()

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


class HomeAssistantWebSocketClient:
    """Persistent Home Assistant WebSocket client with state cache and REST fallback."""

    def __init__(self, url: str, token: str) -> None:
        self.url = url
        self.token = token
        self.websocket: Any | None = None
        self.reader_task: asyncio.Task[None] | None = None
        self.connect_lock = asyncio.Lock()
        self.send_lock = asyncio.Lock()
        self.pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self.next_id = 1
        self.state_cache: dict[str, dict[str, Any]] = {}
        self.connected = False
        self.last_error: str | None = None
        self.subscription_id: int | None = None

    async def connect(self) -> None:
        if self.connected and self.websocket is not None:
            return
        if not self.token:
            raise RuntimeError("Home Assistant API token unavailable")

        async with self.connect_lock:
            if self.connected and self.websocket is not None:
                return
            await self._disconnect()

            try:
                ws = await websockets.connect(
                    self.url,
                    open_timeout=10,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                    max_size=4 * 1024 * 1024,
                )
                hello = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                if hello.get("type") != "auth_required":
                    await ws.close()
                    raise RuntimeError(
                        f"Unexpected Home Assistant WebSocket greeting: {hello.get('type')}"
                    )

                await ws.send(json.dumps({"type": "auth", "access_token": self.token}))
                auth = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                if auth.get("type") != "auth_ok":
                    await ws.close()
                    raise RuntimeError(
                        auth.get("message") or "Home Assistant WebSocket authentication failed"
                    )

                self.websocket = ws
                self.connected = True
                self.last_error = None
                self.reader_task = asyncio.create_task(
                    self._reader_loop(),
                    name="jarvis-ha-websocket-reader",
                )

                states_result = await self.command({"type": "get_states"}, ensure=False)
                states = states_result.get("result") or []
                self.state_cache = {
                    state["entity_id"]: state
                    for state in states
                    if isinstance(state, dict) and state.get("entity_id")
                }

                subscription = await self.command(
                    {"type": "subscribe_events", "event_type": "state_changed"},
                    ensure=False,
                )
                self.subscription_id = subscription.get("id")
            except Exception as exc:
                self.last_error = str(exc)
                await self._disconnect()
                raise RuntimeError(
                    f"Home Assistant WebSocket connection failed: {exc}"
                ) from exc

    async def _reader_loop(self) -> None:
        try:
            assert self.websocket is not None
            async for raw in self.websocket:
                message = json.loads(raw)
                message_type = message.get("type")

                if message_type == "result":
                    future = self.pending.pop(int(message.get("id", -1)), None)
                    if future and not future.done():
                        future.set_result(message)
                    continue

                if message_type == "event":
                    event = message.get("event") or {}
                    if event.get("event_type") != "state_changed":
                        continue
                    data = event.get("data") or {}
                    entity_id = data.get("entity_id")
                    new_state = data.get("new_state")
                    if not entity_id:
                        continue
                    if new_state is None:
                        self.state_cache.pop(entity_id, None)
                    elif isinstance(new_state, dict):
                        self.state_cache[entity_id] = new_state
        except asyncio.CancelledError:
            raise
        except (ConnectionClosed, OSError, json.JSONDecodeError) as exc:
            self.last_error = str(exc)
        finally:
            self.connected = False
            error = RuntimeError(
                f"Home Assistant WebSocket disconnected: {self.last_error or 'connection closed'}"
            )
            for future in self.pending.values():
                if not future.done():
                    future.set_exception(error)
            self.pending.clear()

    async def command(
        self,
        payload: dict[str, Any],
        timeout: float = 15.0,
        ensure: bool = True,
    ) -> dict[str, Any]:
        if ensure:
            await self.connect()
        if not self.connected or self.websocket is None:
            raise RuntimeError("Home Assistant WebSocket is not connected")

        loop = asyncio.get_running_loop()
        async with self.send_lock:
            command_id = self.next_id
            self.next_id += 1
            future: asyncio.Future[dict[str, Any]] = loop.create_future()
            self.pending[command_id] = future
            message = {"id": command_id, **payload}
            try:
                await self.websocket.send(json.dumps(message))
            except Exception:
                self.pending.pop(command_id, None)
                self.connected = False
                raise

        try:
            response = await asyncio.wait_for(future, timeout=timeout)
        except Exception:
            self.pending.pop(command_id, None)
            raise

        if not response.get("success"):
            error = response.get("error") or {}
            raise RuntimeError(
                error.get("message")
                or error.get("code")
                or "Home Assistant WebSocket command failed"
            )
        return response

    async def get_state(self, entity_id: str) -> dict[str, Any] | None:
        await self.connect()
        return self.state_cache.get(entity_id)

    async def call_service(
        self,
        domain: str,
        service: str,
        service_data: dict[str, Any],
    ) -> dict[str, Any]:
        return await self.command(
            {
                "type": "call_service",
                "domain": domain,
                "service": service,
                "service_data": service_data,
                "return_response": False,
            }
        )

    async def wait_for_state(
        self,
        entity_id: str,
        expected: str,
        timeout: float = 5.0,
    ) -> dict[str, Any] | None:
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            state = self.state_cache.get(entity_id)
            if state and state.get("state") == expected:
                return state
            await asyncio.sleep(0.05)
        return self.state_cache.get(entity_id)

    async def _disconnect(self) -> None:
        self.connected = False
        if self.reader_task and self.reader_task is not asyncio.current_task():
            self.reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.reader_task
        self.reader_task = None

        if self.websocket is not None:
            with contextlib.suppress(Exception):
                await self.websocket.close()
        self.websocket = None
        self.subscription_id = None

    async def close(self) -> None:
        await self._disconnect()

    def status(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "cached_entities": len(self.state_cache),
            "subscription_active": self.subscription_id is not None,
            "last_error": self.last_error,
        }


ha_ws = HomeAssistantWebSocketClient(HA_WS_URL, SUPERVISOR_TOKEN)

app = FastAPI(
    title="Jarvis Workshop Assistant",
    version="0.8.5",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


class ChatRequest(BaseModel):
    session_id: str = Field(default="default", min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4000)


class ChatSessionCreate(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)


class JarvisSettingsUpdate(BaseModel):
    general_instructions: str = Field(default="", max_length=GENERAL_INSTRUCTIONS_MAX_CHARS)
    elevenlabs_stability: float = Field(default=0.55, ge=0.0, le=1.0)
    elevenlabs_similarity: float = Field(default=0.75, ge=0.0, le=1.0)
    elevenlabs_style: float = Field(default=0.15, ge=0.0, le=1.0)
    elevenlabs_speed: float = Field(default=0.96, ge=0.7, le=1.2)
    elevenlabs_model: str = Field(default="eleven_flash_v2_5")
    elevenlabs_speaker_boost: bool = False
    auto_speak: bool = True
    response_length: str = Field(default="balanced", pattern="^(brief|balanced|detailed)$")
    confirmation_strictness: str = Field(default="standard", pattern="^(standard|cautious)$")
    context_messages: int = Field(default=20, ge=4, le=50)
    retention_days: int = Field(default=90, ge=0, le=365)
    preferred_language: str = Field(default="auto", min_length=2, max_length=40)
    pronunciation_dictionary: str = Field(default="", max_length=8000)
    theme: str = Field(default="dark", pattern="^(dark|light|gray)$")
    reduced_motion: bool = False
    text_size: str = Field(default="medium", pattern="^(small|medium|large)$")
    interface_density: str = Field(default="comfortable", pattern="^(compact|comfortable)$")
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = Field(default="22:00", pattern="^([01]\\d|2[0-3]):[0-5]\\d$")
    quiet_hours_end: str = Field(default="07:00", pattern="^([01]\\d|2[0-3]):[0-5]\\d$")
    voice_volume: float = Field(default=0.9, ge=0.0, le=1.0)


class SettingsRestoreRequest(BaseModel):
    backup: dict[str, Any]


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    provider: str = Field(default="default", pattern="^(default|openai|elevenlabs)$")
    voice: str = Field(default="cedar", min_length=1, max_length=100)


class EntityCatalogItem(BaseModel):
    entity_id: str = Field(min_length=3, max_length=255)
    friendly_name: str = Field(min_length=1, max_length=255)
    domain: str = Field(min_length=1, max_length=64)
    device_class: str | None = Field(default=None, max_length=100)
    unit: str | None = Field(default=None, max_length=64)
    access: str = Field(
        pattern="^(read_only|state_only|low_risk_control_proposed|confirmation_required|restricted)$"
    )
    aliases: list[str] = Field(default_factory=list, max_length=20)


class EntityCatalogDraftRequest(BaseModel):
    project: str = Field(default="Jarvis Workshop Assistant", min_length=1, max_length=255)
    entities: list[EntityCatalogItem] = Field(min_length=1, max_length=500)


class EntityPolicyUpdate(BaseModel):
    enabled: bool
    friendly_name: str = Field(min_length=1, max_length=255)
    domain: str = Field(min_length=1, max_length=64)
    device_class: str | None = Field(default=None, max_length=100)
    unit: str | None = Field(default=None, max_length=64)
    access: str = Field(
        pattern="^(read_only|state_only|low_risk_control_proposed|confirmation_required|restricted)$"
    )
    aliases: list[str] = Field(default_factory=list, max_length=20)



MCP_HTTP_TIMEOUT = httpx.Timeout(30.0, connect=2.0)
MCP_HTTP_LIMITS = httpx.Limits(
    max_connections=10,
    max_keepalive_connections=5,
    keepalive_expiry=60.0,
)
MCP_CLIENT: httpx.AsyncClient | None = None
MCP_ACTIVE_URL: str | None = None
MCP_LAST_ERROR: str | None = None
MCP_LAST_LATENCY_MS: float | None = None
MCP_LAST_SUCCESS_AT: float | None = None
MCP_ENDPOINT_LATENCY_MS: dict[str, float] = {}
MCP_TOOL_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
MCP_CACHE_TTLS = {
    "get_profile_summary": 900.0,
    "get_project_context": 300.0,
    "get_latest_handoff": 120.0,
    "get_open_decisions": 120.0,
    "list_projects": 120.0,
}
MCP_LOCK = asyncio.Lock()


def workshop_memory_candidates() -> list[str]:
    candidates: list[str] = []
    for value in (WORKSHOP_MEMORY_INTERNAL_URL, WORKSHOP_MEMORY_URL):
        cleaned = value.strip().rstrip("/")
        if cleaned and cleaned not in candidates:
            candidates.append(cleaned)
    return candidates


def mcp_cache_key(tool_name: str, arguments: dict[str, Any]) -> str:
    return json.dumps(
        {"tool": tool_name, "arguments": arguments},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def get_cached_mcp_result(
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any] | None:
    ttl = MCP_CACHE_TTLS.get(tool_name)
    if not ttl:
        return None
    entry = MCP_TOOL_CACHE.get(mcp_cache_key(tool_name, arguments))
    if not entry:
        return None
    created_at, result = entry
    if time.monotonic() - created_at > ttl:
        MCP_TOOL_CACHE.pop(mcp_cache_key(tool_name, arguments), None)
        return None
    return result


def set_cached_mcp_result(
    tool_name: str,
    arguments: dict[str, Any],
    result: dict[str, Any],
) -> None:
    if tool_name in MCP_CACHE_TTLS:
        MCP_TOOL_CACHE[mcp_cache_key(tool_name, arguments)] = (
            time.monotonic(),
            result,
        )


async def get_mcp_client() -> httpx.AsyncClient:
    global MCP_CLIENT
    if MCP_CLIENT is None or MCP_CLIENT.is_closed:
        MCP_CLIENT = httpx.AsyncClient(
            timeout=MCP_HTTP_TIMEOUT,
            limits=MCP_HTTP_LIMITS,
            http2=False,
        )
    return MCP_CLIENT


async def close_mcp_client() -> None:
    global MCP_CLIENT
    if MCP_CLIENT is not None and not MCP_CLIENT.is_closed:
        await MCP_CLIENT.aclose()
    MCP_CLIENT = None


class MCPError(RuntimeError):
    pass


class OpenAIError(RuntimeError):
    pass


WORKSHOP_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "list_projects",
        "description": "List available projects in the Workshop Memory Obsidian vault.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_project_context",
        "description": (
            "Load compact context for a named workshop project, including its "
            "overview, latest handoff, unresolved decisions, and requirements."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "Exact project name.",
                },
                "include_requirements": {
                    "type": "boolean",
                    "description": "Whether project requirements should be included.",
                },
            },
            "required": ["project", "include_requirements"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_latest_handoff",
        "description": "Return the latest session handoff for a named project.",
        "parameters": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Exact project name."},
            },
            "required": ["project"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_open_decisions",
        "description": "Return unresolved Open or Proposed design decisions for a project.",
        "parameters": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Exact project name."},
            },
            "required": ["project"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_profile_summary",
        "description": "Return the user's compact workshop workflow and preferences summary.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_home_assistant_state",
        "description": "Read one approved Home Assistant entity state.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "Exact Home Assistant entity ID."}
            },
            "required": ["entity_id"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "turn_on_home_assistant_entity",
        "description": "Immediately turn on one enabled entity whose access is low_risk_control_proposed. No extra approval is required.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "Exact approved Home Assistant entity ID."}
            },
            "required": ["entity_id"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "turn_off_home_assistant_entity",
        "description": "Immediately turn off one enabled entity whose access is low_risk_control_proposed. No extra approval is required.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "Exact approved Home Assistant entity ID."}
            },
            "required": ["entity_id"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "find_home_assistant_entities",
        "description": (
            "Find Jarvis-approved Home Assistant entities by friendly name, "
            "entity ID, or alias. Use this before state or control calls when "
            "the user gives a natural device name."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural device name, alias, or partial entity ID."
                }
            },
            "required": ["query"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "save_general_instruction",
        "description": (
            "Append one behavior or preference to Jarvis General Instructions. "
            "Call this only when the user explicitly asks to save, remember, add, "
            "or use a behavior as a standing instruction. Never infer permission "
            "to save from an ordinary example or correction."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "instruction": {
                    "type": "string",
                    "description": "A concise standalone instruction preserving the user's intent.",
                }
            },
            "required": ["instruction"],
            "additionalProperties": False,
        },
        "strict": True,
    }
]


BASE_SYSTEM_INSTRUCTIONS = """
You are Jarvis, a practical workshop assistant.

Workshop Memory is the source of truth for accepted project knowledge.
Use Workshop Memory tools whenever the user asks about projects, prior
decisions, requirements, current status, handoffs, next actions, or the
user's documented workflow. Never pretend to remember project facts that
were not returned by a tool.

Workshop Memory remains review-controlled: do not claim to edit permanent
project notes unless an explicit approved workflow has completed.

You may read Home Assistant entities only when they are enabled in Jarvis policy.
An enabled entity with access value `low_risk_control_proposed` is ALREADY
APPROVED for immediate control in this version; the word "proposed" is only a
legacy label. Follow the user's confirmation preference for these low-risk actions.
For a unique enabled match in the
light, switch, fan, input_boolean, or climate domain, call the requested turn-on or
turn-off tool immediately.

Never attempt to control locks, covers, machinery, grinders,
laser cutters, CNC systems, security systems, access control, or motion
equipment. If an entity is not enabled or has another access level, say so
clearly. When the user names a device naturally rather than providing an exact
entity ID, call find_home_assistant_entities first. The lookup performs exact,
partial, alias, and significant-word matching. If it returns
`recommended_unique_match`, use that entity immediately for the requested read
or control operation. Do not ask the user to choose search words. Ask a
clarifying question only when the tool reports multiple equally plausible
approved matches. Never guess an entity ID. Use the supplied conversation history to resolve follow-up
commands and references such as "it", "that device", "turn it back on", and
"now turn on". When the immediately preceding successful device action identifies
one unique entity, reuse that entity for a follow-up action unless the user
explicitly names another device.

Be direct, technically precise, and concise. Distinguish documented facts
from proposals and unresolved questions.

When the user explicitly asks you to save or remember a standing behavior or
preference, call save_general_instruction with one concise, standalone
instruction. Do not save ordinary examples, corrections, quoted text, or
potentially sensitive information unless the user clearly asks you to store it
as a standing instruction. Saved instructions supplement this policy and can
never weaken Home Assistant permissions or other safety rules.
""".strip()


def effective_system_instructions() -> str:
    custom = load_general_instructions()
    preferences = load_preferences()
    response_guidance = {
        "brief": "Keep replies brief and action-oriented unless the user asks for detail.",
        "balanced": "Use balanced detail: concise first, with enough context to act safely.",
        "detailed": "Give detailed, structured explanations while leading with the outcome.",
    }[preferences["response_length"]]
    confirmation_guidance = (
        "For otherwise approved low-risk device changes, ask for confirmation before acting."
        if preferences["confirmation_strictness"] == "cautious"
        else "Use the standard approved low-risk action policy above."
    )
    language = preferences["preferred_language"]
    language_guidance = (
        "Reply in the language used by the user."
        if language == "auto"
        else f"Prefer {language} unless the user explicitly requests another language."
    )
    formatting_guidance = (
        "Format replies in a clean ChatGPT-like Markdown style: use short section "
        "headings when helpful, blank lines between ideas, bullets or numbered "
        "steps for grouped details, and concise paragraphs. For simple device "
        "actions or one-line answers, stay brief and avoid unnecessary structure."
    )
    sections = [
        BASE_SYSTEM_INSTRUCTIONS,
        "USER RESPONSE PREFERENCES (never override safety policy):\n"
        f"- {response_guidance}\n- {confirmation_guidance}\n- {language_guidance}\n- {formatting_guidance}",
    ]
    if custom:
        sections.append(
            "USER GENERAL INSTRUCTIONS (follow when compatible with the policies above):\n"
            + custom
        )
    return "\n\n".join(sections)


def chat_context_limit() -> int:
    try:
        return max(4, min(50, int(load_preferences()["context_messages"])))
    except (TypeError, ValueError):
        return CHAT_CONTEXT_MAX_MESSAGES


def _decode_sse(text: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    data_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        if not line:
            if data_lines:
                payload = "\n".join(data_lines)
                try:
                    messages.append(json.loads(payload))
                except json.JSONDecodeError as exc:
                    raise MCPError(f"Invalid MCP SSE JSON: {exc}") from exc
                data_lines = []
            continue

        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())

    if data_lines:
        payload = "\n".join(data_lines)
        try:
            messages.append(json.loads(payload))
        except json.JSONDecodeError as exc:
            raise MCPError(f"Invalid MCP SSE JSON: {exc}") from exc

    return messages


async def _read_mcp_response(response: httpx.Response) -> list[dict[str, Any]]:
    if response.is_error:
        detail = response.text[:1000]
        raise MCPError(f"MCP HTTP {response.status_code}: {detail}")

    if response.status_code in (202, 204) or not response.content.strip():
        return []

    content_type = response.headers.get("content-type", "").lower()
    if "text/event-stream" in content_type:
        return _decode_sse(response.text)

    if "application/json" in content_type:
        try:
            body = response.json()
        except json.JSONDecodeError as exc:
            raise MCPError(
                f"Invalid MCP JSON response: {response.text[:500]}"
            ) from exc
        return body if isinstance(body, list) else [body]

    raise MCPError(f"Unsupported MCP response type: {content_type or 'missing'}")


async def _mcp_post(
    client: httpx.AsyncClient,
    endpoint_url: str,
    payload: dict[str, Any],
    session_id: str | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    response = await client.post(
        endpoint_url,
        headers=headers,
        json=payload,
    )
    messages = await _read_mcp_response(response)
    returned_session_id = response.headers.get("mcp-session-id") or session_id
    return messages, returned_session_id


def _find_result(messages: list[dict[str, Any]], request_id: int) -> dict[str, Any]:
    for message in messages:
        if message.get("id") == request_id:
            if "error" in message:
                error = message["error"]
                raise MCPError(
                    f"MCP error {error.get('code')}: {error.get('message')}"
                )
            return message.get("result", {})
    raise MCPError(f"No MCP result received for request id {request_id}")


async def _call_workshop_memory_endpoint(
    endpoint_url: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    client = await get_mcp_client()

    initialize_id = 1
    initialize_payload = {
        "jsonrpc": "2.0",
        "id": initialize_id,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {
                "name": "jarvis-workshop-assistant",
                "version": "0.7.0",
            },
        },
    }

    init_messages, session_id = await _mcp_post(
        client,
        endpoint_url,
        initialize_payload,
    )
    _find_result(init_messages, initialize_id)

    await _mcp_post(
        client,
        endpoint_url,
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        },
        session_id,
    )

    call_id = 2
    call_messages, _ = await _mcp_post(
        client,
        endpoint_url,
        {
            "jsonrpc": "2.0",
            "id": call_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        },
        session_id,
    )
    result = _find_result(call_messages, call_id)

    content = result.get("content", [])
    if not content:
        return result

    text_parts = [
        item.get("text", "")
        for item in content
        if item.get("type") == "text"
    ]
    if not text_parts:
        return result

    combined = "\n".join(text_parts)
    try:
        parsed = json.loads(combined)
    except json.JSONDecodeError:
        return {"text": combined}
    return parsed if isinstance(parsed, dict) else {"result": parsed}


async def probe_workshop_memory_endpoint(endpoint_url: str) -> tuple[bool, float, str | None]:
    started = time.perf_counter()
    try:
        await _call_workshop_memory_endpoint(
            endpoint_url,
            "check_server_status",
            {},
        )
        latency_ms = (time.perf_counter() - started) * 1000
        MCP_ENDPOINT_LATENCY_MS[endpoint_url] = round(latency_ms, 2)
        return True, latency_ms, None
    except (MCPError, httpx.HTTPError, OSError, RuntimeError) as exc:
        return False, (time.perf_counter() - started) * 1000, str(exc)


async def select_workshop_memory_endpoint(force: bool = False) -> str:
    global MCP_ACTIVE_URL, MCP_LAST_ERROR, MCP_LAST_LATENCY_MS

    if MCP_ACTIVE_URL and not force:
        return MCP_ACTIVE_URL

    errors: list[str] = []
    for endpoint_url in workshop_memory_candidates():
        ok, latency_ms, error = await probe_workshop_memory_endpoint(endpoint_url)
        if ok:
            MCP_ACTIVE_URL = endpoint_url
            MCP_LAST_LATENCY_MS = round(latency_ms, 2)
            MCP_LAST_ERROR = None
            return endpoint_url
        errors.append(f"{endpoint_url}: {error}")

    MCP_ACTIVE_URL = None
    MCP_LAST_ERROR = " | ".join(errors) or "No Workshop Memory endpoint configured"
    raise MCPError(MCP_LAST_ERROR)


async def call_workshop_memory_tool(
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    global MCP_ACTIVE_URL, MCP_LAST_ERROR, MCP_LAST_LATENCY_MS, MCP_LAST_SUCCESS_AT

    cached = get_cached_mcp_result(tool_name, arguments)
    if cached is not None:
        return {**cached, "_jarvis_cache": "hit"}

    async with MCP_LOCK:
        endpoint_url = await select_workshop_memory_endpoint()
        started = time.perf_counter()

        try:
            result = await _call_workshop_memory_endpoint(
                endpoint_url,
                tool_name,
                arguments,
            )
        except (MCPError, httpx.HTTPError, OSError, RuntimeError) as first_error:
            MCP_LAST_ERROR = str(first_error)
            MCP_ACTIVE_URL = None
            endpoint_url = await select_workshop_memory_endpoint(force=True)
            started = time.perf_counter()
            result = await _call_workshop_memory_endpoint(
                endpoint_url,
                tool_name,
                arguments,
            )

        MCP_LAST_LATENCY_MS = round((time.perf_counter() - started) * 1000, 2)
        MCP_LAST_SUCCESS_AT = time.time()
        MCP_LAST_ERROR = None
        set_cached_mcp_result(tool_name, arguments, result)
        return result


def openai_error_message(response: httpx.Response) -> str:
    try:
        detail = response.json()
    except json.JSONDecodeError:
        detail = response.text[:1000]
    return f"OpenAI HTTP {response.status_code}: {detail}"


async def create_openai_response(payload: dict[str, Any]) -> dict[str, Any]:
    if not OPENAI_API_KEY:
        raise OpenAIError("OpenAI API key is not configured")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(
            OPENAI_RESPONSES_URL,
            headers=headers,
            json=payload,
        )

    if response.is_error:
        raise OpenAIError(openai_error_message(response))

    return response.json()


def response_text(response: dict[str, Any]) -> str:
    texts: list[str] = []
    for item in response.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    texts.append(content.get("text", ""))
    return "\n".join(text for text in texts if text).strip()


def function_calls(response: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in response.get("output", [])
        if item.get("type") == "function_call"
    ]


def entity_domain(entity_id: str) -> str:
    if "." not in entity_id:
        raise ValueError("Invalid Home Assistant entity ID")
    return entity_id.split(".", 1)[0]


def ensure_read_allowed(entity_id: str) -> None:
    access = effective_entity_access(entity_id)
    if access not in {"read_only", "state_only", "low_risk_control_proposed"}:
        raise PermissionError(f"Entity is not approved for Jarvis access: {entity_id}")


def ensure_control_allowed(entity_id: str) -> str:
    access = effective_entity_access(entity_id)
    if access != "low_risk_control_proposed":
        raise PermissionError(f"Entity is not approved for Jarvis control: {entity_id}")
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
    tokens = {
        token for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) >= 3 and token not in stop_words
    }
    return tokens


def find_approved_entities(query: str) -> dict[str, Any]:
    normalized = " ".join(query.lower().split())
    query_tokens = _search_tokens(normalized)
    policy = load_entity_policy()
    matches: list[dict[str, Any]] = []

    # Include legacy config whitelist entries even if no UI policy exists.
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
    ensure_read_allowed(entity_id)
    if not SUPERVISOR_TOKEN:
        raise RuntimeError("Home Assistant API token unavailable")

    try:
        state = await ha_ws.get_state(entity_id)
        if state is None:
            raise RuntimeError(f"Home Assistant entity not found: {entity_id}")
        return normalize_ha_state(state)
    except RuntimeError:
        # REST remains a resilience fallback if the persistent socket is unavailable.
        return normalize_ha_state(await ha_get_state_rest(entity_id))


async def ha_set_power(entity_id: str, turn_on: bool) -> dict[str, Any]:
    domain = ensure_control_allowed(entity_id)
    if not SUPERVISOR_TOKEN:
        raise RuntimeError("Home Assistant API token unavailable")

    service = "turn_on" if turn_on else "turn_off"
    expected = "on" if turn_on else "off"
    transport = "websocket"

    try:
        await ha_ws.call_service(
            domain,
            service,
            {"entity_id": entity_id},
        )
        verified_raw = await ha_ws.wait_for_state(entity_id, expected, timeout=5.0)
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
        "success": verified.get("state") == expected,
        "requested_action": f"{domain}.{service}",
        "entity_id": entity_id,
        "verified_state": verified.get("state"),
        "friendly_name": verified.get("friendly_name"),
        "transport": transport,
    }


async def execute_tool_calls(
    calls: list[dict[str, Any]],
    audit: list[dict[str, Any]],
    session_id: str = "default",
) -> list[dict[str, Any]]:
    tool_outputs: list[dict[str, Any]] = []
    allowed_names = {tool["name"] for tool in WORKSHOP_TOOLS}

    for call in calls:
        name = call.get("name", "")
        call_id = call.get("call_id", "")
        try:
            arguments = json.loads(call.get("arguments", "{}"))
        except json.JSONDecodeError as exc:
            raise OpenAIError(f"Invalid tool arguments for {name}") from exc

        if name not in allowed_names:
            result: dict[str, Any] = {"error": f"Tool is not allowed: {name}"}
        else:
            try:
                if name == "find_home_assistant_entities":
                    result = find_approved_entities(arguments["query"])
                elif name == "get_home_assistant_state":
                    result = await ha_get_state(arguments["entity_id"])
                elif name == "turn_on_home_assistant_entity":
                    if load_preferences()["confirmation_strictness"] == "cautious":
                        result = {"error": "Cautious mode requires explicit confirmation through the local confirmation flow."}
                    else:
                        result = await ha_set_power(arguments["entity_id"], True)
                elif name == "turn_off_home_assistant_entity":
                    if load_preferences()["confirmation_strictness"] == "cautious":
                        result = {"error": "Cautious mode requires explicit confirmation through the local confirmation flow."}
                    else:
                        result = await ha_set_power(arguments["entity_id"], False)
                elif name == "save_general_instruction":
                    result = append_general_instruction(arguments["instruction"])
                else:
                    result = await call_workshop_memory_tool(name, arguments)

                if name in {
                    "get_home_assistant_state",
                    "turn_on_home_assistant_entity",
                    "turn_off_home_assistant_entity",
                } and "error" not in result:
                    remember_session_entity(
                        session_id,
                        result.get("entity_id") or arguments["entity_id"],
                        result.get("friendly_name"),
                        result.get("verified_state") or result.get("state"),
                    )
            except (MCPError, httpx.HTTPError, RuntimeError, PermissionError, ValueError) as exc:
                result = {"error": str(exc)}

        audit.append(
            {
                "tool": name,
                "arguments": arguments,
                "success": "error" not in result,
            }
        )
        tool_outputs.append(
            {
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps(result, ensure_ascii=False),
            }
        )

    return tool_outputs


async def try_local_ha_route(
    message: str,
    session_id: str = "default",
) -> dict[str, Any] | None:
    """Execute a deterministic HA request, or return None for the model path."""
    previous_entity = get_session_entity(session_id)
    normalized = " ".join(message.lower().strip().split())
    pending = PENDING_LOW_RISK_ACTIONS.get(session_id)
    if pending and normalized in {"confirm", "yes confirm", "confirm it", "proceed"}:
        intent = pending
        PENDING_LOW_RISK_ACTIONS.pop(session_id, None)
    elif pending and normalized in {"cancel", "no", "do not", "don't"}:
        PENDING_LOW_RISK_ACTIONS.pop(session_id, None)
        return {"reply": "Cancelled. No device action was taken.", "tool_calls": []}

    elif previous_entity and is_entity_followup(message):
        intent: dict[str, Any] = {
            "kind": "control" if "turn" in normalized or "switch" in normalized else "state",
            "entity": previous_entity,
            "source": "session_reference",
        }
        if intent["kind"] == "control":
            intent["turn_on"] = " on" in f" {normalized}" and " off" not in f" {normalized}"
    else:
        parsed = parse_local_ha_intent(message)
        if not parsed:
            return None
        lookup = find_approved_entities(parsed["query"])
        entity = lookup.get("recommended_unique_match")
        if not entity:
            return None
        intent = {**parsed, "entity": entity, "source": "approved_entity_lookup"}

    entity_id = intent["entity"]["entity_id"]
    if (
        intent["kind"] == "control"
        and load_preferences()["confirmation_strictness"] == "cautious"
        and pending is not intent
    ):
        PENDING_LOW_RISK_ACTIONS[session_id] = intent
        friendly_name = intent["entity"].get("friendly_name") or entity_id
        action = "turn on" if intent["turn_on"] else "turn off"
        return {
            "reply": f"Confirm: {action} {friendly_name}? Reply “confirm” to proceed or “cancel” to stop.",
            "tool_calls": [],
        }
    if intent["kind"] == "control":
        result = await ha_set_power(entity_id, bool(intent["turn_on"]))
        state = result.get("verified_state")
        friendly_name = result.get("friendly_name") or entity_id
        remember_session_entity(session_id, entity_id, friendly_name, state)
        reply = f"{friendly_name} is now {state or ('on' if intent['turn_on'] else 'off')}."
        tool_name = (
            "turn_on_home_assistant_entity"
            if intent["turn_on"]
            else "turn_off_home_assistant_entity"
        )
    else:
        result = await ha_get_state(entity_id)
        state = result.get("state")
        friendly_name = result.get("friendly_name") or entity_id
        remember_session_entity(session_id, entity_id, friendly_name, state)
        reply = f"{friendly_name} is {state}."
        tool_name = "get_home_assistant_state"

    return {
        "reply": reply,
        "tool_calls": [{
            "tool": tool_name,
            "arguments": {"entity_id": entity_id},
            "success": True,
            "route": "local",
            "source": intent["source"],
        }],
    }


async def run_jarvis(message: str, session_id: str = "default") -> dict[str, Any]:
    local_result = await try_local_ha_route(message, session_id)
    if local_result:
        append_chat_message(session_id, "user", message)
        append_chat_message(session_id, "assistant", local_result["reply"])
        return local_result

    response = await create_openai_response(
        {
            "model": OPENAI_MODEL,
            "instructions": effective_system_instructions(),
            "input": (
                list(get_chat_history(session_id))[-chat_context_limit():]
                + (
                    [{
                        "role": "developer",
                        "content": (
                            "The current conversational device reference is "
                            + json.dumps(get_session_entity(session_id), ensure_ascii=False)
                            + ". Resolve 'it' and 'that device' to this exact entity."
                        ),
                    }]
                    if get_session_entity(session_id)
                    else []
                )
                + [{"role": "user", "content": message}]
            ),
            "tools": WORKSHOP_TOOLS,
            "tool_choice": "auto",
        }
    )

    audit: list[dict[str, Any]] = []
    max_tool_rounds = 5

    for _round in range(max_tool_rounds + 1):
        calls = function_calls(response)

        if not calls:
            text = response_text(response)
            if not text:
                raise OpenAIError("The model returned no text or function call")
            append_chat_message(session_id, "user", message)
            append_chat_message(session_id, "assistant", text)
            return {"reply": text, "tool_calls": audit}

        if _round >= max_tool_rounds:
            raise OpenAIError(
                f"Tool-call limit exceeded after {max_tool_rounds} rounds"
            )

        tool_outputs = await execute_tool_calls(calls, audit, session_id)

        response = await create_openai_response(
            {
                "model": OPENAI_MODEL,
                "instructions": effective_system_instructions(),
                "previous_response_id": response["id"],
                "input": tool_outputs,
                "tools": WORKSHOP_TOOLS,
                "tool_choice": "auto",
            }
        )

    raise OpenAIError("Jarvis tool loop ended unexpectedly")


def stream_event(event_type: str, **data: Any) -> bytes:
    payload = {"type": event_type, **data}
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")


async def stream_openai_response(payload: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
    if not OPENAI_API_KEY:
        raise OpenAIError("OpenAI API key is not configured")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    request_payload = {**payload, "stream": True}

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
        async with client.stream(
            "POST",
            OPENAI_RESPONSES_URL,
            headers=headers,
            json=request_payload,
        ) as response:
            if response.is_error:
                body = await response.aread()
                raise OpenAIError(
                    f"OpenAI HTTP {response.status_code}: "
                    f"{body.decode('utf-8', errors='replace')[:1000]}"
                )

            data_lines: list[str] = []
            async for raw_line in response.aiter_lines():
                line = raw_line.rstrip("\r")

                if not line:
                    if data_lines:
                        payload_text = "\n".join(data_lines)
                        data_lines = []
                        if payload_text == "[DONE]":
                            continue
                        try:
                            yield json.loads(payload_text)
                        except json.JSONDecodeError as exc:
                            raise OpenAIError(
                                f"Invalid OpenAI stream event: {payload_text[:500]}"
                            ) from exc
                    continue

                if line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())

            if data_lines:
                payload_text = "\n".join(data_lines)
                if payload_text != "[DONE]":
                    yield json.loads(payload_text)


async def _run_jarvis_stream_events(message: str, session_id: str = "default") -> AsyncIterator[bytes]:
    yield stream_event("status", message="Thinking…")

    local_result = await try_local_ha_route(message, session_id)
    if local_result:
        yield stream_event("status", message="Using Home Assistant…")
        reply = local_result["reply"]
        yield stream_event("status", message="Responding…")
        yield stream_event("delta", text=reply)
        yield stream_event("done", tool_calls=local_result["tool_calls"])
        return

    audit: list[dict[str, Any]] = []
    max_tool_rounds = 5
    response: dict[str, Any] | None = None
    emitted_initial_text = False

    async for event in stream_openai_response(
        {
            "model": OPENAI_MODEL,
            "instructions": effective_system_instructions(),
            "input": (
                list(get_chat_history(session_id))[-chat_context_limit():]
                + (
                    [{
                        "role": "developer",
                        "content": (
                            "The current conversational device reference is "
                            + json.dumps(get_session_entity(session_id), ensure_ascii=False)
                            + ". Resolve 'it' and 'that device' to this exact entity."
                        ),
                    }]
                    if get_session_entity(session_id)
                    else []
                )
                + [{"role": "user", "content": message}]
            ),
            "tools": WORKSHOP_TOOLS,
            "tool_choice": "auto",
        }
    ):
        event_type = event.get("type")
        if event_type == "response.output_text.delta":
            if not emitted_initial_text:
                yield stream_event("status", message="Responding…")
                emitted_initial_text = True
            delta = event.get("delta", "")
            if delta:
                yield stream_event("delta", text=delta)
        elif event_type == "response.completed":
            response = event.get("response")
        elif event_type in {"response.failed", "error"}:
            raise OpenAIError(
                event.get("message")
                or event.get("error", {}).get("message")
                or "OpenAI streaming response failed"
            )

    if response is None:
        raise OpenAIError("OpenAI stream ended without response.completed")

    if emitted_initial_text and not function_calls(response):
        yield stream_event("done", tool_calls=audit)
        return

    for round_index in range(max_tool_rounds + 1):
        calls = function_calls(response)

        if not calls:
            # The first response already contains the final text. Emit it in
            # small chunks so the UI still updates progressively.
            text = response_text(response)
            if not text:
                raise OpenAIError("The model returned no text or function call")
            yield stream_event("status", message="Responding…")
            chunk_size = 24
            for index in range(0, len(text), chunk_size):
                yield stream_event("delta", text=text[index:index + chunk_size])
            yield stream_event("done", tool_calls=audit)
            return

        if round_index >= max_tool_rounds:
            raise OpenAIError(
                f"Tool-call limit exceeded after {max_tool_rounds} rounds"
            )

        tool_names_list = [call.get("name", "unknown") for call in calls]
        tool_names = ", ".join(tool_names_list)
        local_ha_tools = {
            "find_home_assistant_entities",
            "get_home_assistant_state",
            "turn_on_home_assistant_entity",
            "turn_off_home_assistant_entity",
        }
        if all(name in local_ha_tools for name in tool_names_list):
            status_message = f"Using Home Assistant: {tool_names}…"
        else:
            status_message = f"Using tools: {tool_names}…"
        yield stream_event("status", message=status_message)

        tool_outputs = await execute_tool_calls(calls, audit, session_id)

        # Stream the next model response. If it requests more tools, collect
        # the completed response and continue the loop. If it produces text,
        # forward each output_text delta immediately.
        streamed_response: dict[str, Any] | None = None
        emitted_text = False

        async for event in stream_openai_response(
            {
                "model": OPENAI_MODEL,
                "instructions": effective_system_instructions(),
                "previous_response_id": response["id"],
                "input": tool_outputs,
                "tools": WORKSHOP_TOOLS,
                "tool_choice": "auto",
            }
        ):
            event_type = event.get("type")

            if event_type == "response.output_text.delta":
                if not emitted_text:
                    yield stream_event("status", message="Responding…")
                    emitted_text = True
                delta = event.get("delta", "")
                if delta:
                    yield stream_event("delta", text=delta)

            elif event_type == "response.completed":
                streamed_response = event.get("response")

            elif event_type in {"response.failed", "error"}:
                raise OpenAIError(
                    event.get("message")
                    or event.get("error", {}).get("message")
                    or "OpenAI streaming response failed"
                )

        if streamed_response is None:
            raise OpenAIError("OpenAI stream ended without response.completed")

        if emitted_text and not function_calls(streamed_response):
            yield stream_event("done", tool_calls=audit)
            return

        response = streamed_response

    raise OpenAIError("Jarvis streaming tool loop ended unexpectedly")


async def run_jarvis_stream(message: str, session_id: str = "default") -> AsyncIterator[bytes]:
    """Persist a completed streamed exchange while forwarding events unchanged."""
    reply_parts: list[str] = []
    completed = False
    async for event_bytes in _run_jarvis_stream_events(message, session_id):
        try:
            event = json.loads(event_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            event = {}
        if event.get("type") == "delta" and event.get("text"):
            reply_parts.append(str(event["text"]))
        elif event.get("type") == "done":
            completed = True
        yield event_bytes
    if completed and reply_parts:
        append_chat_message(session_id, "user", message)
        append_chat_message(session_id, "assistant", "".join(reply_parts))


@app.websocket("/api/chat/ws")
async def chat_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    stream_task: asyncio.Task[None] | None = None
    control_task: asyncio.Task[dict[str, Any]] | None = None

    try:
        payload = await websocket.receive_json()
        request = ChatRequest.model_validate(payload)

        async def send_stream() -> None:
            async for event_bytes in run_jarvis_stream(request.message, request.session_id):
                event_text = event_bytes.decode("utf-8").strip()
                if event_text:
                    await websocket.send_text(event_text)

        stream_task = asyncio.create_task(send_stream(), name="jarvis-response-stream")
        control_task = asyncio.create_task(websocket.receive_json(), name="jarvis-stop-listener")
        done, _pending = await asyncio.wait(
            {stream_task, control_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        if control_task in done:
            control = control_task.result()
            if control.get("type") == "stop" and not stream_task.done():
                stream_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await stream_task
                await websocket.send_json({"type": "stopped"})
        elif stream_task in done:
            await stream_task

    except WebSocketDisconnect:
        return
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        for task in (stream_task, control_task):
            if task is not None and not task.done():
                task.cancel()
        for task in (stream_task, control_task):
            if task is not None:
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task
        try:
            await websocket.close()
        except Exception:
            pass


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    async def generate() -> AsyncIterator[bytes]:
        try:
            async for event in run_jarvis_stream(request.message, request.session_id):
                yield event
        except (OpenAIError, MCPError, httpx.HTTPError) as exc:
            yield stream_event("error", message=str(exc))

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/health")
async def health() -> dict[str, Any]:
    configured_speech_provider = SPEECH_PROVIDER if SPEECH_PROVIDER in {"openai", "elevenlabs"} else "openai"
    return {
        "status": "ok",
        "version": "0.8.5",
        "home_assistant_configured": bool(SUPERVISOR_TOKEN),
        "workshop_memory_configured": bool(WORKSHOP_MEMORY_URL),
        "openai_configured": bool(OPENAI_API_KEY),
        "openai_model": OPENAI_MODEL,
        "voice_configured": bool(OPENAI_API_KEY) or bool(ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID),
        "speech_provider": configured_speech_provider,
        "speech_providers": {
            "openai": {"configured": bool(OPENAI_API_KEY)},
            "elevenlabs": {
                "configured": bool(ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID),
                "voice_name": ELEVENLABS_VOICE_NAME,
            },
        },
        "transcription_model": OPENAI_TRANSCRIPTION_MODEL,
        "tts_model": OPENAI_TTS_MODEL,
        "elevenlabs_model": ELEVENLABS_MODEL_ID,
        "ha_read_entity_count": len((await approved_ha_entities())["read_entities"]),
        "ha_control_entity_count": len((await approved_ha_entities())["control_entities"]),
    }


@app.get("/api/connections/status")
async def connections_status() -> dict[str, Any]:
    ha_status = ha_ws.status()
    return {
        "home_assistant": {
            **ha_status,
            "websocket_url": HA_WS_URL,
            "rest_fallback_url": HA_API_BASE,
        },
        "workshop_memory": {
            "active_url": MCP_ACTIVE_URL,
            "candidates": workshop_memory_candidates(),
            "last_latency_ms": MCP_LAST_LATENCY_MS,
            "endpoint_latency_ms": MCP_ENDPOINT_LATENCY_MS,
            "last_success_at_unix": MCP_LAST_SUCCESS_AT,
            "last_error": MCP_LAST_ERROR,
            "http_pool_open": bool(MCP_CLIENT and not MCP_CLIENT.is_closed),
            "cache_entries": len(MCP_TOOL_CACHE),
        },
        "openai": {
            "configured": bool(OPENAI_API_KEY),
            "model": OPENAI_MODEL,
        },
    }


@app.get("/api/memory/status")
async def memory_status() -> dict[str, Any]:
    try:
        result = await call_workshop_memory_tool("check_server_status", {})
        return {"connected": True, "result": result}
    except (MCPError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/memory/project/{project_name}")
async def memory_project(project_name: str) -> dict[str, Any]:
    try:
        result = await call_workshop_memory_tool(
            "get_project_context",
            {"project": project_name, "include_requirements": True},
        )
        return {"connected": True, "project": project_name, "result": result}
    except (MCPError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


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


@app.on_event("startup")
async def start_ha_websocket() -> None:
    load_chat_sessions()
    prune_expired_chats()
    await get_mcp_client()
    with contextlib.suppress(MCPError, httpx.HTTPError, OSError, RuntimeError):
        await select_workshop_memory_endpoint(force=True)

    if not SUPERVISOR_TOKEN:
        return
    try:
        await ha_ws.connect()
    except RuntimeError:
        # App remains available; the client reconnects lazily and REST is a fallback.
        pass

    # Apply the owner's socket/HVAC auto-approval policy without requiring the
    # Entities screen to be opened first.
    with contextlib.suppress(HTTPException, OSError, RuntimeError):
        await list_ha_entities()


@app.on_event("shutdown")
async def stop_ha_websocket() -> None:
    await ha_ws.close()
    await close_mcp_client()


@app.get("/api/chats")
async def list_chats() -> dict[str, Any]:
    chats = [
        {
            "session_id": session_id,
            "title": CHAT_SESSION_META.get(session_id, {}).get("title") or chat_title(messages),
            "updated_at": CHAT_SESSION_META.get(session_id, {}).get("updated_at", 0),
            "message_count": len(messages),
        }
        for session_id, messages in CHAT_SESSIONS.items()
    ]
    chats.sort(key=lambda item: item["updated_at"], reverse=True)
    return {"chats": chats}


@app.get("/api/settings")
async def read_settings() -> dict[str, Any]:
    instructions = load_general_instructions()
    voice = load_elevenlabs_voice_settings()
    return {
        "general_instructions": instructions,
        "max_characters": GENERAL_INSTRUCTIONS_MAX_CHARS,
        "elevenlabs_voice_settings": voice,
        "elevenlabs_voice_defaults": ELEVENLABS_VOICE_DEFAULTS,
        "preferences": load_preferences(),
        "elevenlabs_models": sorted(ELEVENLABS_MODELS),
    }


@app.put("/api/settings")
async def update_settings(request: JarvisSettingsUpdate) -> dict[str, Any]:
    if request.elevenlabs_model not in ELEVENLABS_MODELS:
        raise HTTPException(status_code=400, detail="Unsupported ElevenLabs model")
    try:
        instructions = save_general_instructions(request.general_instructions)
        voice = save_elevenlabs_voice_settings(
            {
                "stability": request.elevenlabs_stability,
                "similarity": request.elevenlabs_similarity,
                "style": request.elevenlabs_style,
                "speed": request.elevenlabs_speed,
            }
        )
        preferences = save_preferences(
            {
                "elevenlabs_model": request.elevenlabs_model,
                "elevenlabs_speaker_boost": request.elevenlabs_speaker_boost,
                "auto_speak": request.auto_speak,
                "response_length": request.response_length,
                "confirmation_strictness": request.confirmation_strictness,
                "context_messages": request.context_messages,
                "retention_days": request.retention_days,
                "preferred_language": request.preferred_language.strip() or "auto",
                "pronunciation_dictionary": request.pronunciation_dictionary.strip(),
                "theme": request.theme,
                "reduced_motion": request.reduced_motion,
                "text_size": request.text_size,
                "interface_density": request.interface_density,
                "quiet_hours_enabled": request.quiet_hours_enabled,
                "quiet_hours_start": request.quiet_hours_start,
                "quiet_hours_end": request.quiet_hours_end,
                "voice_volume": request.voice_volume,
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "saved": True,
        "general_instructions": instructions,
        "elevenlabs_voice_settings": voice,
        "preferences": preferences,
    }


@app.get("/api/settings/backup")
async def export_settings_backup() -> Response:
    backup = {
        "format": "jarvis-backup-v1",
        "created_at": time.time(),
        "settings": load_settings_payload(),
        "chats": json.loads(CHAT_STORAGE_PATH.read_text(encoding="utf-8"))
        if CHAT_STORAGE_PATH.exists() else {"version": 1, "sessions": {}},
        "entity_policy": json.loads(ENTITY_POLICY_PATH.read_text(encoding="utf-8"))
        if ENTITY_POLICY_PATH.exists() else {"version": 1, "entities": {}},
    }
    # Secrets are environment-backed and are intentionally absent from this file.
    return Response(
        json.dumps(backup, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=jarvis-backup.json"},
    )


@app.post("/api/settings/restore")
async def restore_settings_backup(request: SettingsRestoreRequest) -> dict[str, Any]:
    backup = request.backup
    if backup.get("format") != "jarvis-backup-v1":
        raise HTTPException(status_code=400, detail="Unsupported Jarvis backup format")
    settings = backup.get("settings")
    chats = backup.get("chats")
    policy = backup.get("entity_policy")
    if not isinstance(settings, dict) or not isinstance(chats, dict) or not isinstance(policy, dict):
        raise HTTPException(status_code=400, detail="Backup is missing required sections")
    if not isinstance(chats.get("sessions", {}), dict) or not isinstance(policy.get("entities", {}), dict):
        raise HTTPException(status_code=400, detail="Backup data is malformed")
    save_settings_payload(settings)
    CHAT_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHAT_STORAGE_PATH.write_text(json.dumps(chats, ensure_ascii=False, indent=2), encoding="utf-8")
    save_entity_policy(policy.get("entities", {}))
    load_chat_sessions()
    return {"restored": True, "chat_count": len(CHAT_SESSIONS)}


@app.delete("/api/chats")
async def clear_all_chats() -> dict[str, Any]:
    count = len(CHAT_SESSIONS)
    CHAT_SESSIONS.clear()
    CHAT_SESSION_ORDER.clear()
    CHAT_SESSION_META.clear()
    persist_chat_sessions()
    return {"deleted": count}


@app.post("/api/chats")
async def create_chat(request: ChatSessionCreate) -> dict[str, Any]:
    get_chat_history(request.session_id)
    persist_chat_sessions()
    return {"session_id": request.session_id, "title": "New chat"}


@app.get("/api/chat/history/{session_id}")
async def read_chat_history(session_id: str) -> dict[str, Any]:
    history = get_chat_history(session_id)
    return {
        "session_id": session_id,
        "title": CHAT_SESSION_META.get(session_id, {}).get("title") or chat_title(history),
        "messages": list(history),
    }


@app.delete("/api/chat/history/{session_id}")
async def delete_chat_history(session_id: str) -> dict[str, Any]:
    clear_chat_history(session_id)
    return {"cleared": True, "session_id": session_id}


@app.get("/api/ha/websocket-status")
async def ha_websocket_status() -> dict[str, Any]:
    status = ha_ws.status()
    if not status["connected"] and SUPERVISOR_TOKEN:
        try:
            await ha_ws.connect()
        except RuntimeError:
            pass
        status = ha_ws.status()
    return {
        **status,
        "url": HA_WS_URL,
        "rest_fallback": True,
    }


@app.get("/api/ha/approved")
async def approved_ha_entities() -> dict[str, Any]:
    policy = load_entity_policy()
    enabled = {
        entity_id: record
        for entity_id, record in policy.items()
        if record.get("enabled")
    }
    read_entities = sorted(
        entity_id for entity_id, record in enabled.items()
        if record.get("access") in {"read_only", "state_only"}
    )
    control_entities = sorted(
        entity_id for entity_id, record in enabled.items()
        if record.get("access") == "low_risk_control_proposed"
    )
    return {
        "read_entities": sorted(set(read_entities) | HA_READ_ENTITIES),
        "control_entities": sorted(set(control_entities) | HA_CONTROL_ENTITIES),
        "safe_control_domains": sorted(SAFE_CONTROL_DOMAINS),
        # Return the complete policy so aliases on disabled/unapproved entities
        # are restored when the Entities tab is opened again. Approval lists
        # above remain derived only from enabled records.
        "policy": policy,
        "policy_path": str(ENTITY_POLICY_PATH),
    }


@app.put("/api/ha/entity-policy/{entity_id:path}")
async def update_entity_policy(
    entity_id: str,
    request: EntityPolicyUpdate,
) -> dict[str, Any]:
    if "." not in entity_id:
        raise HTTPException(status_code=400, detail="Invalid entity ID")

    actual_domain = entity_domain(entity_id)
    if request.domain != actual_domain:
        raise HTTPException(status_code=400, detail="Entity domain mismatch")

    if request.enabled and request.access == "low_risk_control_proposed":
        if actual_domain not in SAFE_CONTROL_DOMAINS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Control cannot be approved for domain '{actual_domain}'. "
                    f"Allowed domains: {', '.join(sorted(SAFE_CONTROL_DOMAINS))}"
                ),
            )

    clean_aliases = []
    seen = set()
    for alias in request.aliases:
        cleaned = " ".join(alias.strip().split())
        key = cleaned.lower()
        if cleaned and key not in seen:
            clean_aliases.append(cleaned)
            seen.add(key)

    policy = load_entity_policy()
    policy[entity_id] = {
        "enabled": request.enabled,
        "friendly_name": request.friendly_name,
        "domain": request.domain,
        "device_class": request.device_class,
        "unit": request.unit,
        "access": request.access,
        "aliases": clean_aliases,
    }
    save_entity_policy(policy)

    return {
        "saved": True,
        "entity_id": entity_id,
        "effective_access": effective_entity_access(entity_id),
        "record": policy[entity_id],
        "persistent_path": str(ENTITY_POLICY_PATH),
    }


@app.get("/api/ha/entities")
async def list_ha_entities() -> dict[str, Any]:
    """
    Return a normalized read-only entity inventory from Home Assistant.

    Current states are included for interface display only. They should not be
    treated as permanent Workshop Memory data.
    """
    if not SUPERVISOR_TOKEN:
        raise HTTPException(status_code=503, detail="Home Assistant API token unavailable")

    headers = {
        "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(f"{HA_API_BASE}/states", headers=headers)

    if response.is_error:
        raise HTTPException(
            status_code=502,
            detail=f"Home Assistant returned HTTP {response.status_code}",
        )

    raw_states = response.json()
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
        entities.append(
            {
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
            }
        )

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

    entities.sort(
        key=lambda entity: (
            str(entity.get("domain", "")).lower(),
            str(entity.get("friendly_name", "")).lower(),
            str(entity.get("entity_id", "")).lower(),
        )
    )

    domains = sorted({entity["domain"] for entity in entities})

    return {
        "count": len(entities),
        "domains": domains,
        "entities": entities,
        "note": (
            "States are live Home Assistant data. Only stable metadata should "
            "later be proposed for Workshop Memory."
        ),
    }


def entity_catalog_markdown(entities: list[EntityCatalogItem]) -> str:
    lines = [
        "# Home Assistant Entity Catalog",
        "",
        "This is a review-only catalog generated by Jarvis.",
        "Live entity states are intentionally excluded.",
        "",
    ]

    for entity in sorted(entities, key=lambda item: item.entity_id):
        lines.extend(
            [
                f"## {entity.entity_id}",
                f"- Friendly name: {entity.friendly_name}",
                f"- Domain: {entity.domain}",
                f"- Device class: {entity.device_class or 'Not documented'}",
                f"- Unit: {entity.unit or 'Not applicable'}",
                f"- Jarvis access: {entity.access}",
            ]
        )
        if entity.aliases:
            lines.append("- Aliases:")
            for alias in entity.aliases:
                lines.append(f"  - {alias}")
        else:
            lines.append("- Aliases: None recorded")
        lines.append("")

    return "\n".join(lines).strip()


@app.post("/api/memory/entity-catalog-draft")
async def save_entity_catalog_draft(
    request: EntityCatalogDraftRequest,
) -> dict[str, Any]:
    """
    Save selected Home Assistant entity metadata as an unreviewed Workshop
    Memory session draft. This does not modify permanent project notes.
    """
    markdown = entity_catalog_markdown(request.entities)

    work_completed = [
        f"Reviewed {len(request.entities)} Home Assistant entities for Jarvis access.",
        "Generated a stable entity catalog without live state values.",
    ]

    decisions_proposed = [
        f"{entity.entity_id}: access={entity.access}"
        for entity in request.entities
    ]

    files_or_systems = [
        "Home Assistant entity registry/state metadata",
        "Jarvis Workshop Assistant entity access catalog",
    ]

    try:
        result = await call_workshop_memory_tool(
            "save_session_draft",
            {
                "project": request.project,
                "source": "ChatGPT",
                "session_goal": "Review Home Assistant entities for Jarvis access",
                "work_completed": work_completed,
                "decisions_proposed": decisions_proposed,
                "tests_or_observations": [
                    "Entity metadata was exported from Home Assistant.",
                    "Live states were excluded from the permanent-memory proposal.",
                ],
                "problems_and_risks": [
                    "Risk classifications are proposed and require user review.",
                    "No Home Assistant write access has been enabled.",
                ],
                "files_or_systems_affected": files_or_systems,
                "open_questions": [
                    "Which proposed low-risk controls should eventually be approved?",
                    "Which entities should remain restricted?",
                ],
                "next_actions": [
                    "Review the generated session draft in Workshop Memory.",
                    "Approve or revise entity access classifications.",
                    "Only after approval, expose selected read-only entities to Jarvis.",
                ],
            },
        )
    except (MCPError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "saved": True,
        "project": request.project,
        "entity_count": len(request.entities),
        "catalog_markdown": markdown,
        "workshop_memory_result": result,
        "permanent_project_notes_changed": False,
        "review_required": True,
    }


@app.get("/api/ha/states/{entity_id}")
async def get_ha_state(entity_id: str) -> dict[str, Any]:
    if not SUPERVISOR_TOKEN:
        raise HTTPException(status_code=503, detail="Home Assistant API token unavailable")

    headers = {
        "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{HA_API_BASE}/states/{entity_id}", headers=headers)

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Entity not found")
    if response.is_error:
        raise HTTPException(
            status_code=502,
            detail=f"Home Assistant returned HTTP {response.status_code}",
        )
    return response.json()


@app.post("/api/voice/transcribe")
async def transcribe_voice(audio: UploadFile = File(...)) -> dict[str, str]:
    """Transcribe one bounded browser microphone recording without exposing the API key."""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OpenAI API key is not configured")

    content_type = (audio.content_type or "application/octet-stream").lower()
    if not (content_type.startswith("audio/") or content_type == "video/webm"):
        raise HTTPException(status_code=415, detail="Unsupported microphone recording format")

    audio_bytes = await audio.read(VOICE_UPLOAD_MAX_BYTES + 1)
    await audio.close()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Microphone recording is empty")
    if len(audio_bytes) > VOICE_UPLOAD_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Microphone recording is too large")

    filename = audio.filename or "jarvis-recording.webm"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    files = {"file": (filename, audio_bytes, content_type)}
    data = {
        "model": OPENAI_TRANSCRIPTION_MODEL,
        "response_format": "json",
        "prompt": "Jarvis workshop assistant. Preserve Home Assistant entity names and commands.",
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=10.0)) as client:
        response = await client.post(
            OPENAI_TRANSCRIPTIONS_URL,
            headers=headers,
            data=data,
            files=files,
        )
    if response.is_error:
        raise HTTPException(
            status_code=502,
            detail=f"Voice transcription failed: {openai_error_message(response)}",
        )
    text = str(response.json().get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="No speech was recognized")
    return {"text": text, "model": OPENAI_TRANSCRIPTION_MODEL}


@app.post("/api/voice/speech")
async def generate_speech(request: SpeechRequest) -> Response:
    """Generate AI speech for playback on the browser device that requested it."""
    provider = SPEECH_PROVIDER if request.provider == "default" else request.provider
    preferences = load_preferences()
    speech_text = apply_pronunciation_dictionary(request.text)
    if provider not in {"openai", "elevenlabs"}:
        provider = "openai"

    if provider == "elevenlabs":
        if not ELEVENLABS_API_KEY or not ELEVENLABS_VOICE_ID:
            raise HTTPException(
                status_code=503,
                detail="ElevenLabs API key and voice ID are not configured",
            )
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        voice_settings = load_elevenlabs_voice_settings()
        payload = {
            "text": speech_text,
            "model_id": preferences["elevenlabs_model"],
            "voice_settings": {
                "stability": voice_settings["stability"],
                "similarity_boost": voice_settings["similarity"],
                "style": voice_settings["style"],
                "use_speaker_boost": preferences["elevenlabs_speaker_boost"],
                "speed": voice_settings["speed"],
            },
        }
        response = None
        client = httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=10.0))
        try:
            upstream_request = client.build_request(
                "POST",
                f"{ELEVENLABS_SPEECH_URL}/{ELEVENLABS_VOICE_ID}/stream",
                params={"output_format": "mp3_44100_128", "optimize_streaming_latency": "4"},
                headers=headers,
                json=payload,
            )
            response = await client.send(upstream_request, stream=True)
        except httpx.HTTPError:
            await client.aclose()
        if response is not None and not response.is_error:
            async def relay_elevenlabs_audio() -> AsyncIterator[bytes]:
                try:
                    async for chunk in response.aiter_bytes():
                        if chunk:
                            yield chunk
                finally:
                    await response.aclose()
                    await client.aclose()

            return StreamingResponse(
                relay_elevenlabs_audio(),
                media_type="audio/mpeg",
                headers={
                    "Cache-Control": "no-store",
                    "X-Jarvis-Voice": ELEVENLABS_VOICE_NAME,
                    "X-Jarvis-Speech-Provider": "elevenlabs",
                },
            )
        if response is not None:
            await response.aread()
            await response.aclose()
            await client.aclose()
        if not (SPEECH_FALLBACK_TO_OPENAI and OPENAI_API_KEY):
            detail = "ElevenLabs speech generation failed"
            with contextlib.suppress(ValueError, TypeError, AttributeError):
                error_data = response.json()
                provider_detail = error_data.get("detail")
                if isinstance(provider_detail, dict):
                    detail = str(provider_detail.get("message") or detail)
                elif provider_detail:
                    detail = str(provider_detail)
            raise HTTPException(status_code=502, detail=detail)

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OpenAI API key is not configured")
    voice = request.voice.lower().strip()
    if voice not in TTS_VOICES:
        voice = "cedar" if provider == "elevenlabs" else voice
    if voice not in TTS_VOICES:
        raise HTTPException(status_code=400, detail="Unsupported Jarvis voice")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_TTS_MODEL,
        "voice": voice,
        "input": speech_text,
        "instructions": (
            "Speak as a calm, concise workshop AI assistant. Use a measured pace "
            "and clear pronunciation. Do not add words that are not in the input."
        ),
        "response_format": "mp3",
    }
    response = None
    client = httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=10.0))
    try:
        upstream_request = client.build_request(
            "POST",
            OPENAI_SPEECH_URL,
            headers=headers,
            json=payload,
        )
        response = await client.send(upstream_request, stream=True)
    except httpx.HTTPError:
        await client.aclose()
        raise
    if response.is_error:
        await response.aread()
        await response.aclose()
        await client.aclose()
        raise HTTPException(
            status_code=502,
            detail=f"Speech generation failed: {openai_error_message(response)}",
        )

    async def relay_openai_audio() -> AsyncIterator[bytes]:
        try:
            async for chunk in response.aiter_bytes():
                if chunk:
                    yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    return StreamingResponse(
        relay_openai_audio(),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-store",
            "X-Jarvis-Voice": voice,
            "X-Jarvis-Speech-Provider": "openai",
        },
    )


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict[str, Any]:
    try:
        return await run_jarvis(request.message, request.session_id)
    except (OpenAIError, MCPError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/{path:path}", include_in_schema=False)
async def frontend(path: str = "") -> FileResponse:
    candidate = STATIC_DIR / path
    if path and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(STATIC_DIR / "index.html")
