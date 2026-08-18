import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.74 expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(backend, "import socket\n", "import socket\nimport sqlite3\n", "sqlite import")
    backend = replace_once(
        backend,
        '''    "web_search_context_size": "medium",
}''',
        '''    "web_search_context_size": "medium",
    "fast_memory_enabled": True,
    "fast_memory_auto_capture": True,
    "fast_memory_context_items": 10,
}''',
        "fast memory preference defaults",
    )

    models = r'''class FastMemoryWriteRequest(BaseModel):
    kind: str = Field(pattern="^(profile|preference|project|decision|fact|follow_up|session_summary|temporary)$")
    subject: str = Field(min_length=1, max_length=160)
    key: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=1600)
    summary: str = Field(default="", max_length=500)
    keywords: list[str] = Field(default_factory=list, max_length=20)
    importance: int = Field(default=3, ge=1, le=5)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    pinned: bool = False
    expires_at: float = Field(default=0, ge=0)


class FastMemoryForgetRequest(BaseModel):
    query: str = Field(min_length=2, max_length=300)


'''
    backend = replace_once(
        backend,
        "class SettingsRestoreRequest(BaseModel):\n",
        models + "class SettingsRestoreRequest(BaseModel):\n",
        "fast memory request models",
    )
    backend = replace_once(
        backend,
        '''    web_search_context_size: str = Field(default="medium", pattern="^(low|medium|high)$")
''',
        '''    web_search_context_size: str = Field(default="medium", pattern="^(low|medium|high)$")
    fast_memory_enabled: bool = True
    fast_memory_auto_capture: bool = True
    fast_memory_context_items: int = Field(default=10, ge=2, le=20)
''',
        "fast memory settings model",
    )

    memory_backend = r'''FAST_MEMORY_PATH = Path("/data/zbrano_fast_memory.sqlite3")
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


'''
    backend = replace_once(
        backend,
        "def append_chat_message(session_id: str, role: str, content: str) -> None:\n",
        memory_backend + "def append_chat_message(session_id: str, role: str, content: str) -> None:\n",
        "fast memory backend",
    )
    backend = replace_once(
        backend,
        '''    persist_chat_sessions()


def clear_chat_history(session_id: str) -> None:''',
        '''    persist_chat_sessions()
    if role == "assistant" and len(history) >= 2 and history[-2].get("role") == "user":
        schedule_fast_memory_extraction(
            session_id,
            str(history[-2].get("model_content") or history[-2].get("content") or ""),
            content,
        )


def clear_chat_history(session_id: str) -> None:''',
        "background extraction hook",
    )

    memory_tools = r'''    {
        "type": "function",
        "name": "remember_fast_memory",
        "description": "Save or update one concise local Fast Memory when the user explicitly asks ZBRANO to remember it. Existing type/subject/key records are updated instead of duplicated.",
        "parameters": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["profile", "preference", "project", "decision", "fact", "follow_up", "temporary"]},
                "subject": {"type": "string"}, "key": {"type": "string"}, "value": {"type": "string"},
                "summary": {"type": "string"}, "keywords": {"type": "array", "items": {"type": "string"}},
                "importance": {"type": "integer", "minimum": 1, "maximum": 5},
                "expires_at": {"type": "number", "description": "Unix expiry timestamp or 0 for permanent."}
            },
            "required": ["kind", "subject", "key", "value", "summary", "keywords", "importance", "expires_at"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "search_fast_memory",
        "description": "Search ZBRANO's fast local memory for profile, preference, project, decision, fact, follow-up, and session-summary context.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"},
            "kind": {"type": "string", "enum": ["", "profile", "preference", "project", "decision", "fact", "follow_up", "session_summary", "temporary"]},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50}
        }, "required": ["query", "kind", "limit"], "additionalProperties": False},
        "strict": True
    },
    {
        "type": "function",
        "name": "forget_fast_memory",
        "description": "Delete matching Fast Memory only when the user explicitly asks ZBRANO to forget or remove that remembered information.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": False},
        "strict": True
    },
'''
    backend = replace_once(
        backend,
        '''    {
        "type": "function",
        "name": "save_general_instruction",''',
        memory_tools + '''    {
        "type": "function",
        "name": "save_general_instruction",''',
        "fast memory chat tools",
    )
    backend = replace_once(
        backend,
        '''                elif name == "save_general_instruction":
                    result = append_general_instruction(arguments["instruction"])''',
        '''                elif name == "remember_fast_memory":
                    arguments["confidence"] = 1.0
                    arguments["pinned"] = bool(arguments.get("importance", 3) >= 5)
                    result = upsert_fast_memory(arguments, source_session=session_id, automatic=False)
                elif name == "search_fast_memory":
                    result = fast_memory_search(arguments.get("query", ""), kind=arguments.get("kind", ""), limit=arguments.get("limit", 20), session_id=session_id)
                elif name == "forget_fast_memory":
                    result = forget_fast_memory(arguments.get("query", ""))
                elif name == "save_general_instruction":
                    result = append_general_instruction(arguments["instruction"])''',
        "fast memory tool execution",
    )
    backend = replace_once(
        backend,
        '''    if tool_names and all(name in local_ha for name in tool_names):
        return {"label": "Reading Home Assistant", "provider": "home_assistant", "plugin_id": ""}''',
        '''    if tool_names and all(name in local_ha for name in tool_names):
        return {"label": "Reading Home Assistant", "provider": "home_assistant", "plugin_id": ""}
    if tool_names and all(name in {"remember_fast_memory", "search_fast_memory", "forget_fast_memory"} for name in tool_names):
        writing_memory = any(name != "search_fast_memory" for name in tool_names)
        return {"label": "Updating Fast Memory" if writing_memory else "Reading Fast Memory", "provider": "fast_memory", "plugin_id": ""}''',
        "fast memory activity",
    )

    backend = replace_once(
        backend,
        r'''        "USER RESPONSE PREFERENCES (never override safety policy):\n"
        f"- {response_guidance}\n- {confirmation_guidance}\n- {language_guidance}\n- {formatting_guidance}",
    ]''',
        r'''        "USER RESPONSE PREFERENCES (never override safety policy):\n"
        f"- {response_guidance}\n- {confirmation_guidance}\n- {language_guidance}\n- {formatting_guidance}",
        "FAST MEMORY POLICY:\n"
        "- Fast Memory is compact local working context, not the authoritative long-form project archive.\n"
        "- Use supplied Fast Memory when relevant, but trust the user's current statement over an older record.\n"
        "- Call remember_fast_memory immediately when the user explicitly asks to remember a durable fact or preference.\n"
        "- Call search_fast_memory when the user asks what ZBRANO remembers or when supplied context is insufficient.\n"
        "- Call forget_fast_memory only after an explicit request to forget matching local memories.\n"
        "- Keep detailed project documents and accepted technical records in Workshop Memory.",
    ]''',
        "fast memory system policy",
    )
    count = backend.count("model_chat_history(session_id)\n                + (")
    if count != 2:
        raise RuntimeError(f"ZBRANO v0.12.74 expected two initial chat context markers; found {count}")
    backend = backend.replace(
        "model_chat_history(session_id)\n                + (",
        "model_chat_history(session_id)\n                + fast_memory_input(message, session_id)\n                + (",
    )

    priority = r'''
FAST_MEMORY_INTENT_TERMS = (
    "remember this", "remember that", "remember my", "remember i", "fast memory",
    "what do you remember", "what do you know about me", "forget this", "forget that",
    "forget what", "forget about", "remove this memory", "save this to memory",
    "keep this in memory", "remember for later", "personal profile", "memory profile",
)


def is_fast_memory_intent(message: str) -> bool:
    normalized = " ".join(str(message or "").casefold().split())
    if "workshop memory" in normalized:
        return False
    return any(term in normalized for term in FAST_MEMORY_INTENT_TERMS)


def fast_memory_priority_tools() -> list[dict[str, Any]]:
    names = {"remember_fast_memory", "search_fast_memory", "forget_fast_memory"}
    return [tool for tool in WORKSHOP_TOOLS if str(tool.get("name") or "") in names]


'''
    backend = replace_once(
        backend,
        "def runtime_chat_tools(search_mode: str = \"auto\", message: str = \"\") -> list[dict[str, Any]]:\n",
        priority + "def runtime_chat_tools(search_mode: str = \"auto\", message: str = \"\") -> list[dict[str, Any]]:\n",
        "fast memory priority routing",
    )
    backend = replace_once(
        backend,
        '''    if is_grinder_diagnostic_intent(message):
        return grinder_priority_tools()
    if is_calendar_intent(message):''',
        '''    if is_grinder_diagnostic_intent(message):
        return grinder_priority_tools()
    if is_fast_memory_intent(message):
        return fast_memory_priority_tools()
    if is_calendar_intent(message):''',
        "fast memory priority tool selection",
    )

    memory_api = r'''@app.get("/api/fast-memory")
async def read_fast_memory(query: str = "", kind: str = "", limit: int = 100) -> dict[str, Any]:
    result = fast_memory_search(query, kind=kind, limit=limit)
    result["status"] = fast_memory_status()
    return result


@app.post("/api/fast-memory")
async def create_fast_memory(request: FastMemoryWriteRequest) -> dict[str, Any]:
    return upsert_fast_memory(request.model_dump(), automatic=False)


@app.put("/api/fast-memory/{memory_id}")
async def update_fast_memory(memory_id: str, request: FastMemoryWriteRequest) -> dict[str, Any]:
    with _fast_memory_connect() as connection:
        existing = connection.execute("SELECT id FROM memory_records WHERE id=?", (memory_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Fast Memory record not found")
    result = upsert_fast_memory(request.model_dump(), automatic=False)
    replacement_id = str((result.get("memory") or {}).get("id") or "")
    if replacement_id and replacement_id != memory_id:
        delete_fast_memory(memory_id)
    return result


@app.delete("/api/fast-memory/{memory_id}")
async def remove_fast_memory(memory_id: str) -> dict[str, Any]:
    return {"deleted": delete_fast_memory(memory_id), "id": memory_id}


@app.post("/api/fast-memory/forget")
async def forget_fast_memory_api(request: FastMemoryForgetRequest) -> dict[str, Any]:
    return forget_fast_memory(request.query)


'''
    backend = replace_once(
        backend,
        '@app.get("/api/settings/backup")\n',
        memory_api + '@app.get("/api/settings/backup")\n',
        "fast memory API",
    )
    backend = replace_once(
        backend,
        '''        "calendar": calendar_store(),
    }''',
        '''        "calendar": calendar_store(),
        "fast_memory": export_fast_memory(),
    }''',
        "fast memory backup export",
    )
    backend = replace_once(
        backend,
        '''    calendar = backup.get("calendar")
    if not isinstance(settings, dict)''',
        '''    calendar = backup.get("calendar")
    fast_memory = backup.get("fast_memory")
    if not isinstance(settings, dict)''',
        "fast memory backup input",
    )
    backend = replace_once(
        backend,
        '''    if calendar is not None and (
        not isinstance(calendar, dict)
        or not isinstance(calendar.get("appointments", []), list)
    ):
        raise HTTPException(status_code=400, detail="Backup calendar data is malformed")''',
        '''    if calendar is not None and (
        not isinstance(calendar, dict)
        or not isinstance(calendar.get("appointments", []), list)
    ):
        raise HTTPException(status_code=400, detail="Backup calendar data is malformed")
    if fast_memory is not None and (
        not isinstance(fast_memory, dict)
        or not isinstance(fast_memory.get("memories", []), list)
    ):
        raise HTTPException(status_code=400, detail="Backup Fast Memory data is malformed")''',
        "fast memory backup validation",
    )
    backend = replace_once(
        backend,
        '''    if calendar is not None:
        _calendar_save(calendar)
    load_chat_sessions()''',
        '''    if calendar is not None:
        _calendar_save(calendar)
    if fast_memory is not None:
        restore_fast_memory(fast_memory)
    load_chat_sessions()''',
        "fast memory backup restore",
    )
    backend = replace_once(
        backend,
        '''                "auto_sync_releases_to_workshop_memory": request.auto_sync_releases_to_workshop_memory,
            }''',
        '''                "auto_sync_releases_to_workshop_memory": request.auto_sync_releases_to_workshop_memory,
                "web_search_enabled": request.web_search_enabled,
                "web_search_context_size": request.web_search_context_size,
                "fast_memory_enabled": request.fast_memory_enabled,
                "fast_memory_auto_capture": request.fast_memory_auto_capture,
                "fast_memory_context_items": request.fast_memory_context_items,
            }''',
        "fast memory settings persistence",
    )

    backend = replace_once(
        backend,
        '''    frontend_text = ""
    try:''',
        '''    try:
        memory_health = fast_memory_status()
        add(
            "Fast Memory operational",
            "operational" if memory_health.get("operational") else "failed",
            f"{memory_health.get('total', 0)} organized records; SQLite readable; bounded to {memory_health.get('max_records', 0)}",
            "memory",
            "Inspect /data/zbrano_fast_memory.sqlite3 and the Fast Memory API.",
        )
    except Exception as exc:
        add("Fast Memory operational", "failed", str(exc), "memory", "Inspect Fast Memory SQLite storage.")

    frontend_text = ""
    try:''',
        "fast memory diagnostics",
    )
    backend = replace_once(
        backend,
        '''            "Calendar frontend wired": ('id="calendar-tab"', 'id="calendar-panel"', 'zbrano-v01271-calendar-center'),
            "Entities frontend wired":''',
        '''            "Calendar frontend wired": ('id="calendar-tab"', 'id="calendar-panel"', 'zbrano-v01271-calendar-center'),
            "Fast Memory frontend wired": ('id="fast-memory-list"', 'id="fast-memory-form"', 'zbrano-v01274-fast-memory'),
            "Entities frontend wired":''',
        "fast memory frontend diagnostics",
    )
    backend = replace_once(
        backend,
        '''    "attachments": {
        "title": "Chat attachments",''',
        '''    "fast_memory": {
        "title": "Fast Memory",
        "aliases": ("fast memory", "personal profile", "session memory", "remember", "forget"),
        "terms": ("fast memory", "frontend source", "persistent storage", "application health"),
        "layers": ("SQLite storage", "deduplication", "retrieval", "background extraction", "interface"),
        "files": ("jarvis/apply_fast_memory_v01274.py", "jarvis/app/main.py", "jarvis/app/static/index.html"),
    },
    "attachments": {
        "title": "Chat attachments",''',
        "fast memory developer feature",
    )

    memory_html = r'''      <section class="fast-memory-center" aria-labelledby="fast-memory-heading">
        <div class="fast-memory-heading"><div><h3 id="fast-memory-heading">FAST MEMORY</h3><p>Compact local profile, project, decision, fact, follow-up, and session context.</p></div><button id="fast-memory-refresh" type="button">Refresh</button></div>
        <div class="settings-grid fast-memory-policy">
          <label class="toggle-row"><input id="fast-memory-enabled" type="checkbox" checked> Use relevant Fast Memory in chats</label>
          <label class="toggle-row"><input id="fast-memory-auto-capture" type="checkbox" checked> Organize important details after each reply</label>
          <div class="setting-field"><label for="fast-memory-context-items">Maximum memories per response</label><input id="fast-memory-context-items" type="number" min="2" max="20" value="10"><small>Only relevance-ranked records are loaded.</small></div>
        </div>
        <div id="fast-memory-status" class="fast-memory-status" role="status">Loading Fast Memory&hellip;</div>
        <div class="fast-memory-toolbar">
          <input id="fast-memory-search" type="search" placeholder="Search memories">
          <select id="fast-memory-kind" aria-label="Memory type"><option value="">All types</option><option value="profile">Profile</option><option value="preference">Preferences</option><option value="project">Projects</option><option value="decision">Decisions</option><option value="fact">Facts</option><option value="follow_up">Follow-ups</option><option value="session_summary">Sessions</option><option value="temporary">Temporary</option></select>
        </div>
        <form id="fast-memory-form" class="fast-memory-form">
          <input id="fast-memory-id" type="hidden">
          <select id="fast-memory-edit-kind" aria-label="Type"><option value="profile">Profile</option><option value="preference">Preference</option><option value="project">Project</option><option value="decision">Decision</option><option value="fact" selected>Fact</option><option value="follow_up">Follow-up</option><option value="temporary">Temporary</option></select>
          <input id="fast-memory-subject" required maxlength="160" placeholder="Subject, e.g. Royce or Grinder">
          <input id="fast-memory-key" required maxlength="120" placeholder="Stable key, e.g. preferred_units">
          <textarea id="fast-memory-value" required maxlength="1600" rows="2" placeholder="Concise memory value"></textarea>
          <div class="fast-memory-form-row"><label>Importance <select id="fast-memory-importance"><option value="3">Useful</option><option value="4">Important</option><option value="5">Critical / pinned</option><option value="2">Minor</option><option value="1">Low</option></select></label><label class="toggle-row"><input id="fast-memory-pinned" type="checkbox"> Pin</label></div>
          <div class="settings-actions"><button type="submit">Save memory</button><button id="fast-memory-form-clear" type="button">Clear</button><span id="fast-memory-form-status"></span></div>
        </form>
        <div id="fast-memory-list" class="fast-memory-list"></div>
      </section>
'''
    frontend = replace_once(
        frontend,
        '''      <div class="settings-actions"><button id="export-backup" type="button">Export Backup</button>''',
        memory_html + '''      <div class="settings-actions"><button id="export-backup" type="button">Export Backup</button>''',
        "fast memory center",
    )
    frontend = replace_once(
        frontend,
        '''const retentionDays = document.getElementById("retention-days");
const preferredLanguage''',
        '''const retentionDays = document.getElementById("retention-days");
const fastMemoryEnabled = document.getElementById("fast-memory-enabled");
const fastMemoryAutoCapture = document.getElementById("fast-memory-auto-capture");
const fastMemoryContextItems = document.getElementById("fast-memory-context-items");
const preferredLanguage''',
        "fast memory settings controls",
    )
    frontend = replace_once(
        frontend,
        '''    retentionDays.value = String(jarvisPreferences.retention_days ?? 90);
    preferredLanguage.value''',
        '''    retentionDays.value = String(jarvisPreferences.retention_days ?? 90);
    fastMemoryEnabled.checked = jarvisPreferences.fast_memory_enabled !== false;
    fastMemoryAutoCapture.checked = jarvisPreferences.fast_memory_auto_capture !== false;
    fastMemoryContextItems.value = String(jarvisPreferences.fast_memory_context_items ?? 10);
    preferredLanguage.value''',
        "fast memory settings load",
    )
    frontend = replace_once(
        frontend,
        '''        retention_days: Number(retentionDays.value),
        preferred_language:''',
        '''        retention_days: Number(retentionDays.value),
        fast_memory_enabled: fastMemoryEnabled.checked,
        fast_memory_auto_capture: fastMemoryAutoCapture.checked,
        fast_memory_context_items: Number(fastMemoryContextItems.value),
        preferred_language:''',
        "fast memory settings save",
    )

    memory_css = r'''
    /* v0.12.74 organized local Fast Memory. */
    .fast-memory-center { display:grid; gap:.7rem; margin-top:1rem; padding-top:1rem; border-top:1px solid var(--line); }
    .fast-memory-heading { display:flex; align-items:flex-start; justify-content:space-between; gap:.7rem; }
    .fast-memory-heading h3,.fast-memory-heading p { margin:.05rem 0 .2rem; }
    .fast-memory-policy { align-items:start; }
    .fast-memory-status { padding:.65rem .75rem; border:1px solid var(--line); border-radius:7px; color:var(--text-muted); }
    .fast-memory-toolbar { display:grid; grid-template-columns:minmax(0,1fr) minmax(9rem,.35fr); gap:.5rem; }
    .fast-memory-toolbar input,.fast-memory-toolbar select,.fast-memory-form input,.fast-memory-form select,.fast-memory-form textarea { width:100%; min-width:0; }
    .fast-memory-form { display:grid; grid-template-columns:minmax(8rem,.35fr) minmax(10rem,.65fr) minmax(10rem,.65fr); gap:.5rem; padding:.7rem; border:1px solid var(--line); border-radius:7px; }
    .fast-memory-form textarea,.fast-memory-form .fast-memory-form-row,.fast-memory-form .settings-actions { grid-column:1/-1; }
    .fast-memory-form-row { display:flex; flex-wrap:wrap; align-items:end; gap:.7rem; }
    .fast-memory-form-row label:not(.toggle-row) { display:grid; gap:.25rem; }
    .fast-memory-list { display:grid; gap:.45rem; max-height:32rem; overflow:auto; overscroll-behavior:contain; }
    .fast-memory-item { display:grid; gap:.35rem; padding:.65rem; border:1px solid var(--line); border-radius:7px; background:color-mix(in srgb,var(--surface-strong) 72%,transparent); }
    .fast-memory-item-head { display:flex; align-items:flex-start; justify-content:space-between; gap:.5rem; }
    .fast-memory-item-title { min-width:0; font-weight:650; overflow-wrap:anywhere; }
    .fast-memory-badge { display:inline-block; margin-right:.35rem; padding:.1rem .35rem; border:1px solid var(--line); border-radius:999px; color:var(--cyan); font-size:.64rem; text-transform:uppercase; }
    .fast-memory-value { overflow-wrap:anywhere; }
    .fast-memory-meta { display:flex; flex-wrap:wrap; gap:.35rem; color:var(--text-muted); font-size:.68rem; }
    .fast-memory-actions { display:flex; flex-wrap:wrap; gap:.3rem; }
    .fast-memory-actions button { padding:.28rem .45rem; font-size:.69rem; }
    @media(max-width:720px) { .fast-memory-form { grid-template-columns:1fr; } .fast-memory-form > * { grid-column:1; } .fast-memory-toolbar { grid-template-columns:1fr; } }
'''
    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.74 could not locate stylesheet close")
    frontend = frontend[:style_close] + memory_css + frontend[style_close:]

    memory_runtime = r'''
<script id="zbrano-v01274-fast-memory">
(() => {
  const root = document.getElementById("fast-memory-list");
  const form = document.getElementById("fast-memory-form");
  if (!root || !form) return;
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"})[char]);
  let memories = [];

  async function api(path, options={}) {
    const response = await fetch(path, {cache:"no-store", ...options});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    return data;
  }

  function clearForm() {
    form.reset();
    $("fast-memory-id").value = "";
    $("fast-memory-edit-kind").value = "fact";
    $("fast-memory-importance").value = "3";
    $("fast-memory-form-status").textContent = "";
  }

  function render(data) {
    memories = data.memories || [];
    const status = data.status || {};
    const groups = Object.entries(status.by_kind || {}).map(([kind,count]) => `${kind.replaceAll("_"," ")}: ${count}`).join(" · ");
    const runtime = status.runtime || {};
    const process = runtime.running ? " · organizing the latest conversation…" : runtime.last_error ? ` · last organizer error: ${runtime.last_error}` : "";
    $("fast-memory-status").textContent = `${status.total || 0} organized memories · ${status.pinned || 0} pinned${groups ? ` · ${groups}` : ""}${process}`;
    root.replaceChildren();
    if (!memories.length) { root.innerHTML = '<div class="calendar-empty">No matching Fast Memory. Important details will appear here after conversations.</div>'; return; }
    for (const item of memories) {
      const node = document.createElement("article");
      node.className = "fast-memory-item";
      const date = new Date(Number(item.updated_at || 0) * 1000).toLocaleString();
      node.innerHTML = `<div class="fast-memory-item-head"><div class="fast-memory-item-title"><span class="fast-memory-badge">${esc(item.kind.replaceAll("_"," "))}</span>${esc(item.subject)} · ${esc(item.key)}</div><span>${item.pinned ? "📌" : ""}</span></div><div class="fast-memory-value">${esc(item.summary || item.value)}</div><div class="fast-memory-meta"><span>importance ${esc(item.importance)}</span><span>confidence ${Math.round(Number(item.confidence || 0)*100)}%</span><span>revision ${esc(item.revision)}</span><span>${esc(date)}</span></div><div class="fast-memory-actions"><button type="button" data-memory-edit="${esc(item.id)}">Edit</button><button type="button" data-memory-pin="${esc(item.id)}">${item.pinned ? "Unpin" : "Pin"}</button><button type="button" data-memory-delete="${esc(item.id)}">Delete</button></div>`;
      root.appendChild(node);
    }
  }

  async function load() {
    const query = $("fast-memory-search").value.trim();
    const kind = $("fast-memory-kind").value;
    const data = await api(`api/fast-memory?query=${encodeURIComponent(query)}&kind=${encodeURIComponent(kind)}&limit=100`);
    render(data);
  }

  function edit(item) {
    $("fast-memory-id").value = item.id;
    $("fast-memory-edit-kind").value = item.kind === "session_summary" ? "fact" : item.kind;
    $("fast-memory-subject").value = item.subject;
    $("fast-memory-key").value = item.key;
    $("fast-memory-value").value = item.value;
    $("fast-memory-importance").value = String(item.importance || 3);
    $("fast-memory-pinned").checked = Boolean(item.pinned);
    form.scrollIntoView({behavior:"smooth", block:"center"});
  }

  form.addEventListener("submit", async event => {
    event.preventDefault();
    const id = $("fast-memory-id").value;
    const body = {
      kind: $("fast-memory-edit-kind").value, subject: $("fast-memory-subject").value.trim(),
      key: $("fast-memory-key").value.trim(), value: $("fast-memory-value").value.trim(),
      summary: $("fast-memory-value").value.trim(), keywords: [], importance: Number($("fast-memory-importance").value),
      confidence: 1, pinned: $("fast-memory-pinned").checked, expires_at: 0,
    };
    $("fast-memory-form-status").textContent = "Saving…";
    try {
      await api(id ? `api/fast-memory/${encodeURIComponent(id)}` : "api/fast-memory", {method:id ? "PUT" : "POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
      clearForm(); await load();
    } catch (error) { $("fast-memory-form-status").textContent = `Save failed: ${error.message || error}`; }
  });
  root.addEventListener("click", async event => {
    const editButton = event.target.closest("[data-memory-edit]");
    if (editButton) { const item = memories.find(memory => memory.id === editButton.dataset.memoryEdit); if (item) edit(item); return; }
    const pinButton = event.target.closest("[data-memory-pin]");
    if (pinButton) {
      const item = memories.find(memory => memory.id === pinButton.dataset.memoryPin); if (!item) return;
      await api(`api/fast-memory/${encodeURIComponent(item.id)}`, {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({...item, pinned:!item.pinned})}); await load(); return;
    }
    const deleteButton = event.target.closest("[data-memory-delete]");
    if (deleteButton && confirm("Delete this Fast Memory?")) { await api(`api/fast-memory/${encodeURIComponent(deleteButton.dataset.memoryDelete)}`, {method:"DELETE"}); await load(); }
  });
  $("fast-memory-refresh").addEventListener("click", () => load().catch(error => { $("fast-memory-status").textContent = error.message || error; }));
  $("fast-memory-search").addEventListener("input", () => { clearTimeout(window.zbranoFastMemorySearchTimer); window.zbranoFastMemorySearchTimer = setTimeout(() => load().catch(()=>{}), 250); });
  $("fast-memory-kind").addEventListener("change", () => load().catch(()=>{}));
  $("fast-memory-form-clear").addEventListener("click", clearForm);
  document.querySelector('[data-settings-target="memory"]')?.addEventListener("click", () => load().catch(error => { $("fast-memory-status").textContent = `Fast Memory unavailable: ${error.message || error}`; }));
  window.zbranoFastMemory = {refresh:load};
})();
</script>
'''
    frontend = replace_once(frontend, "\n</body>\n</html>", memory_runtime + "\n</body>\n</html>", "fast memory runtime")

    backend = backend.replace('version="0.12.73"', 'version="0.12.74"')
    backend = backend.replace('"version": "0.12.73"', '"version": "0.12.74"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.73"', '"X-ZBRANO-Frontend-Version": "0.12.74"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.73"', '"name": "ZBRANO Developer Mode", "version": "0.12.74"')
    frontend = frontend.replace("HUD 0.12.73", "HUD 0.12.74")

    backend_markers = (
        'version="0.12.74"', "FAST_MEMORY_PATH", "CREATE TABLE IF NOT EXISTS memory_records",
        "def upsert_fast_memory(", "def fast_memory_search(", "def fast_memory_context(",
        "async def extract_fast_memory_from_exchange(", '"name": "remember_fast_memory"',
        '@app.get("/api/fast-memory")', '"fast_memory": export_fast_memory()',
        '"Fast Memory operational"', "fast_memory_input(message, session_id)",
    )
    frontend_markers = (
        "HUD 0.12.74", 'id="fast-memory-list"', 'id="fast-memory-form"',
        'id="fast-memory-enabled"', 'id="zbrano-v01274-fast-memory"',
        "window.zbranoFastMemory", "fast_memory_auto_capture: fastMemoryAutoCapture.checked",
    )
    missing = [marker for marker in backend_markers if marker not in backend]
    missing += [marker for marker in frontend_markers if marker not in frontend]
    if missing:
        raise RuntimeError("ZBRANO v0.12.74 verification failed: " + ", ".join(missing))

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
