from __future__ import annotations

from collections import deque
import contextlib
import json
from pathlib import Path
import re
import shutil
import time
from typing import Any


load_preferences = None
chat_context_limit = None
schedule_fast_memory_extraction = None


def configure_conversations_domain(
    *, load_preferences_fn, chat_context_limit_fn, schedule_fast_memory_extraction_fn,
) -> None:
    global load_preferences, chat_context_limit, schedule_fast_memory_extraction
    load_preferences = load_preferences_fn
    chat_context_limit = chat_context_limit_fn
    schedule_fast_memory_extraction = schedule_fast_memory_extraction_fn

CHAT_HISTORY_MAX_MESSAGES = 200

CHAT_CONTEXT_MAX_MESSAGES = 20

CHAT_SESSIONS_MAX = 100

CHAT_SESSIONS: dict[str, deque[dict[str, Any]]] = {}

CHAT_SESSION_ORDER: deque[str] = deque(maxlen=CHAT_SESSIONS_MAX)

CHAT_SESSION_META: dict[str, dict[str, Any]] = {}

CHAT_STORAGE_PATH = Path("/data/chat_sessions.json")

CHAT_UPLOAD_ROOT=Path("/data/uploads")

LAST_ENTITY_BY_SESSION: dict[str, dict[str, Any]] = {}

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

INTERNAL_CHAT_SESSION_PREFIXES = ("zbrano-diagnostic-", "zbrano-playwright-")

def is_internal_chat_session(session_id: str) -> bool:
    normalized = str(session_id or "").strip().lower()
    return any(normalized.startswith(prefix) for prefix in INTERNAL_CHAT_SESSION_PREFIXES)

def purge_internal_chat_sessions() -> int:
    internal = [
        session_id for session_id in CHAT_SESSIONS
        if is_internal_chat_session(session_id)
    ]
    for session_id in internal:
        CHAT_SESSIONS.pop(session_id, None)
        CHAT_SESSION_META.pop(session_id, None)
        LAST_ENTITY_BY_SESSION.pop(session_id, None)
        with contextlib.suppress(ValueError):
            CHAT_SESSION_ORDER.remove(session_id)
    if internal:
        persist_chat_sessions()
    return len(internal)

def persist_chat_sessions() -> None:
    CHAT_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "sessions": {
            session_id: {
                "title": CHAT_SESSION_META.get(session_id, {}).get("title")
                or chat_title(messages),
                "updated_at": CHAT_SESSION_META.get(session_id, {}).get("updated_at", 0),
                "auto_speak": CHAT_SESSION_META.get(session_id, {}).get("auto_speak"),
                "messages": list(messages),
            }
            for session_id, messages in CHAT_SESSIONS.items()
            if not is_internal_chat_session(session_id)
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
    removed_internal = False
    for session_id, record in ordered:
        if is_internal_chat_session(session_id):
            removed_internal = True
            continue
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
            "auto_speak": record.get("auto_speak") if isinstance(record.get("auto_speak"), bool) else None,
        }
    if removed_internal:
        persist_chat_sessions()

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
    internal = is_internal_chat_session(session_id)
    if session_id not in CHAT_SESSIONS:
        if not internal and len(CHAT_SESSIONS) >= CHAT_SESSIONS_MAX and CHAT_SESSION_ORDER:
            oldest = CHAT_SESSION_ORDER.popleft()
            CHAT_SESSIONS.pop(oldest, None)
            CHAT_SESSION_META.pop(oldest, None)
        CHAT_SESSIONS[session_id] = deque(maxlen=CHAT_HISTORY_MAX_MESSAGES)
        if not internal:
            CHAT_SESSION_ORDER.append(session_id)
        CHAT_SESSION_META[session_id] = {"title": "New chat", "updated_at": time.time()}
    return CHAT_SESSIONS[session_id]

ATTACHMENT_CONTEXT_MARKER = "\n\n--- Attached file context ---\n"

ATTACHMENT_HEADER_RE = re.compile(
    r"^File: (?P<name>.+) \(id=(?P<file_id>[a-f0-9]{24}), scope=(?P<scope>[^,]+), type=(?P<mime_type>[^,]+), bytes=(?P<size>\d+)\)$",
    re.MULTILINE,
)

def _attachment_message_parts(content: str) -> tuple[str, list[dict[str, Any]]]:
    if ATTACHMENT_CONTEXT_MARKER not in content:
        return content, []
    visible, context = content.split(ATTACHMENT_CONTEXT_MARKER, 1)
    attachments = []
    for match in ATTACHMENT_HEADER_RE.finditer(context):
        attachments.append({
            "file_id": match.group("file_id"),
            "name": match.group("name"),
            "scope": match.group("scope"),
            "mime_type": match.group("mime_type"),
            "size": int(match.group("size")),
        })
    return visible.rstrip(), attachments

def public_chat_message(message: dict[str, Any]) -> dict[str, Any]:
    content = str(message.get("content") or "")
    visible, parsed_attachments = _attachment_message_parts(content)
    attachments = message.get("attachments")
    return {
        "role": str(message.get("role") or "assistant"),
        "content": visible,
        "attachments": attachments if isinstance(attachments, list) else parsed_attachments,
    }

def model_chat_history(session_id: str) -> list[dict[str, str]]:
    history = list(get_chat_history(session_id))
    history = history[-chat_context_limit():]
    return [
        {
            "role": str(message.get("role") or "user"),
            "content": str(message.get("model_content") or message.get("content") or ""),
        }
        for message in history
    ]

def append_chat_message(session_id: str, role: str, content: str) -> None:
    if not content:
        return
    history = get_chat_history(session_id)
    record: dict[str, Any] = {"role": role, "content": content}
    if role == "user":
        visible, attachments = _attachment_message_parts(content)
        if attachments:
            record["content"] = visible
            record["model_content"] = content
            record["attachments"] = attachments
    history.append(record)
    CHAT_SESSION_META[session_id] = {
        "title": chat_title(history),
        "updated_at": time.time(),
        "auto_speak": CHAT_SESSION_META.get(session_id, {}).get("auto_speak"),
    }
    persist_chat_sessions()
    if role == "assistant" and len(history) >= 2 and history[-2].get("role") == "user":
        schedule_fast_memory_extraction(
            session_id,
            str(history[-2].get("model_content") or history[-2].get("content") or ""),
            content,
        )

def clear_chat_history(session_id: str) -> None:
    CHAT_SESSIONS.pop(session_id, None)
    LAST_ENTITY_BY_SESSION.pop(session_id, None)
    CHAT_SESSION_META.pop(session_id, None)
    try:
        CHAT_SESSION_ORDER.remove(session_id)
    except ValueError:
        pass
    shutil.rmtree(CHAT_UPLOAD_ROOT / re.sub(r"[^A-Za-z0-9_.-]", "_", session_id)[:128], ignore_errors=True)
    persist_chat_sessions()
