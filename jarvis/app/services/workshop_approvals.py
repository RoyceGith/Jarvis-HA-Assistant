from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any


PENDING_WORKSHOP_APPROVALS: dict[str, dict[str, Any]] = {}
WORKSHOP_TASK_APPROVAL_GRANTS: dict[str, float] = {}
WORKSHOP_TASK_APPROVAL_SECONDS = 15 * 60

_tool_permission: Callable[[str], str] = lambda name: "read_only"
_gmail_write_calls: Callable[[list[dict[str, Any]]], list[dict[str, Any]]] = lambda calls: []


def configure_workshop_approvals(
    *,
    tool_permission_fn: Callable[[str], str],
    gmail_write_calls_fn: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
) -> None:
    global _tool_permission, _gmail_write_calls
    _tool_permission = tool_permission_fn
    _gmail_write_calls = gmail_write_calls_fn


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


def workshop_memory_write_calls(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        call for call in calls
        if _tool_permission(str(call.get("name") or "")) == "write"
    ]


def workshop_memory_approval_prompt(calls: list[dict[str, Any]]) -> str:
    writes = workshop_memory_write_calls(calls)
    gmail_writes = _gmail_write_calls(calls)
    lines = [
        "Gmail Direct is requesting permission to create an unsent draft:"
        if gmail_writes else
        "Workshop Memory is requesting permission to change permanent project data:"
    ]
    for call in writes[:5]:
        name = str(call.get("name") or "unknown tool")
        arguments = summarize_workshop_memory_arguments(call.get("arguments") or "{}")
        lines.append(f"- `{name}` with `{arguments}`")
    if len(writes) > 5:
        lines.append(f"- …and {len(writes) - 5} more change(s)")
    lines.append(
        "The message will remain a draft and will not be sent. Reply **approve** to create it or **cancel** to deny."
        if gmail_writes else
        "Reply **approve** for this write, **approve task** to allow Workshop Memory writes in this chat for 15 minutes, or **cancel** to deny."
    )
    return "\n".join(lines)


def store_workshop_memory_approval(
    session_id: str,
    response_id: str,
    calls: list[dict[str, Any]],
) -> str:
    PENDING_WORKSHOP_APPROVALS[session_id] = {
        "response_id": response_id,
        "calls": calls,
    }
    return workshop_memory_approval_prompt(calls)
