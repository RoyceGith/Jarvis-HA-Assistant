from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.64 expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        '''async def continue_workshop_memory_approval(
    pending: dict[str, Any],
    approved: bool,
    session_id: str,
) -> dict[str, Any]:''',
        '''async def continue_workshop_memory_approval(
    pending: dict[str, Any],
    approved: bool,
    session_id: str,
    approval_message: str,
) -> dict[str, Any]:''',
        "Workshop Memory approval continuation signature",
    )

    start = backend.find("async def continue_workshop_memory_approval(")
    end = backend.find("\n\nPENDING_MCP_APPROVALS:", start)
    if start < 0 or end < 0:
        raise RuntimeError("ZBRANO v0.12.64 could not isolate the approval continuation")
    continuation = backend[start:end]
    instruction_references = continuation.count(
        "priority_system_instructions(effective_system_instructions(), message)"
    )
    tool_references = continuation.count("runtime_chat_tools(message=message)")
    if instruction_references != 2 or tool_references != 2:
        raise RuntimeError(
            "ZBRANO v0.12.64 expected two instruction and two tool message references; "
            f"found {instruction_references} and {tool_references}"
        )
    continuation = continuation.replace(
        "priority_system_instructions(effective_system_instructions(), message)",
        "priority_system_instructions(effective_system_instructions(), approval_message)",
    )
    continuation = continuation.replace(
        "runtime_chat_tools(message=message)",
        "runtime_chat_tools(message=approval_message)",
    )
    if "(), message)" in continuation or "message=message" in continuation:
        raise RuntimeError("ZBRANO v0.12.64 left an undefined message reference in the approval continuation")
    backend = backend[:start] + continuation + backend[end:]

    old_call = '''        result = await continue_workshop_memory_approval(
            pending_workshop, workshop_decision in {"once", "task"}, session_id
        )'''
    new_call = '''        result = await continue_workshop_memory_approval(
            pending_workshop,
            workshop_decision in {"once", "task"},
            session_id,
            message,
        )'''
    backend = replace_once(backend, old_call, new_call, "non-streaming approval call")

    old_stream_call = '''        result = await continue_workshop_memory_approval(
            pending_workshop, approved, session_id
        )'''
    new_stream_call = '''        result = await continue_workshop_memory_approval(
            pending_workshop,
            approved,
            session_id,
            message,
        )'''
    backend = replace_once(backend, old_stream_call, new_stream_call, "streaming approval call")

    backend = backend.replace('version="0.12.63"', 'version="0.12.64"')
    backend = backend.replace('"version": "0.12.63"', '"version": "0.12.64"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.63"', '"X-ZBRANO-Frontend-Version": "0.12.64"')
    backend = backend.replace(
        '"name": "ZBRANO Developer Mode", "version": "0.12.63"',
        '"name": "ZBRANO Developer Mode", "version": "0.12.64"',
    )
    frontend = frontend.replace("HUD 0.12.63", "HUD 0.12.64")

    required_backend = (
        "approval_message: str",
        "priority_system_instructions(effective_system_instructions(), approval_message)",
        "runtime_chat_tools(message=approval_message)",
        'version="0.12.64"',
    )
    missing = [marker for marker in required_backend if marker not in backend]
    if missing:
        raise RuntimeError("ZBRANO v0.12.64 verification failed: " + ", ".join(missing))
    if "HUD 0.12.64" not in frontend:
        raise RuntimeError("ZBRANO v0.12.64 frontend version was not updated")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
