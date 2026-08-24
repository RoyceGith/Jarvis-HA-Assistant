from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from typing import Any


load_preferences = None
is_internal_chat_session = None
active_agent_model = None
create_openai_response = None
function_calls = None


def configure_fast_memory_domain(
    *, load_preferences_fn, is_internal_chat_session_fn, active_agent_model_fn,
    create_openai_response_fn, function_calls_fn,
) -> None:
    global load_preferences, is_internal_chat_session, active_agent_model
    global create_openai_response, function_calls
    load_preferences = load_preferences_fn
    is_internal_chat_session = is_internal_chat_session_fn
    active_agent_model = active_agent_model_fn
    create_openai_response = create_openai_response_fn
    function_calls = function_calls_fn

FAST_MEMORY_PATH = Path("/data/zbrano_fast_memory.sqlite3")

FAST_MEMORY_KINDS = {
    "profile", "preference", "project", "decision", "fact",
    "follow_up", "session_summary", "temporary",
}

FAST_MEMORY_MAX_RECORDS = 800

FAST_MEMORY_CONTEXT_MAX_CHARS = 4800

FAST_MEMORY_TASKS: set[asyncio.Task[Any]] = set()

FAST_MEMORY_RUNTIME: dict[str, Any] = {
    "running": False, "last_run": 0.0, "last_error": "", "captured": 0,
}

FAST_MEMORY_STOP_WORDS = {
    "the", "and", "for", "that", "this", "with", "from", "have", "has", "had",
    "you", "your", "are", "was", "were", "will", "would", "can", "could", "about",
    "into", "then", "than", "but", "not", "all", "what", "when", "where", "which",
    "how", "why", "our", "their", "there", "here", "also", "just", "some", "any",
}

FAST_MEMORY_SECRET_RE = re.compile(
    r"(?i)(?:password|passphrase|api[_ -]?key|access[_ -]?token|refresh[_ -]?token|client[_ -]?secret|authorization)\s*[:=]|\b(?:sk|ghp|github_pat)_[A-Za-z0-9_-]{16,}"
)

def _fast_memory_connect() -> sqlite3.Connection:
    FAST_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(FAST_MEMORY_PATH), timeout=3.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute(
        """CREATE TABLE IF NOT EXISTS memory_records (
        id TEXT PRIMARY KEY,
        identity_key TEXT NOT NULL UNIQUE,
        fingerprint TEXT NOT NULL,
        kind TEXT NOT NULL,
        subject TEXT NOT NULL,
        memory_key TEXT NOT NULL,
        value TEXT NOT NULL,
        summary TEXT NOT NULL,
        keywords TEXT NOT NULL,
        importance INTEGER NOT NULL,
        confidence REAL NOT NULL,
        pinned INTEGER NOT NULL DEFAULT 0,
        source_session TEXT NOT NULL DEFAULT '',
        source_excerpt TEXT NOT NULL DEFAULT '',
        automatic INTEGER NOT NULL DEFAULT 0,
        confirmations INTEGER NOT NULL DEFAULT 1,
        revision INTEGER NOT NULL DEFAULT 1,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL,
        last_accessed REAL NOT NULL DEFAULT 0,
        expires_at REAL NOT NULL DEFAULT 0
        )"""
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_fast_memory_kind ON memory_records(kind)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_fast_memory_updated ON memory_records(updated_at DESC)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_fast_memory_expiry ON memory_records(expires_at)")
    return connection

def _fast_memory_text(value: Any, limit: int) -> str:
    return " ".join(str(value or "").strip().split())[:limit]

def _fast_memory_slug(value: Any, limit: int = 120) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", _fast_memory_text(value, limit).casefold()).strip("_")
    return cleaned[:limit] or "general"

def _fast_memory_tokens(value: Any) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9_]{2,}", str(value or "").casefold())
        if token not in FAST_MEMORY_STOP_WORDS
    }

def _fast_memory_identity(kind: str, subject: str, memory_key: str) -> str:
    return f"{kind}|{_fast_memory_slug(subject, 100)}|{_fast_memory_slug(memory_key, 100)}"

