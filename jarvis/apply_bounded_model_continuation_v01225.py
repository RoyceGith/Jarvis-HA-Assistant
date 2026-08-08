import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"ZBRANO v0.12.25 patch expected one {label} marker; found {count}"
        )
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.25 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        "async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:",
        "async with httpx.AsyncClient(timeout=httpx.Timeout(210.0, connect=10.0)) as client:",
        "model stream transport timeout",
    )

    helper_marker = '''def active_agent_model() -> str:
'''
    progress_helpers = '''async def stream_openai_response_with_progress(
    payload: dict[str, Any],
    *,
    hard_timeout: float,
) -> AsyncIterator[dict[str, Any]]:
    """Keep a silent Responses stream observable and enforce its caller deadline."""
    stream = stream_openai_response(payload).__aiter__()
    pending = asyncio.create_task(stream.__anext__())
    started = time.monotonic()
    continuation = bool(payload.get("previous_response_id"))
    if developer_mode_enabled():
        phases = (
            [
                "Reviewing the diagnostic evidence...",
                "Waiting for Developer repository tools...",
                "Checking the supported repair path...",
                "Developer analysis is still active...",
            ]
            if continuation
            else [
                "Planning the Developer investigation...",
                "Waiting for the first diagnostic step...",
                "Developer analysis is still active...",
            ]
        )
    else:
        phases = [
            "Waiting for the model response...",
            "The request is still active...",
        ]
    phase_index = 0
    try:
        while True:
            elapsed = time.monotonic() - started
            remaining = hard_timeout - elapsed
            if remaining <= 0:
                pending.cancel()
                with contextlib.suppress(asyncio.CancelledError, StopAsyncIteration):
                    await pending
                raise OpenAIError(
                    f"Developer model/tool continuation timed out after {int(hard_timeout)} seconds. "
                    "The request was stopped safely; no unapproved repository write was performed."
                )
            try:
                event = await asyncio.wait_for(
                    asyncio.shield(pending),
                    timeout=min(10.0, remaining),
                )
            except asyncio.TimeoutError:
                elapsed_seconds = int(time.monotonic() - started)
                phase = phases[min(phase_index, len(phases) - 1)]
                phase_index += 1
                yield {
                    "type": "zbrano.progress",
                    "message": f"{phase} · {elapsed_seconds}s",
                }
                continue
            except StopAsyncIteration:
                break
            yield event
            pending = asyncio.create_task(stream.__anext__())
    finally:
        if not pending.done():
            pending.cancel()
        with contextlib.suppress(asyncio.CancelledError, StopAsyncIteration):
            await pending
        with contextlib.suppress(Exception):
            await stream.aclose()


def remote_mcp_progress(event: dict[str, Any]) -> str | None:
    event_type = str(event.get("type") or "")
    if event_type not in {"response.output_item.added", "response.output_item.done"}:
        return None
    item = event.get("item") if isinstance(event.get("item"), dict) else {}
    item_type = str(item.get("type") or "")
    if item_type == "mcp_list_tools":
        return "Loading Developer repository tools..."
    if item_type != "mcp_call":
        return None
    name = str(item.get("name") or "repository tool")
    if event_type.endswith(".done"):
        return f"Developer tool completed: {name}. Reviewing its result..."
    return f"Developer tool started: {name}..."


'''
    backend = replace_once(
        backend,
        helper_marker,
        progress_helpers + helper_marker,
        "model continuation progress helpers",
    )

    approval_call = '''        async for event in stream_openai_response(
            {
                "model": OPENAI_MODEL,
                "instructions": developer_system_instructions(effective_system_instructions()),
                "previous_response_id": pending_approval["response_id"],
                "input": approval_input,
                "tools": runtime_chat_tools(),
                "tool_choice": "auto",
            }
        ):'''
    approval_replacement = '''        async for event in stream_openai_response_with_progress(
            {
                "model": OPENAI_MODEL,
                "instructions": developer_system_instructions(effective_system_instructions()),
                "previous_response_id": pending_approval["response_id"],
                "input": approval_input,
                "tools": runtime_chat_tools(),
                "tool_choice": "auto",
            },
            hard_timeout=180.0,
        ):'''
    backend = replace_once(
        backend,
        approval_call,
        approval_replacement,
        "approved MCP continuation deadline",
    )

    approval_handler = '''            event_type = event.get("type")
            if event_type == "response.output_text.delta":
'''
    approval_handler_replacement = '''            event_type = event.get("type")
            if event_type == "zbrano.progress":
                yield stream_event("status", message=event.get("message") or "Approved Developer work is active...")
                continue
            remote_status = remote_mcp_progress(event)
            if remote_status:
                yield stream_event("status", message=remote_status)
            if event_type == "response.output_text.delta":
'''
    backend = replace_once(
        backend,
        approval_handler,
        approval_handler_replacement,
        "approved MCP progress handling",
    )

    request_state_marker = '''    audit: list[dict[str, Any]] = []
    max_tool_rounds = runtime_tool_round_limit(session_id)
    response: dict[str, Any] | None = None
    emitted_initial_text = False

    async for event in stream_openai_response(
'''
    request_state_replacement = '''    audit: list[dict[str, Any]] = []
    max_tool_rounds = runtime_tool_round_limit(session_id)
    response: dict[str, Any] | None = None
    emitted_initial_text = False
    request_deadline = time.monotonic() + (300.0 if developer_mode_enabled() else 180.0)

    async def bounded_model_stream(payload: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        remaining = request_deadline - time.monotonic()
        if remaining <= 0:
            raise OpenAIError(
                "The self-repair request reached its 5-minute safety limit. "
                "It was stopped without an unapproved repository write."
            )
        async for stream_item in stream_openai_response_with_progress(
            payload,
            hard_timeout=min(180.0, remaining),
        ):
            yield stream_item

    async for event in bounded_model_stream(
'''
    backend = replace_once(
        backend,
        request_state_marker,
        request_state_replacement,
        "overall request deadline",
    )

    initial_handler = '''        event_type = event.get("type")
        if event_type == "response.output_text.delta":
'''
    initial_handler_replacement = '''        event_type = event.get("type")
        if event_type == "zbrano.progress":
            yield stream_event("status", message=event.get("message") or "Developer analysis is active...")
            continue
        remote_status = remote_mcp_progress(event)
        if remote_status:
            yield stream_event("status", message=remote_status)
        if event_type == "response.output_text.delta":
'''
    backend = replace_once(
        backend,
        initial_handler,
        initial_handler_replacement,
        "initial model progress handling",
    )

    continuation_call = '''        async for event in stream_openai_response(
            {
                "model": active_agent_model(),
            **agent_reasoning_payload(),
                "instructions": developer_system_instructions(effective_system_instructions()),
                "previous_response_id": response["id"],
'''
    continuation_replacement = '''        async for event in bounded_model_stream(
            {
                "model": active_agent_model(),
            **agent_reasoning_payload(),
                "instructions": developer_system_instructions(effective_system_instructions()),
                "previous_response_id": response["id"],
'''
    backend = replace_once(
        backend,
        continuation_call,
        continuation_replacement,
        "post-tool bounded continuation",
    )

    continuation_handler = '''            event_type = event.get("type")

            if event_type == "response.output_text.delta":
'''
    continuation_handler_replacement = '''            event_type = event.get("type")

            if event_type == "zbrano.progress":
                yield stream_event("status", message=event.get("message") or "Developer analysis is active...")
                continue
            remote_status = remote_mcp_progress(event)
            if remote_status:
                yield stream_event("status", message=remote_status)

            if event_type == "response.output_text.delta":
'''
    backend = replace_once(
        backend,
        continuation_handler,
        continuation_handler_replacement,
        "continuation progress handling",
    )

    backend = backend.replace('version="0.12.24"', 'version="0.12.25"')
    backend = backend.replace('"version": "0.12.24"', '"version": "0.12.25"')
    frontend = frontend.replace("HUD 0.12.24", "HUD 0.12.25")

    require(backend, '"type": "zbrano.progress"', "stream heartbeat")
    require(backend, "request_deadline = time.monotonic() +", "overall request deadline")
    require(backend, "Developer tool started:", "remote MCP visibility")
    require(backend, "async for event in bounded_model_stream(", "bounded model stream")
    require(backend, "hard_timeout=180.0", "approved MCP deadline")
    require(backend, "5-minute safety limit", "overall timeout message")
    require(backend, 'version="0.12.25"', "backend version")
    require(frontend, "HUD 0.12.25", "HUD version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
