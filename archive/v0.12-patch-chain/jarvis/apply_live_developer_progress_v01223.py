import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(
            f"ZBRANO v0.12.23 patch expected one {label} marker; found {text.count(old)}"
        )
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.23 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        '''                elif name == "investigate_zbrano_feature":
                    result = await investigate_zbrano_feature(
                        arguments["feature"],
                        arguments["symptom"],
                    )''',
        '''                elif name == "investigate_zbrano_feature":
                    result = await asyncio.wait_for(
                        investigate_zbrano_feature(
                            arguments["feature"],
                            arguments["symptom"],
                        ),
                        timeout=30.0,
                    )''',
        "targeted investigation timeout",
    )
    backend = replace_once(
        backend,
        "except (MCPError, httpx.HTTPError, RuntimeError, PermissionError, ValueError) as exc:",
        "except (asyncio.TimeoutError, MCPError, httpx.HTTPError, RuntimeError, PermissionError, ValueError) as exc:",
        "tool timeout handling",
    )

    progress_helpers = '''def _tool_progress_phases(tool_names: list[str]) -> list[str]:
    if "investigate_zbrano_feature" in tool_names:
        return [
            "Checking the affected runtime layers...",
            "Reviewing targeted diagnostic evidence...",
            "Locating the likely fault boundary...",
        ]
    if "inspect_zbrano_ui_with_playwright" in tool_names:
        return [
            "Opening the local interface...",
            "Inspecting browser and network evidence...",
            "Reviewing the interface result...",
        ]
    return [
        "Waiting for the tool result...",
        "Reviewing returned evidence...",
        "The tool is taking longer than expected...",
    ]


def _tool_completion_status(tool_names: list[str], outputs: list[dict[str, Any]]) -> str:
    if "investigate_zbrano_feature" not in tool_names:
        return "Tool work complete. Reviewing the result..."
    for output in outputs:
        try:
            result = json.loads(str(output.get("output") or "{}"))
        except (TypeError, ValueError):
            continue
        if result.get("error"):
            return "Investigation stopped with an error. Preparing the details..."
        if result.get("status") in {"failed", "degraded"}:
            return "Problem confirmed. Reviewing the fault boundary..."
    return "Investigation complete. Reviewing the evidence..."


'''
    backend = replace_once(
        backend,
        "async def _run_jarvis_stream_events(message: str, session_id: str = \"default\") -> AsyncIterator[bytes]:",
        progress_helpers + "async def _run_jarvis_stream_events(message: str, session_id: str = \"default\") -> AsyncIterator[bytes]:",
        "progress helpers",
    )

    backend = replace_once(
        backend,
        '''        if all(name in local_ha_tools for name in tool_names_list):
            status_message = f"Using Home Assistant: {tool_names}…"
        else:
            status_message = f"Using tools: {tool_names}…"''',
        '''        if all(name in local_ha_tools for name in tool_names_list):
            status_message = f"Using Home Assistant: {tool_names}…"
        elif "investigate_zbrano_feature" in tool_names_list:
            status_message = "Investigating the reported feature..."
        elif "inspect_zbrano_ui_with_playwright" in tool_names_list:
            status_message = "Inspecting the ZBRANO interface..."
        else:
            status_message = f"Working with: {tool_names}…"''',
        "initial tool status",
    )

    old_execution = '''        tool_outputs = await execute_tool_calls(
            calls,
            audit,
            session_id,
            approved_workshop_call_ids=(
                workshop_write_call_ids(calls) if write_calls else set()
            ),
        )

        # Stream the next model response.'''
    new_execution = '''        tool_task = asyncio.create_task(
            execute_tool_calls(
                calls,
                audit,
                session_id,
                approved_workshop_call_ids=(
                    workshop_write_call_ids(calls) if write_calls else set()
                ),
            )
        )
        progress_started = time.monotonic()
        progress_phases = _tool_progress_phases(tool_names_list)
        progress_index = 0
        hard_timeout = 40.0 if "investigate_zbrano_feature" in tool_names_list else 90.0
        while not tool_task.done():
            elapsed = time.monotonic() - progress_started
            remaining = hard_timeout - elapsed
            if remaining <= 0:
                tool_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await tool_task
                raise OpenAIError(
                    f"Tool work timed out after {int(hard_timeout)} seconds. "
                    "No repository changes were made; retry or inspect the runtime log."
                )
            try:
                await asyncio.wait_for(asyncio.shield(tool_task), timeout=min(8.0, remaining))
            except asyncio.TimeoutError:
                elapsed_seconds = int(time.monotonic() - progress_started)
                phase = progress_phases[min(progress_index, len(progress_phases) - 1)]
                yield stream_event("status", message=f"{phase} · {elapsed_seconds}s")
                progress_index += 1
        tool_outputs = await tool_task
        yield stream_event(
            "status",
            message=_tool_completion_status(tool_names_list, tool_outputs),
        )

        # Stream the next model response.'''
    backend = replace_once(backend, old_execution, new_execution, "live tool execution progress")

    frontend = replace_once(
        frontend,
        '''let responseStartedAt = 0;
let firstResponseSeconds = null;''',
        '''let responseStartedAt = 0;
let firstResponseSeconds = null;
let responseActivityBaseLabel = "Working";
let responseActivityUpdatedAt = 0;''',
        "activity state",
    )
    frontend = replace_once(
        frontend,
        '''  aiResponseTimer.textContent = firstResponseSeconds === null
    ? formatResponseTime(elapsed)
    : `first ${firstResponseSeconds.toFixed(1)}s · total ${formatResponseTime(elapsed)}`;''',
        '''  aiResponseTimer.textContent = firstResponseSeconds === null
    ? formatResponseTime(elapsed)
    : `first ${firstResponseSeconds.toFixed(1)}s · total ${formatResponseTime(elapsed)}`;
  const quietSeconds = responseActivityUpdatedAt
    ? (performance.now() - responseActivityUpdatedAt) / 1000
    : 0;
  if (firstResponseSeconds === null && quietSeconds >= 20) {
    const suffix = quietSeconds >= 60
      ? "taking longer than expected; you can stop safely"
      : "still working";
    aiActivityLabel.textContent = `${responseActivityBaseLabel} · ${suffix}`;
  }''',
        "stale activity feedback",
    )
    frontend = replace_once(
        frontend,
        '''  firstResponseSeconds = null;
  aiActivity.hidden = false;
  aiActivityLabel.textContent = label;''',
        '''  firstResponseSeconds = null;
  responseActivityBaseLabel = label || "Thinking";
  responseActivityUpdatedAt = performance.now();
  aiActivity.hidden = false;
  aiActivityLabel.textContent = responseActivityBaseLabel;''',
        "activity start",
    )
    frontend = replace_once(
        frontend,
        '''function setResponseActivity(label) {
  if (label) aiActivityLabel.textContent = label;
}''',
        '''function setResponseActivity(label) {
  if (!label) return;
  responseActivityBaseLabel = label;
  responseActivityUpdatedAt = performance.now();
  aiActivityLabel.textContent = label;
}''',
        "activity update",
    )

    backend = backend.replace('version="0.12.22"', 'version="0.12.23"')
    backend = backend.replace('"version": "0.12.22"', '"version": "0.12.23"')
    frontend = frontend.replace("HUD 0.12.22", "HUD 0.12.23")

    require(backend, "Problem confirmed. Reviewing the fault boundary...", "confirmed-fault status")
    require(backend, "hard_timeout = 40.0", "developer hard timeout")
    require(frontend, "taking longer than expected; you can stop safely", "stale feedback")
    require(backend, 'version="0.12.23"', "backend version")
    require(frontend, "HUD 0.12.23", "HUD version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