def _fast_memory_fingerprint(kind: str, subject: str, memory_key: str, value: str) -> str:
    normalized = "|".join((kind, _fast_memory_slug(subject), _fast_memory_slug(memory_key), _fast_memory_text(value, 1600).casefold()))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def _fast_memory_public(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    record = dict(row)
    try:
        keywords = json.loads(record.get("keywords") or "[]")
    except (TypeError, json.JSONDecodeError):
        keywords = []
    record["keywords"] = keywords if isinstance(keywords, list) else []
    record["pinned"] = bool(record.get("pinned"))
    record["automatic"] = bool(record.get("automatic"))
    record.pop("identity_key", None)
    record.pop("fingerprint", None)
    record["key"] = record.pop("memory_key", "")
    return record

def _fast_memory_prune() -> int:
    now = time.time()
    deleted = 0
    with _fast_memory_connect() as connection:
        cursor = connection.execute("DELETE FROM memory_records WHERE pinned=0 AND expires_at>0 AND expires_at<=?", (now,))
        deleted += max(0, cursor.rowcount)
        session_rows = connection.execute(
            "SELECT id FROM memory_records WHERE kind='session_summary' AND pinned=0 ORDER BY updated_at DESC"
        ).fetchall()
        for row in session_rows[100:]:
            connection.execute("DELETE FROM memory_records WHERE id=?", (row["id"],))
            deleted += 1
        count = int(connection.execute("SELECT COUNT(*) FROM memory_records").fetchone()[0])
        excess = max(0, count - FAST_MEMORY_MAX_RECORDS)
        if excess:
            rows = connection.execute(
                "SELECT id FROM memory_records WHERE pinned=0 ORDER BY importance ASC, confidence ASC, confirmations ASC, updated_at ASC LIMIT ?",
                (excess,),
            ).fetchall()
            for row in rows:
                connection.execute("DELETE FROM memory_records WHERE id=?", (row["id"],))
                deleted += 1
    return deleted

def upsert_fast_memory(payload: dict[str, Any], *, source_session: str = "", automatic: bool = False) -> dict[str, Any]:
    kind = _fast_memory_text(payload.get("kind"), 40).casefold()
    if kind not in FAST_MEMORY_KINDS:
        raise ValueError("Unsupported Fast Memory type")
    subject = _fast_memory_text(payload.get("subject"), 160)
    memory_key = _fast_memory_slug(payload.get("key"), 120)
    value = _fast_memory_text(payload.get("value"), 1600)
    summary = _fast_memory_text(payload.get("summary") or value, 500)
    keywords = sorted({_fast_memory_text(item, 60).casefold() for item in payload.get("keywords", []) if _fast_memory_text(item, 60)})[:20]
    importance = max(1, min(5, int(payload.get("importance") or 3)))
    confidence = max(0.0, min(1.0, float(payload.get("confidence") if payload.get("confidence") is not None else 1.0)))
    pinned = bool(payload.get("pinned"))
    expires_at = max(0.0, float(payload.get("expires_at") or 0))
    if not subject or not value:
        raise ValueError("Fast Memory subject and value are required")
    if automatic and kind != "session_summary" and (importance < 3 or confidence < 0.72):
        return {"saved": False, "reason": "below_quality_threshold"}
    if FAST_MEMORY_SECRET_RE.search(f"{memory_key} {value}"):
        return {"saved": False, "reason": "credential_like_content_blocked"}
    now = time.time()
    identity = _fast_memory_identity(kind, subject, memory_key)
    fingerprint = _fast_memory_fingerprint(kind, subject, memory_key, value)
    record_id = hashlib.sha256(f"{identity}:{now}:{os.urandom(8).hex()}".encode()).hexdigest()[:24]
    excerpt = _fast_memory_text(payload.get("source_excerpt"), 260)
    action = "created"
    with _fast_memory_connect() as connection:
        existing = connection.execute(
            "SELECT * FROM memory_records WHERE identity_key=? OR fingerprint=? ORDER BY identity_key=? DESC LIMIT 1",
            (identity, fingerprint, identity),
        ).fetchone()
        if not existing:
            incoming_tokens = _fast_memory_tokens(f"{value} {summary}")
            candidates = connection.execute(
                "SELECT * FROM memory_records WHERE kind=? ORDER BY updated_at DESC LIMIT 100", (kind,),
            ).fetchall()
            for candidate in candidates:
                if _fast_memory_slug(candidate["subject"], 100) != _fast_memory_slug(subject, 100):
                    continue
                candidate_tokens = _fast_memory_tokens(f"{candidate['value']} {candidate['summary']}")
                union = incoming_tokens | candidate_tokens
                similarity = len(incoming_tokens & candidate_tokens) / len(union) if union else 0.0
                if similarity >= 0.82:
                    existing = candidate
                    break
        if existing:
            record_id = str(existing["id"])
            same_value = _fast_memory_text(existing["value"], 1600).casefold() == value.casefold()
            action = "confirmed" if same_value else "updated"
            connection.execute(
                """UPDATE memory_records SET identity_key=?, fingerprint=?, kind=?, subject=?, memory_key=?, value=?, summary=?, keywords=?,
                importance=?, confidence=?, pinned=?, source_session=?, source_excerpt=?, automatic=?, confirmations=?, revision=?, updated_at=?, expires_at=? WHERE id=?""",
                (
                    identity, fingerprint, kind, subject, memory_key, value, summary,
                    json.dumps(keywords, ensure_ascii=False), max(importance, int(existing["importance"])) if same_value else importance,
                    max(confidence, float(existing["confidence"])) if same_value else confidence,
                    int(pinned or bool(existing["pinned"])), source_session or str(existing["source_session"]),
                    excerpt or str(existing["source_excerpt"]), int(automatic and bool(existing["automatic"])),
                    int(existing["confirmations"]) + 1 if same_value else 1,
                    int(existing["revision"]) if same_value else int(existing["revision"]) + 1,
                    now, expires_at, record_id,
                ),
            )
        else:
            connection.execute(
                """INSERT INTO memory_records
                (id,identity_key,fingerprint,kind,subject,memory_key,value,summary,keywords,importance,confidence,pinned,source_session,source_excerpt,automatic,confirmations,revision,created_at,updated_at,last_accessed,expires_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    record_id, identity, fingerprint, kind, subject, memory_key, value, summary,
                    json.dumps(keywords, ensure_ascii=False), importance, confidence, int(pinned), source_session,
                    excerpt, int(automatic), 1, 1, now, now, 0.0, expires_at,
                ),
            )
        row = connection.execute("SELECT * FROM memory_records WHERE id=?", (record_id,)).fetchone()
    _fast_memory_prune()
    return {"saved": True, "action": action, "memory": _fast_memory_public(row)}

def fast_memory_search(query: str = "", *, kind: str = "", limit: int = 20, session_id: str = "") -> dict[str, Any]:
    _fast_memory_prune()
    query = _fast_memory_text(query, 300)
    kind = _fast_memory_text(kind, 40).casefold()
    if kind and kind not in FAST_MEMORY_KINDS:
        raise ValueError("Unsupported Fast Memory type")
    now = time.time()
    with _fast_memory_connect() as connection:
        sql = "SELECT * FROM memory_records WHERE (expires_at=0 OR expires_at>?)"
        values: list[Any] = [now]
        if kind:
            sql += " AND kind=?"
            values.append(kind)
        rows = connection.execute(sql, values).fetchall()
    query_tokens = _fast_memory_tokens(query)
    scored: list[tuple[float, sqlite3.Row]] = []
    for row in rows:
        subject_tokens = _fast_memory_tokens(row["subject"])
        key_tokens = _fast_memory_tokens(row["memory_key"])
        text_tokens = _fast_memory_tokens(f"{row['value']} {row['summary']} {row['keywords']}")
        overlap = len(query_tokens & text_tokens)
        subject_overlap = len(query_tokens & subject_tokens)
        key_overlap = len(query_tokens & key_tokens)
        baseline = 1.3 if session_id and row["kind"] in {"profile", "preference"} and int(row["importance"]) >= 4 else 0.0
        if row["kind"] == "session_summary" and str(row["source_session"]) == session_id:
            baseline += 3.0
        if query_tokens and overlap + subject_overlap + key_overlap == 0 and baseline == 0:
            continue
        age_days = max(0.0, (now - float(row["updated_at"])) / 86400.0)
        recency = max(0.0, 1.5 - min(age_days, 180.0) / 120.0)
        score = overlap * 2.5 + subject_overlap * 4.0 + key_overlap * 3.0 + int(row["importance"]) * 0.7 + float(row["confidence"]) + recency + baseline + (4.0 if row["pinned"] else 0.0)
        scored.append((score, row))
    scored.sort(key=lambda item: (item[0], float(item[1]["updated_at"])), reverse=True)
    selected = scored[:max(1, min(int(limit), 100))]
    if selected:
        with _fast_memory_connect() as connection:
            connection.executemany("UPDATE memory_records SET last_accessed=? WHERE id=?", [(now, row["id"]) for _, row in selected])
    return {"query": query, "count": len(selected), "memories": [_fast_memory_public(row) for _, row in selected]}

def fast_memory_status() -> dict[str, Any]:
    _fast_memory_prune()
    with _fast_memory_connect() as connection:
        total = int(connection.execute("SELECT COUNT(*) FROM memory_records").fetchone()[0])
        grouped = {str(row["kind"]): int(row["count"]) for row in connection.execute("SELECT kind,COUNT(*) AS count FROM memory_records GROUP BY kind")}
        pinned = int(connection.execute("SELECT COUNT(*) FROM memory_records WHERE pinned=1").fetchone()[0])
    return {
        "operational": True, "total": total, "pinned": pinned, "by_kind": grouped,
        "database_bytes": FAST_MEMORY_PATH.stat().st_size if FAST_MEMORY_PATH.exists() else 0,
        "max_records": FAST_MEMORY_MAX_RECORDS, "runtime": dict(FAST_MEMORY_RUNTIME),
    }

def delete_fast_memory(memory_id: str) -> bool:
    with _fast_memory_connect() as connection:
        cursor = connection.execute("DELETE FROM memory_records WHERE id=?", (_fast_memory_text(memory_id, 64),))
        return cursor.rowcount > 0

def forget_fast_memory(query: str) -> dict[str, Any]:
    matches = fast_memory_search(query, limit=100).get("memories", [])
    deleted = 0
    for memory in matches:
        if delete_fast_memory(str(memory.get("id") or "")):
            deleted += 1
    return {"deleted": deleted, "query": query}

def export_fast_memory() -> dict[str, Any]:
    with _fast_memory_connect() as connection:
        rows = connection.execute("SELECT * FROM memory_records ORDER BY updated_at DESC").fetchall()
    return {"version": 1, "memories": [_fast_memory_public(row) for row in rows]}

def restore_fast_memory(payload: dict[str, Any]) -> int:
    memories = payload.get("memories") if isinstance(payload, dict) else None
    if not isinstance(memories, list):
        raise ValueError("Fast Memory backup data is malformed")
    with _fast_memory_connect() as connection:
        connection.execute("DELETE FROM memory_records")
    restored = 0
    for item in memories[:FAST_MEMORY_MAX_RECORDS]:
        if not isinstance(item, dict):
            continue
        try:
            result = upsert_fast_memory(item, source_session=str(item.get("source_session") or ""), automatic=bool(item.get("automatic")))
            restored += int(bool(result.get("saved")))
        except (TypeError, ValueError):
            continue
    return restored

def fast_memory_context(message: str, session_id: str) -> str:
    preferences = load_preferences()
    if not preferences.get("fast_memory_enabled", True):
        return ""
    limit = max(2, min(20, int(preferences.get("fast_memory_context_items", 10) or 10)))
    memories = fast_memory_search(message, limit=limit, session_id=session_id).get("memories", [])
    lines: list[str] = []
    size = 0
    for memory in memories:
        line = f"- [{memory['kind']}] {memory['subject']} / {memory['key']}: {memory['summary'] or memory['value']}"
        if size + len(line) > FAST_MEMORY_CONTEXT_MAX_CHARS:
            break
        lines.append(line)
        size += len(line)
    if not lines:
        return ""
    return (
        "FAST MEMORY (local, concise, user-editable context). Use only when relevant. "
        "If it conflicts with the user's current statement, trust the current statement and update memory.\n"
        + "\n".join(lines)
    )

def fast_memory_input(message: str, session_id: str) -> list[dict[str, str]]:
    context = fast_memory_context(message, session_id)
    return [{"role": "developer", "content": context}] if context else []

def _fast_memory_exchange_eligible(session_id: str, user_text: str, assistant_text: str) -> bool:
    if is_internal_chat_session(session_id) or not load_preferences().get("fast_memory_auto_capture", True):
        return False
    normalized = " ".join(user_text.casefold().split())
    if len(normalized) < 12 or normalized in {"approve", "approved", "cancel", "yes", "no", "ok", "thanks", "thank you"}:
        return False
    blocked = ("reply **approve**", "permission required", "request failed:", "tool-call limit")
    return not any(marker in assistant_text.casefold() for marker in blocked)

async def extract_fast_memory_from_exchange(session_id: str, user_text: str, assistant_text: str) -> None:
    if not _fast_memory_exchange_eligible(session_id, user_text, assistant_text):
        return
    FAST_MEMORY_RUNTIME.update(running=True, last_error="")
    try:
        previous = fast_memory_search("", kind="session_summary", limit=100).get("memories", [])
        previous_summary = next((item.get("value", "") for item in previous if item.get("source_session") == session_id), "")
        extractor_tool = {
            "type": "function", "name": "record_fast_memory_batch",
            "description": "Return only durable, useful memory extracted from the completed conversation exchange.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_summary": {"type": "string", "description": "Updated rolling session summary in at most 420 characters."},
                    "memories": {
                        "type": "array", "maxItems": 6,
                        "items": {
                            "type": "object",
                            "properties": {
                                "kind": {"type": "string", "enum": ["profile", "preference", "project", "decision", "fact", "follow_up", "temporary"]},
                                "subject": {"type": "string"}, "key": {"type": "string"}, "value": {"type": "string"},
                                "summary": {"type": "string"}, "keywords": {"type": "array", "items": {"type": "string"}},
                                "importance": {"type": "integer", "minimum": 1, "maximum": 5},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                "expiry_days": {"type": "integer", "minimum": 0, "maximum": 365},
                            },
                            "required": ["kind", "subject", "key", "value", "summary", "keywords", "importance", "confidence", "expiry_days"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["session_summary", "memories"], "additionalProperties": False,
            },
            "strict": True,
        }
        response = await create_openai_response({
            "model": active_agent_model(),
            "instructions": (
                "Extract compact Fast Memory. Save only durable user facts, preferences, project state, accepted decisions, and real follow-ups. "
                "Never save credentials, access tokens, private keys, raw transcripts, tool chatter, speculative assistant claims, greetings, or trivial details. "
                "A memory must be explicitly stated or clearly confirmed by the user. Use stable snake_case keys so later updates replace earlier values. "
                "Importance 3 is useful, 4 is important, 5 is identity-critical. Confidence must be at least 0.72 to save. "
                "Temporary information needs expiry_days. Update the rolling summary rather than repeating the whole conversation."
            ),
            "input": [{"role": "user", "content": json.dumps({
                "previous_session_summary": previous_summary[:420],
                "user": _fast_memory_text(user_text, 4000),
                "assistant": _fast_memory_text(assistant_text, 4000),
            }, ensure_ascii=False)}],
            "tools": [extractor_tool],
            "tool_choice": {"type": "function", "name": "record_fast_memory_batch"},
            "max_output_tokens": 1200,
        })
        calls = function_calls(response)
        if not calls:
            return
        arguments = json.loads(calls[0].get("arguments") or "{}")
        captured = 0
        summary = _fast_memory_text(arguments.get("session_summary"), 420)
        if summary:
            result = upsert_fast_memory({
                "kind": "session_summary", "subject": session_id, "key": "rolling_summary",
                "value": summary, "summary": summary, "keywords": [], "importance": 2,
                "confidence": 1.0, "pinned": False, "expires_at": 0,
                "source_excerpt": _fast_memory_text(user_text, 260),
            }, source_session=session_id, automatic=True)
            captured += int(bool(result.get("saved")))
        for item in arguments.get("memories", [])[:6]:
            if not isinstance(item, dict):
                continue
            expiry_days = max(0, min(365, int(item.pop("expiry_days", 0) or 0)))
            item["expires_at"] = time.time() + expiry_days * 86400 if expiry_days else 0
            item["source_excerpt"] = _fast_memory_text(user_text, 260)
            result = upsert_fast_memory(item, source_session=session_id, automatic=True)
            captured += int(bool(result.get("saved")))
        FAST_MEMORY_RUNTIME["captured"] = int(FAST_MEMORY_RUNTIME.get("captured", 0)) + captured
        FAST_MEMORY_RUNTIME["last_run"] = time.time()
    except Exception as exc:
        FAST_MEMORY_RUNTIME["last_error"] = str(exc)[:500]
        FAST_MEMORY_RUNTIME["last_run"] = time.time()
    finally:
        FAST_MEMORY_RUNTIME["running"] = False

def schedule_fast_memory_extraction(session_id: str, user_text: str, assistant_text: str) -> None:
    if not _fast_memory_exchange_eligible(session_id, user_text, assistant_text):
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    task = loop.create_task(extract_fast_memory_from_exchange(session_id, user_text, assistant_text), name="zbrano-fast-memory")
    FAST_MEMORY_TASKS.add(task)
    task.add_done_callback(FAST_MEMORY_TASKS.discard)
