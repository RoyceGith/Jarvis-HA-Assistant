from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.12 patch missing: {label}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    require(text, old, label)
    return text.replace(old, new, 1)


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")

    pending_marker = "PENDING_WORKSHOP_APPROVALS: dict[str, dict[str, Any]] = {}\n"
    require(text, pending_marker, "task approval state")
    task_approval = r'''WORKSHOP_TASK_APPROVAL_GRANTS: dict[str, float] = {}
WORKSHOP_TASK_APPROVAL_SECONDS = 15 * 60


def workshop_memory_approval_decision(message: str) -> str | None:
    normalized = " ".join(message.strip().lower().split())
    if normalized in {
        "approve task", "approve this task", "approve workflow",
        "approve this workflow", "approve all for this task",
    }:
        return "task"
    if normalized in {
        "approve", "approved", "confirm", "yes", "yes approve", "proceed", "go ahead",
    }:
        return "once"
    if normalized in {"cancel", "deny", "denied", "no", "reject", "do not", "don't"}:
        return "deny"
    return None


def grant_workshop_memory_task_approval(session_id: str) -> None:
    WORKSHOP_TASK_APPROVAL_GRANTS[session_id] = (
        time.monotonic() + WORKSHOP_TASK_APPROVAL_SECONDS
    )


def workshop_memory_task_approval_active(session_id: str) -> bool:
    expires_at = float(WORKSHOP_TASK_APPROVAL_GRANTS.get(session_id) or 0)
    if expires_at <= time.monotonic():
        WORKSHOP_TASK_APPROVAL_GRANTS.pop(session_id, None)
        return False
    return True


def workshop_write_call_ids(calls: list[dict[str, Any]]) -> set[str]:
    return {
        str(call.get("call_id") or "")
        for call in workshop_memory_write_calls(calls)
    }


def summarize_workshop_memory_arguments(raw_arguments: Any) -> str:
    """Describe approval arguments without echoing large note bodies into chat."""
    if isinstance(raw_arguments, str):
        try:
            arguments = json.loads(raw_arguments)
        except json.JSONDecodeError:
            arguments = {"arguments": raw_arguments}
    else:
        arguments = raw_arguments

    content_keys = {
        "content", "body", "note", "note_content", "markdown",
        "template", "template_content", "text",
    }

    def summarize(value: Any, key: str = "", depth: int = 0) -> Any:
        if depth > 3:
            return "<nested value>"
        if isinstance(value, str):
            normalized_key = key.casefold()
            if normalized_key in content_keys or len(value) > 400:
                lines = value.count("\n") + (1 if value else 0)
                title = next(
                    (
                        line.lstrip("# ").strip()[:120]
                        for line in value.splitlines()
                        if line.strip().startswith("#") and line.lstrip("# ").strip()
                    ),
                    "",
                )
                label = "note content" if normalized_key in content_keys else "large text"
                description = f"<{label}: {len(value)} characters, {lines} lines"
                if title:
                    description += f"; title: {title}"
                return description + ">"
            return value
        if isinstance(value, list):
            if len(value) > 12:
                return f"<list with {len(value)} items>"
            return [summarize(item, key, depth + 1) for item in value]
        if isinstance(value, dict):
            items = list(value.items())
            result = {
                str(item_key): summarize(item_value, str(item_key), depth + 1)
                for item_key, item_value in items[:16]
            }
            if len(items) > 16:
                result["additional_fields"] = len(items) - 16
            return result
        return value

    summary = summarize(arguments)
    rendered = json.dumps(summary, ensure_ascii=False, separators=(",", ":"))
    return rendered if len(rendered) <= 1000 else rendered[:1000] + "…"


'''
    text = text.replace(pending_marker, pending_marker + task_approval, 1)

    old_prompt = '    lines.append("Reply **approve** to execute exactly these changes or **cancel** to deny them.")'
    new_prompt = '''    lines.append("Reply **approve** for this write, **approve task** to allow Workshop Memory writes in this chat for 15 minutes, or **cancel** to deny.")'''
    text = replace_once(text, old_prompt, new_prompt, "approval choices")

    old_arguments = '''        arguments = str(call.get("arguments") or "{}")
        if len(arguments) > 900:
            arguments = arguments[:900] + "…"
        lines.append(f"- `{name}` with `{arguments}`")'''
    new_arguments = '''        arguments = summarize_workshop_memory_arguments(
            call.get("arguments") or "{}"
        )
        lines.append(f"- `{name}` with `{arguments}`")'''
    text = replace_once(text, old_arguments, new_arguments, "private approval summary")

    helper_followup = '''        if workshop_memory_write_calls(calls):
            prompt = store_workshop_memory_approval(session_id, response["id"], calls)
            return {"reply": prompt, "tool_calls": audit}
        tool_outputs = await execute_tool_calls(calls, audit, session_id)'''
    helper_replacement = '''        write_calls = workshop_memory_write_calls(calls)
        if write_calls and not workshop_memory_task_approval_active(session_id):
            prompt = store_workshop_memory_approval(session_id, response["id"], calls)
            return {"reply": prompt, "tool_calls": audit}
        tool_outputs = await execute_tool_calls(
            calls,
            audit,
            session_id,
            approved_workshop_call_ids=(
                workshop_write_call_ids(calls) if write_calls else set()
            ),
        )'''
    text = replace_once(text, helper_followup, helper_replacement, "task-approved continuation")

    old_decision = '''    workshop_decision = mcp_approval_decision(message)
    if pending_workshop and workshop_decision is not None:
        PENDING_WORKSHOP_APPROVALS.pop(session_id, None)
        result = await continue_workshop_memory_approval(
            pending_workshop, workshop_decision, session_id
        )'''
    new_decision = '''    workshop_decision = workshop_memory_approval_decision(message)
    if pending_workshop and workshop_decision is not None:
        PENDING_WORKSHOP_APPROVALS.pop(session_id, None)
        if workshop_decision == "task":
            grant_workshop_memory_task_approval(session_id)
        elif workshop_decision == "deny":
            WORKSHOP_TASK_APPROVAL_GRANTS.pop(session_id, None)
        result = await continue_workshop_memory_approval(
            pending_workshop, workshop_decision in {"once", "task"}, session_id
        )'''
    text = replace_once(text, old_decision, new_decision, "non-stream task decision")

    run_gate = '''        if workshop_memory_write_calls(calls):
            prompt = store_workshop_memory_approval(session_id, response["id"], calls)
            append_chat_message(session_id, "user", message)
            append_chat_message(session_id, "assistant", prompt)
            return {"reply": prompt, "tool_calls": audit}

        tool_outputs = await execute_tool_calls(calls, audit, session_id)'''
    run_replacement = '''        write_calls = workshop_memory_write_calls(calls)
        if write_calls and not workshop_memory_task_approval_active(session_id):
            prompt = store_workshop_memory_approval(session_id, response["id"], calls)
            append_chat_message(session_id, "user", message)
            append_chat_message(session_id, "assistant", prompt)
            return {"reply": prompt, "tool_calls": audit}

        tool_outputs = await execute_tool_calls(
            calls,
            audit,
            session_id,
            approved_workshop_call_ids=(
                workshop_write_call_ids(calls) if write_calls else set()
            ),
        )'''
    text = replace_once(text, run_gate, run_replacement, "non-stream task grant")

    stream_decision = '''    workshop_decision = mcp_approval_decision(message)
    if pending_workshop and workshop_decision is not None:
        PENDING_WORKSHOP_APPROVALS.pop(session_id, None)
        yield stream_event(
            "status",
            message="Executing approved Workshop Memory change…" if workshop_decision else "Denying Workshop Memory change…",
        )
        result = await continue_workshop_memory_approval(
            pending_workshop, workshop_decision, session_id
        )'''
    stream_decision_replacement = '''    workshop_decision = workshop_memory_approval_decision(message)
    if pending_workshop and workshop_decision is not None:
        PENDING_WORKSHOP_APPROVALS.pop(session_id, None)
        if workshop_decision == "task":
            grant_workshop_memory_task_approval(session_id)
        elif workshop_decision == "deny":
            WORKSHOP_TASK_APPROVAL_GRANTS.pop(session_id, None)
        approved = workshop_decision in {"once", "task"}
        yield stream_event(
            "status",
            message="Executing approved Workshop Memory change…" if approved else "Denying Workshop Memory change…",
        )
        result = await continue_workshop_memory_approval(
            pending_workshop, approved, session_id
        )'''
    text = replace_once(text, stream_decision, stream_decision_replacement, "stream task decision")

    stream_gate = '''        if workshop_memory_write_calls(calls):
            prompt = store_workshop_memory_approval(session_id, response["id"], calls)
            yield stream_event("status", message="Permission required…")
            yield stream_event("delta", text=prompt)
            yield stream_event("done", tool_calls=audit)
            return

        tool_outputs = await execute_tool_calls(calls, audit, session_id)'''
    stream_gate_replacement = '''        write_calls = workshop_memory_write_calls(calls)
        if write_calls and not workshop_memory_task_approval_active(session_id):
            prompt = store_workshop_memory_approval(session_id, response["id"], calls)
            yield stream_event("status", message="Permission required…")
            yield stream_event("delta", text=prompt)
            yield stream_event("done", tool_calls=audit)
            return

        tool_outputs = await execute_tool_calls(
            calls,
            audit,
            session_id,
            approved_workshop_call_ids=(
                workshop_write_call_ids(calls) if write_calls else set()
            ),
        )'''
    text = replace_once(text, stream_gate, stream_gate_replacement, "stream task grant")

    policy_marker = '''save_general_instruction as a substitute for a project note.'''
    policy_replacement = '''save_general_instruction as a substitute for a project note. Prefer one generic
write_project_note call when the user requests a Markdown note beneath Projects;
that tool can create missing folders and the note in one approved operation.'''
    text = replace_once(text, policy_marker, policy_replacement, "generic note guidance")

    text = text.replace('version="0.12.11"', 'version="0.12.12"')
    text = text.replace('"version": "0.12.11"', '"version": "0.12.12"')
    MAIN.write_text(text, encoding="utf-8")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")
    text = text.replace("HUD 0.12.11", "HUD 0.12.12")
    INDEX.write_text(text, encoding="utf-8")


def verify() -> None:
    main = MAIN.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    required_main = (
        'version="0.12.12"',
        "WORKSHOP_TASK_APPROVAL_GRANTS",
        "WORKSHOP_TASK_APPROVAL_SECONDS = 15 * 60",
        'return "task"',
        "grant_workshop_memory_task_approval",
        "workshop_memory_task_approval_active",
        "workshop_write_call_ids",
        "summarize_workshop_memory_arguments",
        'label = "note content"',
        'title: {title}',
        "**approve task**",
        'workshop_decision in {"once", "task"}',
        "Prefer one generic\nwrite_project_note call",
    )
    missing = [marker for marker in required_main if marker not in main]
    if "HUD 0.12.12" not in index:
        missing.append("HUD 0.12.12")
    if missing:
        raise RuntimeError("ZBRANO v0.12.12 verification failed: " + ", ".join(missing))


if __name__ == "__main__":
    patch_main()
    patch_index()
    verify()
