import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"ZBRANO v0.12.30 patch expected one {label} marker; found {count}"
        )
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.30 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    icon_rewrites = {
        "https://cdn.simpleicons.org/gmail/EA4335": "plugin-icons/gmail.svg",
        "https://cdn.simpleicons.org/googledrive/4285F4": "plugin-icons/googledrive.svg",
        "https://cdn.simpleicons.org/googlecalendar/4285F4": "plugin-icons/googlecalendar.svg",
        "https://cdn.simpleicons.org/googlechat/00AC47": "plugin-icons/googlechat.svg",
        "https://cdn.simpleicons.org/github/181717": "plugin-icons/github.svg",
        "https://cdn.simpleicons.org/cloudflare/F38020": "plugin-icons/cloudflare.svg",
        "https://cdn.simpleicons.org/playwright/2EAD33": "plugin-icons/playwright.svg",
        "https://cdn.simpleicons.org/googlecontacts/4285F4": "",
        "https://cdn.simpleicons.org/googleworkspace/4285F4": "",
        "https://cdn.simpleicons.org/canva/00C4CC": "",
        "https://cdn.simpleicons.org/adobe/FF0000": "",
    }
    for external_url, local_url in icon_rewrites.items():
        backend = backend.replace(external_url, local_url)

    context_row = '''        <div class="composer-context-row" aria-label="Message tools">
          <label class="composer-web-control" for="web-search-mode"><span aria-hidden="true">◎</span><span>Web</span><select id="web-search-mode" title="Choose how this message may use the public web"><option value="auto">Auto</option><option value="search">On</option><option value="off">Off</option></select></label>
          <div class="composer-plugin-context"><span class="composer-context-label">Plugins</span><div id="composer-plugin-icons" class="composer-plugin-icons" role="list" aria-label="Enabled plugins"><span class="composer-plugin-empty">Loading…</span></div></div>
        </div>
'''
    frontend = replace_once(
        frontend,
        context_row,
        "",
        "external composer context row",
    )
    frontend = replace_once(
        frontend,
        '''        <form id="chat-form">
          <textarea id="message"''',
        '''        <form id="chat-form">
          <div class="composer-input-stack">
          <textarea id="message"''',
        "composer input stack opening",
    )
    frontend = replace_once(
        frontend,
        '''          <button id="mic-button" type="button"''',
        context_row.replace("        <div", "            <div", 1).replace("          <label", "              <label", 1).replace("          <div class=\"composer-plugin-context\"", "              <div class=\"composer-plugin-context\"", 1).replace("        </div>\n", "            </div>\n", 1)
        + '''          </div>
          <button id="mic-button" type="button"''',
        "composer input stack closing",
    )
    frontend = replace_once(
        frontend,
        '''  @media (max-width: 680px) {
    .composer-context-row { align-items: flex-start; flex-wrap: wrap; }''',
        '''  .composer-input-stack {
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    gap: .2rem;
    min-width: 0;
  }
  .composer-input-stack #message { box-sizing: border-box; flex: 0 0 auto; width: 100%; }
  .composer-input-stack .composer-context-row { padding-left: .1rem; }
  @media (max-width: 680px) {
    .composer-context-row { align-items: flex-start; flex-wrap: wrap; }''',
        "composer input stack styling",
    )

    internal_chat_helpers = '''INTERNAL_CHAT_SESSION_PREFIXES = ("zbrano-diagnostic-",)


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


'''
    backend = replace_once(
        backend,
        "def persist_chat_sessions() -> None:\n",
        internal_chat_helpers + "def persist_chat_sessions() -> None:\n",
        "internal chat helpers",
    )
    backend = replace_once(
        backend,
        '''            for session_id, messages in CHAT_SESSIONS.items()
        },''',
        '''            for session_id, messages in CHAT_SESSIONS.items()
            if not is_internal_chat_session(session_id)
        },''',
        "internal chat persistence filter",
    )
    backend = replace_once(
        backend,
        '''    CHAT_SESSION_META.clear()
    for session_id, record in ordered:
        if not isinstance(record, dict):
            continue''',
        '''    CHAT_SESSION_META.clear()
    removed_internal = False
    for session_id, record in ordered:
        if is_internal_chat_session(session_id):
            removed_internal = True
            continue
        if not isinstance(record, dict):
            continue''',
        "persisted diagnostic chat cleanup",
    )
    backend = replace_once(
        backend,
        '''        CHAT_SESSION_META[session_id] = {
            "title": str(record.get("title") or chat_title(CHAT_SESSIONS[session_id])),
            "updated_at": float(record.get("updated_at", 0)),
        }


def prune_expired_chats() -> int:''',
        '''        CHAT_SESSION_META[session_id] = {
            "title": str(record.get("title") or chat_title(CHAT_SESSIONS[session_id])),
            "updated_at": float(record.get("updated_at", 0)),
        }
    if removed_internal:
        persist_chat_sessions()


def prune_expired_chats() -> int:''',
        "persisted diagnostic chat rewrite",
    )
    backend = replace_once(
        backend,
        '''def get_chat_history(session_id: str) -> deque[dict[str, Any]]:
    session_id = session_id.strip() or "default"
    if session_id not in CHAT_SESSIONS:
        if len(CHAT_SESSIONS) >= CHAT_SESSIONS_MAX and CHAT_SESSION_ORDER:
            oldest = CHAT_SESSION_ORDER.popleft()
            CHAT_SESSIONS.pop(oldest, None)
            CHAT_SESSION_META.pop(oldest, None)
        CHAT_SESSIONS[session_id] = deque(maxlen=CHAT_HISTORY_MAX_MESSAGES)
        CHAT_SESSION_ORDER.append(session_id)
        CHAT_SESSION_META[session_id] = {"title": "New chat", "updated_at": time.time()}
    return CHAT_SESSIONS[session_id]''',
        '''def get_chat_history(session_id: str) -> deque[dict[str, Any]]:
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
    return CHAT_SESSIONS[session_id]''',
        "internal chat allocation isolation",
    )
    backend = replace_once(
        backend,
        '''        for session_id, messages in CHAT_SESSIONS.items()
    ]
    chats.sort(key=lambda item: item["updated_at"], reverse=True)''',
        '''        for session_id, messages in CHAT_SESSIONS.items()
        if not is_internal_chat_session(session_id)
    ]
    chats.sort(key=lambda item: item["updated_at"], reverse=True)''',
        "internal chat API filter",
    )
    backend = replace_once(
        backend,
        '''@app.post("/api/chats")
async def create_chat(request: ChatSessionCreate) -> dict[str, Any]:
    get_chat_history(request.session_id)
    persist_chat_sessions()
    return {"session_id": request.session_id, "title": "New chat"}''',
        '''@app.post("/api/chats")
async def create_chat(request: ChatSessionCreate) -> dict[str, Any]:
    get_chat_history(request.session_id)
    if not is_internal_chat_session(request.session_id):
        persist_chat_sessions()
    return {"session_id": request.session_id, "title": "New chat"}''',
        "internal chat creation persistence guard",
    )
    backend = replace_once(
        backend,
        '''async def developer_diagnostics() -> dict[str, object]:
    checks: list[dict[str, object]] = []''',
        '''async def developer_diagnostics() -> dict[str, object]:
    purge_internal_chat_sessions()
    checks: list[dict[str, object]] = []''',
        "diagnostic chat preflight cleanup",
    )
    backend = replace_once(
        backend,
        '''        finally:
            try:
                await request_json(f"/api/chat/history/{chat_session}", method="DELETE")
            except Exception:
                pass

        attachment_session = f"zbrano-attachment-{time.time_ns():x}"[-80:]''',
        '''        finally:
            # In-process cleanup cannot be interrupted at an HTTP await boundary.
            clear_chat_history(chat_session)

        attachment_session = f"zbrano-attachment-{time.time_ns():x}"[-80:]''',
        "cancellation-safe diagnostic chat cleanup",
    )

    backend = backend.replace('version="0.12.29"', 'version="0.12.30"')
    backend = backend.replace('"version": "0.12.29"', '"version": "0.12.30"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.29"', '"X-ZBRANO-Frontend-Version": "0.12.30"')
    frontend = frontend.replace("HUD 0.12.29", "HUD 0.12.30")

    if "cdn.simpleicons.org" in backend or "cdn.simpleicons.org" in frontend:
        raise RuntimeError("ZBRANO v0.12.30 still contains a runtime Simple Icons CDN dependency")
    require(frontend, 'class="composer-input-stack"', "textarea and controls stack")
    require(frontend, 'id="composer-plugin-icons"', "enabled plugin indicators")
    require(backend, "def purge_internal_chat_sessions", "diagnostic chat cleanup")
    require(backend, "if not is_internal_chat_session(request.session_id)", "diagnostic chat persistence guard")
    require(backend, "clear_chat_history(chat_session)", "cancellation-safe diagnostic cleanup")
    require(backend, '"X-ZBRANO-Frontend-Version": "0.12.30"', "frontend response version")
    require(backend, 'version="0.12.30"', "backend version")
    require(frontend, "HUD 0.12.30", "HUD version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
