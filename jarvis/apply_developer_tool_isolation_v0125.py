from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.5 patch missing: {label}")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")

    old_version_check = '''            version = str(health_payload.get("version") or "")
            add(
                "Application health and version",
                "operational" if response.status_code == 200 and version == "0.12.3" else "failed",
                f"HTTP {response.status_code}; runtime version {version or 'missing'}; expected 0.12.3",'''
    new_version_check = '''            version = str(health_payload.get("version") or "")
            expected_version = str(app.version)
            add(
                "Application health and version",
                "operational" if response.status_code == 200 and version == expected_version else "failed",
                f"HTTP {response.status_code}; runtime version {version or 'missing'}; expected {expected_version}",'''
    require(text, old_version_check, "dynamic version diagnostic")
    text = text.replace(old_version_check, new_version_check, 1)

    tools_marker = "def developer_runtime_tools() -> list[dict[str, Any]]:\n"
    require(text, tools_marker, "Developer tool registry")
    tool_isolation = r'''def developer_mcp_tools() -> list[dict[str, Any]]:
    """Expose only repository-capable GitHub MCP servers in Developer Mode."""
    return [
        tool for tool in active_mcp_tools()
        if _is_github_plugin(
            str(tool.get("server_url") or ""),
            str(tool.get("server_description") or tool.get("server_label") or ""),
        )
    ]


def runtime_chat_tools() -> list[dict[str, Any]]:
    if developer_mode_enabled():
        return developer_runtime_tools() + developer_mcp_tools()
    return WORKSHOP_TOOLS + active_mcp_tools()


'''
    text = text.replace(tools_marker, tool_isolation + tools_marker, 1)

    combined_tools = "WORKSHOP_TOOLS + developer_runtime_tools() + active_mcp_tools()"
    require(text, combined_tools, "combined chat tools")
    text = text.replace(combined_tools, "runtime_chat_tools()")

    old_allowlist = '    allowed_names = {tool["name"] for tool in WORKSHOP_TOOLS + developer_runtime_tools()}'
    new_allowlist = '''    allowed_function_tools = developer_runtime_tools() if developer_mode_enabled() else WORKSHOP_TOOLS
    allowed_names = {tool["name"] for tool in allowed_function_tools}'''
    require(text, old_allowlist, "function execution allow-list")
    text = text.replace(old_allowlist, new_allowlist, 1)

    local_route = "    local_result = await try_local_ha_route(message, session_id)"
    require(text, local_route, "local Home Assistant route")
    text = text.replace(
        local_route,
        "    local_result = None if developer_mode_enabled() else await try_local_ha_route(message, session_id)",
    )

    old_round_limit = "    max_tool_rounds = 5"
    require(text, old_round_limit, "tool round limits")
    text = text.replace(old_round_limit, "    max_tool_rounds = 12 if developer_mode_enabled() else 5")

    investigation_marker = "async def investigate_zbrano_feature(\n"
    require(text, investigation_marker, "targeted investigation")
    targeted_runner = r'''async def _targeted_developer_diagnostics(feature_key: str) -> dict[str, Any]:
    """Run one bounded feature adapter; never invoke the broad diagnostic suite."""
    checks: list[dict[str, Any]] = []

    def add(name: str, status: str, detail: str, category: str, repair_hint: str = "") -> None:
        checks.append({
            "name": name,
            "status": status,
            "ok": status != "failed",
            "detail": detail,
            "category": category,
            "repair_hint": repair_hint,
        })

    health_payload = await health()
    running_version = str(health_payload.get("version") or "")
    expected_version = str(app.version)
    add(
        "Application health and version",
        "operational" if running_version == expected_version else "failed",
        f"runtime version {running_version or 'missing'}; expected {expected_version}",
        "runtime",
        "Make every version check derive its expected value from app.version.",
    )

    route_paths = {str(getattr(route, "path", "")) for route in app.routes}
    feature_routes = {
        "attachments": ("/api/files/chat/{session_id}",),
        "shared_files": ("/api/files/shared",),
        "new_chat": ("/api/chats",),
        "plugin_catalog": ("/api/plugin-catalog",),
        "plugins": ("/api/plugins",),
        "entities": ("/api/ha/entities",),
        "settings": ("/api/settings",),
        "voice": ("/api/voice/transcribe", "/api/voice/speech"),
        "workshop_memory": ("/api/connections/status",),
        "developer": ("/api/developer/status", "/api/developer/investigate"),
    }
    required_routes = feature_routes.get(feature_key, ())
    missing_routes = [path for path in required_routes if path not in route_paths]
    add(
        f"{DEVELOPER_FEATURE_SPECS[feature_key]['title']} routes",
        "wired" if not missing_routes else "failed",
        "all targeted routes registered" if not missing_routes else f"missing: {', '.join(missing_routes)}",
        "api",
        "Inspect route registration and the latest patch-chain transformation.",
    )

    async def probe(name: str, operation, validator, category: str) -> None:
        try:
            payload = await asyncio.wait_for(operation(), timeout=8.0)
            ok, detail = validator(payload)
            add(name, "operational" if ok else "failed", detail, category)
        except asyncio.TimeoutError:
            add(name, "degraded", "targeted adapter timed out after 8 seconds", category)
        except Exception as exc:
            add(name, "failed", str(exc)[:500], category)

    if feature_key == "shared_files":
        await probe("Shared Files list operational", list_shared_files, lambda p: (isinstance(p.get("files"), list), f"{len(p.get('files', []))} shared files readable"), "files")
    elif feature_key == "new_chat":
        await probe("Conversations API operational", list_chats, lambda p: (isinstance(p.get("chats"), list), f"{len(p.get('chats', []))} conversations readable"), "chat")
    elif feature_key == "plugin_catalog":
        await probe("Plugin Catalog operational", plugin_catalog, lambda p: (isinstance(p.get("plugins"), list), f"{len(p.get('plugins', []))} catalog entries readable"), "plugins")
    elif feature_key == "plugins":
        await probe("Plugins API operational", list_plugins, lambda p: (isinstance(p.get("plugins"), list), f"{len(p.get('plugins', []))} installed plugins"), "plugins")
    elif feature_key == "entities":
        await probe("Entity inventory operational", list_ha_entities, lambda p: (isinstance(p.get("entities"), list), f"{len(p.get('entities', []))} entities returned"), "home_assistant")
    elif feature_key == "settings":
        await probe("Settings API operational", read_settings, lambda p: (isinstance(p.get("preferences"), dict), "preferences readable"), "settings")
    elif feature_key == "developer":
        await probe("Developer API operational", developer_status, lambda p: (p.get("repository") == DEVELOPER_REPOSITORY, f"repository={p.get('repository')}; deployment={p.get('deployment')}"), "developer")
        github_tools = developer_mcp_tools()
        add("Developer GitHub tools", "operational" if github_tools else "degraded", f"{len(github_tools)} GitHub MCP server(s) exposed; Workshop Memory tools excluded", "developer")
    elif feature_key == "workshop_memory":
        add("Workshop Memory configuration", "present" if WORKSHOP_MEMORY_URL else "degraded", "configuration inspected without calling Workshop Memory MCP tools", "integrations")
    elif feature_key == "voice":
        add("Voice configuration", "operational" if health_payload.get("voice_configured") else "degraded", f"provider={health_payload.get('speech_provider')}; configured={bool(health_payload.get('voice_configured'))}", "voice")

    return {"checks": checks, "scope": feature_key, "broad_diagnostics_run": False}


'''
    text = text.replace(investigation_marker, targeted_runner + investigation_marker, 1)
    old_diagnostics = "    diagnostics = await developer_diagnostics()"
    require(text, old_diagnostics, "broad investigation diagnostics")
    text = text.replace(
        old_diagnostics,
        "    diagnostics = await asyncio.wait_for(_targeted_developer_diagnostics(feature_key), timeout=20.0)",
        1,
    )

    old_instruction = "When the user reports that a ZBRANO feature is not working, call investigate_zbrano_feature even if general diagnostics are healthy."
    new_instruction = (
        "When the user reports that a ZBRANO feature is not working, call investigate_zbrano_feature exactly once for that report, even if general diagnostics are healthy. "
        "After it returns, do not call it again in the same turn; use only the returned evidence and GitHub repository tools. "
        "While Developer Mode is active, Workshop Memory, Home Assistant, and non-GitHub MCP tools are unavailable."
    )
    require(text, old_instruction, "Developer investigation instruction")
    text = text.replace(old_instruction, new_instruction, 1)

    text = text.replace('version="0.12.4"', 'version="0.12.5"')
    text = text.replace('"version": "0.12.4"', '"version": "0.12.5"')
    MAIN.write_text(text, encoding="utf-8")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    old_composer = '<input id="message" autocomplete="off" placeholder="Enter command…" required>'
    new_composer = '<textarea id="message" rows="1" autocomplete="off" placeholder="Enter command…" aria-label="Message ZBRANO" required></textarea>'
    require(text, old_composer, "single-line chat composer")
    text = text.replace(old_composer, new_composer, 1)

    form_marker = '        <form id="chat-form">'
    require(text, form_marker, "chat form")
    activity = '''        <div id="ai-activity" class="ai-activity" role="status" aria-live="polite" hidden>
          <span class="ai-activity-pulse" aria-hidden="true"></span>
          <span id="ai-activity-label">Thinking</span>
          <time id="ai-response-timer">00:00.0</time>
        </div>
'''
    text = text.replace(form_marker, activity + form_marker, 1)

    style_close = text.find("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.5 patch missing: style close")
    css = r'''
    #message {
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      resize: none;
      min-height: 3rem;
      max-height: 12rem;
      overflow-y: auto;
      line-height: 1.4;
      font: inherit;
    }
    #chat-form { align-items: flex-end; }
    .ai-activity {
      position: relative;
      z-index: 1;
      display: flex;
      align-items: center;
      gap: .5rem;
      min-height: 1.7rem;
      margin-top: .45rem;
      color: var(--cyan);
      font-size: .72rem;
      letter-spacing: .05em;
    }
    .ai-activity[hidden] { display: none; }
    .ai-activity-pulse {
      width: .55rem;
      height: .55rem;
      border-radius: 50%;
      background: var(--phosphor);
      box-shadow: 0 0 9px var(--phosphor);
      animation: ai-activity-pulse 1s ease-in-out infinite;
    }
    #ai-activity-label { min-width: 0; overflow-wrap: anywhere; }
    #ai-response-timer { margin-left: auto; color: var(--text-muted); font-variant-numeric: tabular-nums; white-space: nowrap; }
    @keyframes ai-activity-pulse { 50% { opacity: .3; transform: scale(.72); } }
    @media (prefers-reduced-motion: reduce) { .ai-activity-pulse { animation: none; } }
'''
    text = text[:style_close] + css + text[style_close:]

    constants = '''const stopButton = document.getElementById("stop-button");
const sendButton = document.getElementById("send-button");'''
    replacement_constants = '''const stopButton = document.getElementById("stop-button");
const aiActivity = document.getElementById("ai-activity");
const aiActivityLabel = document.getElementById("ai-activity-label");
const aiResponseTimer = document.getElementById("ai-response-timer");
const sendButton = document.getElementById("send-button");'''
    require(text, constants, "chat controls")
    text = text.replace(constants, replacement_constants, 1)

    active_request = '''let promptDraft = "";
let activeRequest = null;
'''
    activity_runtime = r'''let promptDraft = "";
let activeRequest = null;
let responseTimerId = null;
let responseStartedAt = 0;
let firstResponseSeconds = null;

function formatResponseTime(seconds) {
  const safe = Math.max(0, Number(seconds) || 0);
  const minutes = Math.floor(safe / 60);
  return `${String(minutes).padStart(2, "0")}:${(safe % 60).toFixed(1).padStart(4, "0")}`;
}

function updateResponseTimer() {
  if (!responseStartedAt) return;
  const elapsed = (performance.now() - responseStartedAt) / 1000;
  aiResponseTimer.textContent = firstResponseSeconds === null
    ? formatResponseTime(elapsed)
    : `first ${firstResponseSeconds.toFixed(1)}s · total ${formatResponseTime(elapsed)}`;
}

function startResponseActivity(label = "Thinking") {
  if (responseTimerId) window.clearInterval(responseTimerId);
  responseStartedAt = performance.now();
  firstResponseSeconds = null;
  aiActivity.hidden = false;
  aiActivityLabel.textContent = label;
  updateResponseTimer();
  responseTimerId = window.setInterval(updateResponseTimer, 100);
}

function setResponseActivity(label) {
  if (label) aiActivityLabel.textContent = label;
}

function markFirstResponse() {
  if (firstResponseSeconds !== null || !responseStartedAt) return;
  firstResponseSeconds = (performance.now() - responseStartedAt) / 1000;
  updateResponseTimer();
}

function finishResponseActivity(label = "Completed") {
  if (responseTimerId) window.clearInterval(responseTimerId);
  responseTimerId = null;
  updateResponseTimer();
  setResponseActivity(label);
}

function resizeComposer() {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 192)}px`;
}

input.addEventListener("input", resizeComposer);
resizeComposer();
'''
    require(text, active_request, "active chat request state")
    text = text.replace(active_request, activity_runtime, 1)

    old_history_handler = '''input.addEventListener("keydown", event => {
  if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
  if (!promptHistory.length) return;
  event.preventDefault();

  if (event.key === "ArrowUp") {
    if (promptHistoryIndex === promptHistory.length) promptDraft = input.value;
    promptHistoryIndex = Math.max(0, promptHistoryIndex - 1);
    input.value = promptHistory[promptHistoryIndex];
  } else {
    promptHistoryIndex = Math.min(promptHistory.length, promptHistoryIndex + 1);
    input.value = promptHistoryIndex === promptHistory.length
      ? promptDraft
      : promptHistory[promptHistoryIndex];
  }
  input.setSelectionRange(input.value.length, input.value.length);
});'''
    new_history_handler = '''input.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    form.requestSubmit();
    return;
  }
  if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
  if (input.value.includes("\\n") || !promptHistory.length) return;
  event.preventDefault();

  if (event.key === "ArrowUp") {
    if (promptHistoryIndex === promptHistory.length) promptDraft = input.value;
    promptHistoryIndex = Math.max(0, promptHistoryIndex - 1);
    input.value = promptHistory[promptHistoryIndex];
  } else {
    promptHistoryIndex = Math.min(promptHistory.length, promptHistoryIndex + 1);
    input.value = promptHistoryIndex === promptHistory.length
      ? promptDraft
      : promptHistory[promptHistoryIndex];
  }
  input.setSelectionRange(input.value.length, input.value.length);
  resizeComposer();
});'''
    require(text, old_history_handler, "prompt history keyboard handler")
    text = text.replace(old_history_handler, new_history_handler, 1)

    stop_marker = '''  stopAudioPlayback("STOPPED");
  stopButton.disabled = true;
});'''
    require(text, stop_marker, "Stop response handler")
    text = text.replace(
        stop_marker,
        '''  stopAudioPlayback("STOPPED");
  stopButton.disabled = true;
  finishResponseActivity("Stopped");
});''',
        1,
    )

    clear_composer = '''  input.value = "";
  input.disabled = true;'''
    require(text, clear_composer, "composer submission reset")
    text = text.replace(
        clear_composer,
        '''  input.value = "";
  resizeComposer();
  startResponseActivity("Thinking");
  input.disabled = true;''',
        1,
    )

    status_event = '''    if (eventData.type === "status") {
      statusText = eventData.message || "Working…";
      if (!answer) renderMessageContent(jarvisMessage, statusText);
    } else if (eventData.type === "delta") {
      if (!answer) renderMessageContent(jarvisMessage, "");'''
    status_replacement = '''    if (eventData.type === "status") {
      statusText = eventData.message || "Working…";
      setResponseActivity(statusText);
      if (!answer) renderMessageContent(jarvisMessage, statusText);
    } else if (eventData.type === "delta") {
      markFirstResponse();
      setResponseActivity("Responding…");
      if (!answer) renderMessageContent(jarvisMessage, "");'''
    require(text, status_event, "stream status handler")
    text = text.replace(status_event, status_replacement, 1)

    error_event = '''    } else if (eventData.type === "error") {
      renderMessageContent(jarvisMessage, `Request failed: ${eventData.message || "Unknown error"}`);'''
    require(text, error_event, "stream error handler")
    text = text.replace(
        error_event,
        '''    } else if (eventData.type === "error") {
      finishResponseActivity("Failed");
      renderMessageContent(jarvisMessage, `Request failed: ${eventData.message || "Unknown error"}`);''',
        1,
    )

    socket_error = '''  socket.addEventListener("error", () => {
    if (!answer) {'''
    require(text, socket_error, "socket error handler")
    text = text.replace(
        socket_error,
        '''  socket.addEventListener("error", () => {
    finishResponseActivity("Connection failed");
    if (!answer) {''',
        1,
    )

    close_marker = '''    if (activeRequest === requestState) activeRequest = null;
    input.disabled = false;'''
    require(text, close_marker, "socket close cleanup")
    text = text.replace(
        close_marker,
        '''    if (activeRequest === requestState) activeRequest = null;
    finishResponseActivity(requestState.stopped ? "Stopped" : (answer ? "Completed" : "No response"));
    input.disabled = false;''',
        1,
    )

    old_status = 'summary.textContent = "Running targeted investigation…";'
    new_status = 'summary.textContent = "Running one targeted adapter (maximum 20 seconds)…";'
    require(text, old_status, "investigation progress text")
    text = text.replace(old_status, new_status, 1)
    text = text.replace("HUD 0.12.4", "HUD 0.12.5")
    INDEX.write_text(text, encoding="utf-8")


