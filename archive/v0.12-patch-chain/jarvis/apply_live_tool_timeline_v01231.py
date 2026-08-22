import os
import re
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.31 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.31 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend_helpers = '''def openai_tool_activity(event: dict[str, Any]) -> dict[str, str] | None:
    """Translate real Responses API tool events into safe UI activity metadata."""
    event_type = str(event.get("type") or "")
    item = event.get("item") if isinstance(event.get("item"), dict) else {}
    item_type = str(item.get("type") or "")
    if "web_search_call" in event_type or item_type == "web_search_call":
        state = "completed" if event_type.endswith((".completed", ".done")) else "started"
        return {
            "id": "native-web-search",
            "label": "Searching web",
            "state": state,
            "provider": "web",
            "plugin_id": "",
        }
    if item_type == "mcp_approval_request":
        label = str(item.get("name") or "Plugin action")[:120]
        server_label = str(item.get("server_label") or "")
        return {
            "id": str(item.get("id") or f"approval-{server_label}-{label}")[:180],
            "label": label,
            "state": "waiting_approval",
            "provider": "plugin",
            "plugin_id": server_label.removeprefix("plugin_"),
        }
    if item_type != "mcp_call" or event_type not in {"response.output_item.added", "response.output_item.done"}:
        return None
    name = str(item.get("name") or "Plugin tool")[:120]
    server_label = str(item.get("server_label") or "")
    state = "completed" if event_type.endswith(".done") else "started"
    return {
        "id": str(item.get("id") or f"mcp-{server_label}-{name}")[:180],
        "label": name.replace("_", " "),
        "state": state,
        "provider": "plugin",
        "plugin_id": server_label.removeprefix("plugin_"),
    }


def local_tool_activity(tool_names: list[str], *, writing: bool = False) -> dict[str, str]:
    local_ha = {
        "find_home_assistant_entities", "get_home_assistant_state",
        "turn_on_home_assistant_entity", "turn_off_home_assistant_entity",
    }
    if tool_names and all(name in local_ha for name in tool_names):
        return {"label": "Reading Home Assistant", "provider": "home_assistant", "plugin_id": ""}
    if "inspect_zbrano_ui_with_playwright" in tool_names:
        return {"label": "Inspecting ZBRANO interface", "provider": "developer", "plugin_id": "builtin-playwright"}
    if "investigate_zbrano_feature" in tool_names:
        return {"label": "Investigating ZBRANO", "provider": "developer", "plugin_id": ""}
    workshop_terms = ("project", "note", "memory", "handoff", "template", "reorganization", "progress")
    if any(any(term in name.lower() for term in workshop_terms) for name in tool_names):
        label = "Updating Workshop Memory" if writing else "Reading Workshop Memory"
        return {"label": label, "provider": "workshop_memory", "plugin_id": ""}
    readable = ", ".join(name.replace("_", " ") for name in tool_names[:3]) or "Tool work"
    return {"label": readable, "provider": "tool", "plugin_id": ""}


'''
    backend = replace_once(
        backend,
        "def remote_mcp_progress(event: dict[str, Any]) -> str | None:\n",
        backend_helpers + "def remote_mcp_progress(event: dict[str, Any]) -> str | None:\n",
        "tool activity helpers",
    )

    def add_activity_hook(match: re.Match[str]) -> str:
        indent = match.group(1)
        return (
            f'{indent}activity = openai_tool_activity(event)\n'
            f'{indent}if activity:\n'
            f'{indent}    yield stream_event("activity", **activity)\n'
            f'{indent}remote_status = remote_mcp_progress(event)'
        )

    backend, hook_count = re.subn(
        r'^(\s*)remote_status = remote_mcp_progress\(event\)$',
        add_activity_hook,
        backend,
        flags=re.MULTILINE,
    )
    if hook_count != 3:
        raise RuntimeError(f"ZBRANO v0.12.31 patch expected three streaming activity hooks; found {hook_count}")

    backend = replace_once(
        backend,
        '''        yield stream_event("status", message=status_message)

        write_calls = workshop_memory_write_calls(calls)
        if write_calls and not workshop_memory_task_approval_active(session_id):''',
        '''        yield stream_event("status", message=status_message)
        activity_id = f"function-round-{round_index}"
        write_calls = workshop_memory_write_calls(calls)
        activity_meta = local_tool_activity(tool_names_list, writing=bool(write_calls))
        yield stream_event("activity", id=activity_id, state="started", **activity_meta)

        if write_calls and not workshop_memory_task_approval_active(session_id):
            yield stream_event("activity", id=activity_id, state="waiting_approval", **activity_meta)''',
        "local tool start activity",
    )
    backend = replace_once(
        backend,
        '''        tool_outputs = await tool_task
        yield stream_event(
            "status",
            message=_tool_completion_status(tool_names_list, tool_outputs),
        )''',
        '''        tool_outputs = await tool_task
        failed = any('"error"' in str(output.get("output") or "") for output in tool_outputs)
        yield stream_event("activity", id=activity_id, state="failed" if failed else "completed", **activity_meta)
        yield stream_event(
            "status",
            message=_tool_completion_status(tool_names_list, tool_outputs),
        )''',
        "local tool completion activity",
    )
    backend = replace_once(
        backend,
        '''        yield stream_event("done", tool_calls=[])
        return

    local_result = None if developer_mode_enabled() else await try_local_ha_route(message, session_id)
    if local_result:
''',
        '''        yield stream_event("done", tool_calls=[])
        return

    local_result = None if developer_mode_enabled() else await try_local_ha_route(message, session_id)
    if local_result:
        yield stream_event("activity", id="local-home-assistant", label="Reading Home Assistant", state="completed", provider="home_assistant", plugin_id="")
''',
        "direct Home Assistant activity",
    )

    timeline_css = '''    .tool-timeline {
      display: flex; flex-wrap: wrap; gap: .35rem; margin: .35rem 0 .45rem; min-width: 0;
    }
    .tool-timeline[hidden] { display: none; }
    .tool-activity {
      display: inline-flex; align-items: center; gap: .35rem; max-width: 100%;
      border: 1px solid var(--line); border-radius: 999px; padding: .24rem .55rem;
      background: color-mix(in srgb, var(--panel) 88%, transparent); color: var(--text-muted);
      font-size: .72rem; line-height: 1.2;
    }
    .tool-activity-label { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .tool-activity-time { font-variant-numeric: tabular-nums; white-space: nowrap; }
    .tool-activity-dot { width: .45rem; height: .45rem; flex: 0 0 auto; border-radius: 50%; background: var(--cyan); }
    .tool-activity[data-state="started"] .tool-activity-dot { animation: ai-activity-pulse 1s ease-in-out infinite; }
    .tool-activity[data-state="completed"] .tool-activity-dot { background: #2faa76; }
    .tool-activity[data-state="failed"] .tool-activity-dot { background: #d35d62; }
    .tool-activity[data-state="waiting_approval"] { border-color: #c99b35; color: var(--text); }
    .tool-activity[data-state="waiting_approval"] .tool-activity-dot { background: #c99b35; }
    .composer-plugin-button.tool-active { border-color: var(--cyan); box-shadow: 0 0 0 .12rem color-mix(in srgb, var(--cyan) 24%, transparent); }
    .composer-plugin-button.tool-active img,.composer-plugin-button.tool-active .composer-plugin-fallback { animation: plugin-tool-pulse .8s ease-in-out infinite alternate; }
    @keyframes plugin-tool-pulse { to { transform: scale(1.15); filter: brightness(1.25); } }
    .attachment-controls {
      gap: .4rem; min-height: 2.25rem; padding: .35rem .15rem .2rem;
      color: var(--text-muted); font-size: .72rem;
    }
    .attachment-controls #attach-file,.attachment-controls #attachment-scope {
      box-sizing: border-box; min-height: 1.9rem; height: 1.9rem; margin: 0;
      border: 1px solid var(--line); border-radius: 999px;
      background: color-mix(in srgb, var(--surface-strong) 82%, transparent);
      color: var(--text); font-size: .72rem; font-weight: 500; line-height: 1;
    }
    .attachment-controls #attach-file {
      display: inline-flex; align-items: center; justify-content: center; gap: .3rem;
      min-width: 5rem; padding: .25rem .7rem; box-shadow: none;
    }
    .attachment-controls #attachment-scope {
      min-width: 9.6rem; max-width: min(13rem, 48vw); padding: .25rem 1.7rem .25rem .65rem;
    }
    .attachment-controls #attach-file:hover,.attachment-controls #attach-file:focus-visible,
    .attachment-controls #attachment-scope:hover,.attachment-controls #attachment-scope:focus-visible {
      border-color: var(--cyan); transform: none; box-shadow: none;
    }
    .attachment-controls #attachment-state { overflow-wrap: anywhere; }
    @media (prefers-reduced-motion: reduce) { .tool-activity-dot,.composer-plugin-button.tool-active img,.composer-plugin-button.tool-active .composer-plugin-fallback { animation: none !important; } }
'''
    frontend = replace_once(
        frontend,
        '''    @media (prefers-reduced-motion: reduce) { .ai-activity-pulse { animation: none; } }
''',
        '''    @media (prefers-reduced-motion: reduce) { .ai-activity-pulse { animation: none; } }
''' + timeline_css,
        "tool timeline styling",
    )
    frontend = replace_once(
        frontend,
        '''        </div>
        <form id="chat-form">
          <div class="composer-input-stack">''',
        '''        </div>
        <div id="tool-timeline" class="tool-timeline" aria-label="Tool activity" aria-live="polite" hidden></div>
        <form id="chat-form">
          <div class="composer-input-stack">''',
        "tool timeline container",
    )
    frontend = replace_once(
        frontend,
        '''const aiResponseTimer = document.getElementById("ai-response-timer");
const sendButton''',
        '''const aiResponseTimer = document.getElementById("ai-response-timer");
const toolTimeline = document.getElementById("tool-timeline");
const toolActivities = new Map();
const sendButton''',
        "tool timeline state",
    )

    timeline_js = '''
function formatToolElapsed(milliseconds) {
  const seconds = Math.max(0, milliseconds) / 1000;
  return seconds < 10 ? `${seconds.toFixed(1)}s` : `${Math.round(seconds)}s`;
}

function setPluginToolActive(pluginId, active) {
  if (!pluginId) return;
  const button = [...document.querySelectorAll("[data-composer-plugin]")]
    .find(item => item.dataset.composerPlugin === pluginId);
  button?.classList.toggle("tool-active", active);
}

function resetToolTimeline() {
  for (const activity of toolActivities.values()) setPluginToolActive(activity.pluginId, false);
  toolActivities.clear();
  toolTimeline.replaceChildren();
  toolTimeline.hidden = true;
}

function updateToolTimelineClock() {
  const now = performance.now();
  for (const activity of toolActivities.values()) {
    const elapsed = (activity.finishedAt || now) - activity.startedAt;
    activity.time.textContent = formatToolElapsed(elapsed);
  }
}

function applyToolActivity(eventData) {
  const id = String(eventData.id || `${eventData.provider || "tool"}-${eventData.label || "activity"}`);
  const state = String(eventData.state || "started");
  let activity = toolActivities.get(id);
  if (!activity) {
    const item = document.createElement("span");
    item.className = "tool-activity";
    const dot = document.createElement("span");
    dot.className = "tool-activity-dot";
    dot.setAttribute("aria-hidden", "true");
    const label = document.createElement("span");
    label.className = "tool-activity-label";
    const time = document.createElement("time");
    time.className = "tool-activity-time";
    item.append(dot, label, time);
    activity = {item, label, time, startedAt: performance.now(), finishedAt: null, pluginId: ""};
    toolActivities.set(id, activity);
    toolTimeline.append(item);
    while (toolTimeline.children.length > 8) toolTimeline.firstElementChild?.remove();
  }
  if (activity.pluginId && activity.pluginId !== eventData.plugin_id) setPluginToolActive(activity.pluginId, false);
  activity.pluginId = String(eventData.plugin_id || "");
  activity.label.textContent = String(eventData.label || "Tool activity");
  activity.item.dataset.state = state;
  activity.finishedAt = ["completed", "failed"].includes(state) ? performance.now() : null;
  const active = state === "started";
  setPluginToolActive(activity.pluginId, active);
  const stateLabel = state === "waiting_approval" ? "approval required" : state;
  activity.item.title = `${activity.label.textContent} · ${stateLabel}`;
  toolTimeline.hidden = false;
  updateToolTimelineClock();
}

function finishOpenToolActivities(state = "completed") {
  for (const activity of toolActivities.values()) {
    if (activity.item.dataset.state !== "started") continue;
    activity.item.dataset.state = state;
    activity.finishedAt = performance.now();
    setPluginToolActive(activity.pluginId, false);
  }
  updateToolTimelineClock();
}
'''
    frontend = replace_once(
        frontend,
        '''function resizeComposer() {''',
        timeline_js + '''
function resizeComposer() {''',
        "tool timeline behavior",
    )
    frontend = replace_once(
        frontend,
        '''  startResponseActivity("Thinking");
  input.disabled = true;''',
        '''  resetToolTimeline();
  startResponseActivity("Thinking");
  input.disabled = true;''',
        "timeline request reset",
    )
    frontend = replace_once(
        frontend,
        '''    if (eventData.type === "status") {
      statusText''',
        '''    if (eventData.type === "activity") {
      applyToolActivity(eventData);
    } else if (eventData.type === "status") {
      statusText''',
        "activity stream handling",
    )
    frontend = replace_once(
        frontend,
        '''    } else if (eventData.type === "error") {
      finishResponseActivity("Failed");''',
        '''    } else if (eventData.type === "error") {
      finishOpenToolActivities("failed");
      finishResponseActivity("Failed");''',
        "failed activity completion",
    )
    frontend = replace_once(
        frontend,
        '''    finishResponseActivity(requestState.stopped ? "Stopped" : (answer ? "Completed" : "No response"));
    input.disabled''',
        '''    finishOpenToolActivities(requestState.stopped ? "failed" : "completed");
    finishResponseActivity(requestState.stopped ? "Stopped" : (answer ? "Completed" : "No response"));
    input.disabled''',
        "closed activity completion",
    )
    frontend = replace_once(
        frontend,
        '''  updateResponseTimer();
  responseTimerId = window.setInterval(updateResponseTimer, 100);''',
        '''  updateResponseTimer();
  responseTimerId = window.setInterval(() => { updateResponseTimer(); updateToolTimelineClock(); }, 100);''',
        "timeline clock",
    )

    backend = backend.replace('version="0.12.30"', 'version="0.12.31"')
    backend = backend.replace('"version": "0.12.30"', '"version": "0.12.31"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.30"', '"X-ZBRANO-Frontend-Version": "0.12.31"')
    frontend = frontend.replace("HUD 0.12.30", "HUD 0.12.31")

    require(backend, "def openai_tool_activity", "OpenAI activity translator")
    require(backend, 'yield stream_event("activity", **activity)', "streamed activity metadata")
    require(frontend, 'id="tool-timeline"', "tool timeline")
    require(frontend, "function applyToolActivity", "tool activity renderer")
    require(frontend, 'classList.toggle("tool-active"', "active plugin indicator")
    require(frontend, ".attachment-controls #attach-file,.attachment-controls #attachment-scope", "compact attachment controls")
    require(backend, 'version="0.12.31"', "backend version")
    require(frontend, "HUD 0.12.31", "HUD version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
