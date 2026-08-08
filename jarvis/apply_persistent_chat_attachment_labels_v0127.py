from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.7 patch missing: {label}")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")

    append_marker = "def append_chat_message(session_id: str, role: str, content: str) -> None:\n"
    require(text, append_marker, "chat persistence function")
    attachment_helpers = r'''ATTACHMENT_CONTEXT_MARKER = "\n\n--- Attached file context ---\n"
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


'''
    text = text.replace(append_marker, attachment_helpers + append_marker, 1)

    old_append = '''def append_chat_message(session_id: str, role: str, content: str) -> None:
    if not content:
        return
    history = get_chat_history(session_id)
    history.append({"role": role, "content": content})
    CHAT_SESSION_META[session_id] = {
        "title": chat_title(history),
        "updated_at": time.time(),
    }
    persist_chat_sessions()
'''
    new_append = '''def append_chat_message(session_id: str, role: str, content: str) -> None:
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
    }
    persist_chat_sessions()
'''
    require(text, old_append, "chat record body")
    text = text.replace(old_append, new_append, 1)

    history_expression = "list(get_chat_history(session_id))[-chat_context_limit():]"
    require(text, history_expression, "model history input")
    text = text.replace(history_expression, "model_chat_history(session_id)")

    public_history = '        "messages": list(history),'
    require(text, public_history, "chat history response")
    text = text.replace(
        public_history,
        '        "messages": [public_chat_message(message) for message in history],',
        1,
    )

    text = text.replace('version="0.12.6"', 'version="0.12.7"')
    text = text.replace('"version": "0.12.6"', '"version": "0.12.7"')
    MAIN.write_text(text, encoding="utf-8")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    old_add_message = '''function addMessage(text, role) {
  const item = document.createElement("div");
  item.className = `message ${role}`;
  renderMessageContent(item, text);
  messages.appendChild(item);
  messages.scrollTop = messages.scrollHeight;
  return item;
}'''
    new_add_message = r'''function formatAttachmentSize(bytes) {
  const size = Number(bytes) || 0;
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(size < 10240 ? 1 : 0)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function appendMessageAttachments(item, attachments = []) {
  if (!Array.isArray(attachments) || !attachments.length) return;
  const list = document.createElement("div");
  list.className = "message-attachments";
  list.setAttribute("aria-label", `${attachments.length} attached file${attachments.length === 1 ? "" : "s"}`);
  for (const attachment of attachments) {
    const chip = document.createElement("span");
    chip.className = "message-attachment";
    const name = document.createElement("strong");
    name.textContent = `📎 ${attachment.name || "Attached file"}`;
    const metadata = document.createElement("small");
    metadata.textContent = [attachment.mime_type, formatAttachmentSize(attachment.size)].filter(Boolean).join(" · ");
    chip.append(name, metadata);
    list.appendChild(chip);
  }
  item.appendChild(list);
}

function addMessage(text, role, attachments = []) {
  const item = document.createElement("div");
  item.className = `message ${role}`;
  renderMessageContent(item, text);
  appendMessageAttachments(item, attachments);
  messages.appendChild(item);
  messages.scrollTop = messages.scrollHeight;
  return item;
}'''
    require(text, old_add_message, "message renderer")
    text = text.replace(old_add_message, new_add_message, 1)

    restored_message = '      addMessage(message.content, message.role === "user" ? "user" : "jarvis");'
    require(text, restored_message, "restored chat message")
    text = text.replace(
        restored_message,
        '      addMessage(message.content, message.role === "user" ? "user" : "jarvis", message.attachments || []);',
        1,
    )

    live_message = '''  rememberPrompt(message);
  addMessage(message, "user");
  input.value = "";'''
    require(text, live_message, "live user message")
    text = text.replace(
        live_message,
        '''  rememberPrompt(message);
  const messageAttachments = typeof window.zbranoAttachmentItems === "function"
    ? window.zbranoAttachmentItems()
    : [];
  addMessage(message, "user", messageAttachments);
  input.value = "";''',
        1,
    )

    ids_export = "  window.zbranoAttachmentIds = () => pending.map(item => item.file_id);"
    require(text, ids_export, "attachment ID exporter")
    text = text.replace(
        ids_export,
        '''  window.zbranoAttachmentIds = () => pending.map(item => item.file_id);
  window.zbranoAttachmentItems = () => pending.map(item => ({
    file_id: item.file_id,
    name: item.name,
    scope: item.scope,
    mime_type: item.mime_type,
    size: item.size,
  }));''',
        1,
    )

    old_upload_status = '''        state.textContent = destination === "shared"
          ? `${files.length} file${files.length === 1 ? "" : "s"} attached and added to Shared Files`
          : `${files.length} file${files.length === 1 ? "" : "s"} attached to this chat`;'''
    new_upload_status = '''        const names = files.map(file => file.name).join(", ");
        state.textContent = destination === "shared"
          ? `Attached and added to Shared Files: ${names}`
          : `Attached to this chat: ${names}`;'''
    require(text, old_upload_status, "attachment count status")
    text = text.replace(old_upload_status, new_upload_status, 1)

    style_close = text.find("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.7 patch missing: style close")
    css = r'''
    .message-attachments { display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .65rem; }
    .message-attachment {
      display: inline-grid;
      gap: .08rem;
      max-width: min(100%, 30rem);
      padding: .35rem .55rem;
      border: 1px solid color-mix(in srgb, var(--cyan) 45%, var(--line));
      border-radius: 6px;
      background: color-mix(in srgb, var(--surface-strong) 82%, transparent);
      color: var(--cyan);
    }
    .message-attachment strong { overflow-wrap: anywhere; font-weight: 600; }
    .message-attachment small { color: var(--text-muted); font-size: .68rem; }
'''
    text = text[:style_close] + css + text[style_close:]

    text = text.replace("HUD 0.12.6", "HUD 0.12.7")
    INDEX.write_text(text, encoding="utf-8")


def verify() -> None:
    main = MAIN.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    required_main = (
        'version="0.12.7"',
        "ATTACHMENT_CONTEXT_MARKER",
        "def public_chat_message(",
        "def model_chat_history(",
        'record["attachments"] = attachments',
        '"messages": [public_chat_message(message) for message in history]',
    )
    required_index = (
        "HUD 0.12.7",
        "function appendMessageAttachments(",
        'className = "message-attachment"',
        "window.zbranoAttachmentItems",
        'addMessage(message, "user", messageAttachments)',
        "message.attachments || []",
        "Attached to this chat: ${names}",
    )
    missing = [marker for marker in required_main if marker not in main]
    missing += [marker for marker in required_index if marker not in index]
    if missing:
        raise RuntimeError("ZBRANO v0.12.7 verification failed: " + ", ".join(missing))


if __name__ == "__main__":
    patch_main()
    patch_index()
    verify()