def verify() -> None:
    main = MAIN.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    required_main = (
        'version="0.12.5"',
        "expected_version = str(app.version)",
        "def developer_mcp_tools()",
        "def runtime_chat_tools()",
        "return developer_runtime_tools() + developer_mcp_tools()",
        "allowed_function_tools = developer_runtime_tools() if developer_mode_enabled() else WORKSHOP_TOOLS",
        "None if developer_mode_enabled() else await try_local_ha_route",
        '"tools": runtime_chat_tools()',
        "async def _targeted_developer_diagnostics(feature_key: str)",
        "broad_diagnostics_run\": False",
        "timeout=20.0",
        "12 if developer_mode_enabled() else 5",
        "Workshop Memory, Home Assistant, and non-GitHub MCP tools are unavailable",
    )
    missing = [marker for marker in required_main if marker not in main]
    if "WORKSHOP_TOOLS + developer_runtime_tools() + active_mcp_tools()" in main:
        missing.append("combined Developer/Workshop toolset still present")
    if "HUD 0.12.5" not in index:
        missing.append("HUD 0.12.5")
    for marker in (
        '<textarea id="message"',
        'id="ai-activity"',
        'id="ai-response-timer"',
        "function startResponseActivity(",
        "function resizeComposer(",
        'event.key === "Enter" && !event.shiftKey',
        'setResponseActivity(statusText)',
        'markFirstResponse()',
    ):
        if marker not in index:
            missing.append(marker)
    if missing:
        raise RuntimeError("ZBRANO v0.12.5 verification failed: " + ", ".join(missing))


if __name__ == "__main__":
    patch_main()
    patch_index()
    verify()
