import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"ZBRANO v0.12.26 patch expected one {label} marker; found {count}"
        )
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.26 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        '''    "auto_sync_releases_to_workshop_memory": True,
}''',
        '''    "auto_sync_releases_to_workshop_memory": True,
    "web_search_enabled": True,
    "web_search_context_size": "medium",
}''',
        "web search preference defaults",
    )
    backend = replace_once(
        backend,
        '''class ChatRequest(BaseModel):
    session_id: str = Field(default="default", min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4000)
    attachment_ids: list[str] = Field(default_factory=list, max_length=20)''',
        '''class ChatRequest(BaseModel):
    session_id: str = Field(default="default", min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4000)
    attachment_ids: list[str] = Field(default_factory=list, max_length=20)
    search_mode: str = Field(default="auto", pattern="^(auto|search|off)$")''',
        "per-message search mode",
    )
    backend = replace_once(
        backend,
        '''    auto_sync_releases_to_workshop_memory: bool = True


class AgentSettingsUpdate''',
        '''    auto_sync_releases_to_workshop_memory: bool = True
    web_search_enabled: bool = True
    web_search_context_size: str = Field(default="medium", pattern="^(low|medium|high)$")


class AgentSettingsUpdate''',
        "search settings validation",
    )

    search_helpers = r'''def native_web_search_tool(search_mode: str = "auto") -> dict[str, Any] | None:
    if developer_mode_enabled() or search_mode == "off":
        return None
    preferences = load_preferences()
    if preferences.get("web_search_enabled") is False:
        return None
    context_size = str(preferences.get("web_search_context_size") or "medium")
    if context_size not in {"low", "medium", "high"}:
        context_size = "medium"
    return {
        "type": "web_search",
        "search_context_size": context_size,
    }


def web_search_tool_choice(search_mode: str = "auto") -> Any:
    search_tool = native_web_search_tool(search_mode)
    return {"type": "web_search"} if search_mode == "search" and search_tool else "auto"


def web_search_include_options(search_mode: str = "auto") -> dict[str, Any]:
    return (
        {"include": ["web_search_call.action.sources"]}
        if native_web_search_tool(search_mode)
        else {}
    )


def response_web_sources(response: dict[str, Any] | None) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(url: Any, title: Any = "") -> None:
        normalized_url = str(url or "").strip()
        if not normalized_url.startswith(("https://", "http://")) or normalized_url in seen:
            return
        seen.add(normalized_url)
        found.append({
            "url": normalized_url[:2000],
            "title": str(title or normalized_url)[:300],
        })

    for item in (response or {}).get("output", []):
        if not isinstance(item, dict):
            continue
        action = item.get("action") if isinstance(item.get("action"), dict) else {}
        for source in action.get("sources", []) if isinstance(action.get("sources"), list) else []:
            if isinstance(source, dict):
                add(source.get("url"), source.get("title"))
        for content in item.get("content", []) if isinstance(item.get("content"), list) else []:
            if not isinstance(content, dict):
                continue
            for annotation in content.get("annotations", []) if isinstance(content.get("annotations"), list) else []:
                if isinstance(annotation, dict) and annotation.get("type") == "url_citation":
                    add(annotation.get("url"), annotation.get("title"))
    return found[:30]


def web_sources_markdown(sources: list[dict[str, Any]]) -> str:
    if not sources:
        return ""
    lines = ["", "", "### Sources"]
    for source in sources[:30]:
        title = str(source.get("title") or source.get("url") or "Source").replace("[", "").replace("]", "")
        url = str(source.get("url") or "")
        if url.startswith(("https://", "http://")):
            lines.append(f"- [{title}]({url})")
    return "\n".join(lines) if len(lines) > 3 else ""


def web_search_progress(event: dict[str, Any]) -> str | None:
    event_type = str(event.get("type") or "")
    item = event.get("item") if isinstance(event.get("item"), dict) else {}
    item_type = str(item.get("type") or "")
    if "web_search_call" not in event_type and item_type != "web_search_call":
        return None
    if event_type.endswith((".completed", ".done")):
        return "Web search complete. Reviewing sources..."
    return "Searching the web..."


'''
    runtime_definition = '''def runtime_chat_tools() -> list[dict[str, Any]]:
    if developer_mode_enabled():
        return developer_runtime_tools() + developer_mcp_tools()
    return WORKSHOP_TOOLS + workshop_memory_function_tools() + active_mcp_tools()
'''
    runtime_replacement = '''def runtime_chat_tools(search_mode: str = "auto") -> list[dict[str, Any]]:
    if developer_mode_enabled():
        return developer_runtime_tools() + developer_mcp_tools()
    tools = WORKSHOP_TOOLS + workshop_memory_function_tools() + active_mcp_tools()
    search_tool = native_web_search_tool(search_mode)
    return tools + ([search_tool] if search_tool else [])
'''
    backend = replace_once(
        backend,
        runtime_definition,
        search_helpers + runtime_replacement,
        "native search tool exposure",
    )

    backend = replace_once(
        backend,
        'async def _run_jarvis_stream_events(message: str, session_id: str = "default") -> AsyncIterator[bytes]:\n    yield stream_event("status", message="Thinking…")',
        'async def _run_jarvis_stream_events(message: str, session_id: str = "default", search_mode: str = "auto") -> AsyncIterator[bytes]:\n    yield stream_event("status", message="Searching the web..." if search_mode == "search" and not developer_mode_enabled() else "Thinking…")',
        "stream search mode",
    )

    stream_start = backend.find('async def _run_jarvis_stream_events(')
    stream_end = backend.find('\n\nasync def run_jarvis_stream(', stream_start)
    if stream_start < 0 or stream_end < 0:
        raise RuntimeError("ZBRANO v0.12.26 patch missing: streaming function bounds")
    stream_section = backend[stream_start:stream_end]
    if stream_section.count("runtime_chat_tools()") != 3 or stream_section.count('"tool_choice": "auto"') != 3:
        raise RuntimeError("ZBRANO v0.12.26 patch expected three streaming search payloads")
    stream_section = stream_section.replace("runtime_chat_tools()", "runtime_chat_tools(search_mode)")
    stream_section = stream_section.replace(
        '"tool_choice": "auto",',
        '"tool_choice": web_search_tool_choice(search_mode),\n                **web_search_include_options(search_mode),',
    )

    stream_section = stream_section.replace(
        '''        remote_status = remote_mcp_progress(event)
        if remote_status:
            yield stream_event("status", message=remote_status)
        if event_type == "response.output_text.delta":''',
        '''        remote_status = remote_mcp_progress(event)
        if remote_status:
            yield stream_event("status", message=remote_status)
        search_status = web_search_progress(event)
        if search_status:
            yield stream_event("status", message=search_status)
        if event_type == "response.output_text.delta":''',
        1,
    )
    stream_section = stream_section.replace(
        '''            remote_status = remote_mcp_progress(event)
            if remote_status:
                yield stream_event("status", message=remote_status)

            if event_type == "response.output_text.delta":''',
        '''            remote_status = remote_mcp_progress(event)
            if remote_status:
                yield stream_event("status", message=remote_status)
            search_status = web_search_progress(event)
            if search_status:
                yield stream_event("status", message=search_status)

            if event_type == "response.output_text.delta":''',
        1,
    )

    stream_section = stream_section.replace(
        '''    if emitted_initial_text and not function_calls(response):
        yield stream_event("done", tool_calls=audit)''',
        '''    if emitted_initial_text and not function_calls(response):
        sources = response_web_sources(response)
        if sources:
            yield stream_event("sources", sources=sources)
        yield stream_event("done", tool_calls=audit)''',
        1,
    )
    stream_section = stream_section.replace(
        '''            for index in range(0, len(text), chunk_size):
                yield stream_event("delta", text=text[index:index + chunk_size])
            yield stream_event("done", tool_calls=audit)''',
        '''            for index in range(0, len(text), chunk_size):
                yield stream_event("delta", text=text[index:index + chunk_size])
            sources = response_web_sources(response)
            if sources:
                yield stream_event("sources", sources=sources)
            yield stream_event("done", tool_calls=audit)''',
        1,
    )
    stream_section = stream_section.replace(
        '''        if emitted_text and not function_calls(streamed_response):
            yield stream_event("done", tool_calls=audit)''',
        '''        if emitted_text and not function_calls(streamed_response):
            sources = response_web_sources(streamed_response)
            if sources:
                yield stream_event("sources", sources=sources)
            yield stream_event("done", tool_calls=audit)''',
        1,
    )
    backend = backend[:stream_start] + stream_section + backend[stream_end:]

    backend = replace_once(
        backend,
        '''async def run_jarvis_stream(message: str, session_id: str = "default") -> AsyncIterator[bytes]:
    """Persist a completed streamed exchange while forwarding events unchanged."""
    reply_parts: list[str] = []
    completed = False
    async for event_bytes in _run_jarvis_stream_events(message, session_id):''',
        '''async def run_jarvis_stream(message: str, session_id: str = "default", search_mode: str = "auto") -> AsyncIterator[bytes]:
    """Persist a completed streamed exchange while forwarding events unchanged."""
    reply_parts: list[str] = []
    completed = False
    async for event_bytes in _run_jarvis_stream_events(message, session_id, search_mode):''',
        "persistent search stream",
    )
    backend = replace_once(
        backend,
        '''        if event.get("type") == "delta" and event.get("text"):
            reply_parts.append(str(event["text"]))
        elif event.get("type") == "done":''',
        '''        if event.get("type") == "delta" and event.get("text"):
            reply_parts.append(str(event["text"]))
        elif event.get("type") == "sources":
            reply_parts.append(web_sources_markdown(event.get("sources") or []))
        elif event.get("type") == "done":''',
        "source persistence",
    )
    backend = replace_once(
        backend,
        'async for event_bytes in run_jarvis_stream(effective_message, request.session_id):',
        'async for event_bytes in run_jarvis_stream(effective_message, request.session_id, request.search_mode):',
        "WebSocket search mode",
    )
    backend = replace_once(
        backend,
        'async for event in run_jarvis_stream(effective_message, request.session_id):',
        'async for event in run_jarvis_stream(effective_message, request.session_id, request.search_mode):',
        "HTTP stream search mode",
    )

    backend = replace_once(
        backend,
        '''            add(
                "Voice pipeline readiness",''',
        '''            web_search_enabled = load_preferences().get("web_search_enabled") is not False
            add(
                "Native Web Search configuration",
                "operational" if openai_ready and web_search_enabled else "degraded",
                f"tool=web_search; model={health_payload.get('openai_model')}; enabled={web_search_enabled}; live search not generated by diagnostics",
                "web_search",
                "Configure the OpenAI API key, enable Web Search in Settings, and verify that the selected model supports the hosted web_search tool.",
            )
            add(
                "Voice pipeline readiness",''',
        "web search diagnostic",
    )
    backend = replace_once(
        backend,
        '''DEVELOPER_FEATURE_SPECS = {
    "attachments": {''',
        '''DEVELOPER_FEATURE_SPECS = {
    "web_search": {
        "title": "Native Web Search",
        "aliases": ("web search", "search web", "internet search", "citation", "sources"),
        "terms": ("native web search", "ai chat", "application health"),
        "layers": ("chat mode", "responses api tool", "stream events", "citations"),
        "files": (
            "jarvis/apply_native_web_search_v01226.py",
            "jarvis/app/main.py",
            "jarvis/app/static/index.html",
        ),
    },
    "attachments": {''',
        "targeted web search feature",
    )

    frontend = replace_once(
        frontend,
        '''<div class="attachment-controls"><button id="attach-file" type="button">📎 Attach</button><select id="attachment-scope" title="Choose where this upload is stored">''',
        '''<div class="attachment-controls"><button id="attach-file" type="button">📎 Attach</button><select id="web-search-mode" title="Choose how this message may use the public web"><option value="auto">Web · Auto</option><option value="search">Search Web</option><option value="off">Web Off</option></select><select id="attachment-scope" title="Choose where this upload is stored">''',
        "composer search selector",
    )
    frontend = replace_once(
        frontend,
        '''      <button type="button" class="settings-category-tab" role="tab" aria-selected="false" data-settings-target="responses">Responses</button>''',
        '''      <button type="button" class="settings-category-tab" role="tab" aria-selected="false" data-settings-target="responses">Responses</button>
      <button type="button" class="settings-category-tab" role="tab" aria-selected="false" data-settings-target="search">Search</button>''',
        "search settings tab",
    )
    frontend = replace_once(
        frontend,
        '''    <div class="settings-card" data-settings-category="instructions" hidden>''',
        '''    <div class="settings-card" data-settings-category="search" hidden>
      <h2>NATIVE WEB SEARCH</h2>
      <p>Allow ZBRANO to retrieve current public information through OpenAI's hosted web_search tool. Developer Mode remains isolated from public search.</p>
      <div class="settings-grid">
        <label class="toggle-row"><input id="web-search-enabled" type="checkbox" checked> Enable automatic Web Search</label>
        <div class="setting-field"><label for="web-search-context-size">Search context</label><select id="web-search-context-size"><option value="low">Low · quick lookups</option><option value="medium">Medium · balanced</option><option value="high">High · detailed searches</option></select><small>Higher context may increase latency and API usage.</small></div>
      </div>
      <p class="setting-note">Use Web · Auto in Chat to let ZBRANO decide, Search Web to require a search, or Web Off for a message that must not browse.</p>
    </div>
    <div class="settings-card" data-settings-category="instructions" hidden>''',
        "search settings card",
    )
    frontend = replace_once(
        frontend,
        '''const confirmationStrictness = document.getElementById("confirmation-strictness");''',
        '''const confirmationStrictness = document.getElementById("confirmation-strictness");
const webSearchMode = document.getElementById("web-search-mode");
const webSearchEnabled = document.getElementById("web-search-enabled");
const webSearchContextSize = document.getElementById("web-search-context-size");''',
        "search frontend controls",
    )
    frontend = replace_once(
        frontend,
        r'''function renderInlineMarkdown(text) {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}''',
        r'''function renderInlineMarkdown(text) {
  return escapeHtml(text)
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}''',
        "safe clickable Markdown links",
    )
    frontend = replace_once(
        frontend,
        '''    responseLength.value = jarvisPreferences.response_length || "balanced";
    confirmationStrictness.value = jarvisPreferences.confirmation_strictness || "standard";''',
        '''    responseLength.value = jarvisPreferences.response_length || "balanced";
    confirmationStrictness.value = jarvisPreferences.confirmation_strictness || "standard";
    webSearchEnabled.checked = jarvisPreferences.web_search_enabled !== false;
    webSearchContextSize.value = jarvisPreferences.web_search_context_size || "medium";''',
        "load search settings",
    )
    frontend = replace_once(
        frontend,
        '''        confirmation_strictness: confirmationStrictness.value,
        context_messages: Number(contextMessages.value),''',
        '''        confirmation_strictness: confirmationStrictness.value,
        web_search_enabled: webSearchEnabled.checked,
        web_search_context_size: webSearchContextSize.value,
        context_messages: Number(contextMessages.value),''',
        "save search settings",
    )
    frontend = replace_once(
        frontend,
        '''      message,
      attachment_ids: attachmentIds,
    }));''',
        '''      message,
      attachment_ids: attachmentIds,
      search_mode: webSearchMode?.value || "auto",
    }));''',
        "send per-message search mode",
    )
    frontend = replace_once(
        frontend,
        '''    } else if (eventData.type === "error") {''',
        r'''    } else if (eventData.type === "sources") {
      const sources = Array.isArray(eventData.sources) ? eventData.sources : [];
      const unique = sources.filter((source, index, items) => source?.url && items.findIndex(item => item?.url === source.url) === index);
      if (unique.length) {
        const sourceText = "\n\n### Sources\n" + unique.map(source => `- [${String(source.title || source.url).replaceAll("[", "").replaceAll("]", "")} ](${source.url})`).join("\n");
        answer += sourceText;
        renderMessageContent(jarvisMessage, answer);
        messages.scrollTop = messages.scrollHeight;
      }
    } else if (eventData.type === "error") {''',
        "render search sources",
    )
    frontend = replace_once(
        frontend,
        '''  .diagnostic-return-banner button { flex: 0 0 auto; }
</style>''',
        '''  .diagnostic-return-banner button { flex: 0 0 auto; }
  .message.jarvis a { color: var(--cyan); text-decoration: underline; text-underline-offset: .15em; overflow-wrap: anywhere; }
  #web-search-mode { min-width: 7.5rem; }
</style>''',
        "citation and search control style",
    )

    backend = backend.replace('version="0.12.25"', 'version="0.12.26"')
    backend = backend.replace('"version": "0.12.25"', '"version": "0.12.26"')
    frontend = frontend.replace("HUD 0.12.25", "HUD 0.12.26")

    require(backend, '"type": "web_search"', "hosted search tool")
    require(backend, '"web_search_call.action.sources"', "complete source inclusion")
    require(backend, "response_web_sources", "citation extraction")
    require(backend, 'search_mode: str = Field(default="auto"', "search request mode")
    require(frontend, 'id="web-search-mode"', "composer search selector")
    require(frontend, 'eventData.type === "sources"', "source rendering")
    require(frontend, 'target="_blank" rel="noopener noreferrer"', "safe citation links")
    require(backend, 'version="0.12.26"', "backend version")
    require(frontend, "HUD 0.12.26", "HUD version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
