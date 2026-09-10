from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any


PENDING_WORKSHOP_APPROVALS: dict[str, dict[str, Any]] = {}
PENDING_MEMORY_ORGANIZATION: dict[str, dict[str, Any]] = {}
WORKSHOP_TASK_APPROVAL_GRANTS: dict[str, float] = {}
WORKSHOP_TASK_APPROVAL_SECONDS = 15 * 60
DIRECT_MEMORY_SAVE_TOOLS = {"save_to_memory_database", "remember_automatically"}
LARGE_MEMORY_PHASE_BYTES = 40_000

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


def is_explicit_memory_save_request(message: str) -> bool:
    """Treat the user's save instruction as consent for that exact memory save."""
    normalized = " ".join(str(message or "").casefold().split())
    direct_phrases = (
        "remember this", "remember that", "remember the following",
        "save this to memory", "save that to memory", "save on memory",
        "store this in memory", "keep this in memory", "add this to memory",
        "memorizza", "salva in memoria", "ricorda questo", "ricorda che",
        "sauvegarde en mémoire", "enregistre en mémoire", "mémorise", "retiens ceci",
        "αποθήκευσε στη μνήμη", "αποθηκευσε στη μνημη", "θυμήσου αυτό",
        "θυμησου αυτο", "κράτησε στη μνήμη", "κρατησε στη μνημη",
    )
    if any(phrase in normalized for phrase in direct_phrases):
        return True
    destinations = (
        "memory database", "knowledge memory", "workshop memory",
        "database di memoria", "archivio memoria", "base de mémoire",
        "base mémoire", "βάση μνήμης", "βαση μνημης",
    )
    save_verbs = (
        "save", "store", "keep", "add", "put", "write", "remember",
        "salva", "memorizza", "ricorda", "conserva", "aggiungi",
        "sauvegarde", "enregistre", "mémorise", "retiens", "ajoute",
        "αποθήκευσε", "αποθηκευσε", "θυμήσου", "θυμησου", "κράτησε",
        "κρατησε", "πρόσθεσε", "προσθεσε",
    )
    return any(destination in normalized for destination in destinations) and any(
        verb in normalized for verb in save_verbs
    )


def explicit_memory_save_authorized(message: str, calls: list[dict[str, Any]]) -> bool:
    """Authorize only plain Memory Database saves explicitly requested now."""
    writes = workshop_memory_write_calls(calls)
    return bool(writes) and is_explicit_memory_save_request(message) and all(
        str(call.get("name") or "") in DIRECT_MEMORY_SAVE_TOOLS
        for call in writes
    )


def remember_memory_organization_choice(
    session_id: str,
    call: dict[str, Any],
    result: dict[str, Any],
) -> None:
    """Keep only the exact follow-up destinations offered for an unfinished save."""
    if str(call.get("name") or "") not in DIRECT_MEMORY_SAVE_TOOLS:
        return
    try:
        arguments = json.loads(str(call.get("arguments") or "{}"))
    except json.JSONDecodeError:
        return
    choices = {
        (str(choice.get("id") or ""), str(choice.get("destination_note") or ""))
        for choice in result.get("choices") or []
        if isinstance(choice, dict)
    }
    if not choices:
        return
    PENDING_MEMORY_ORGANIZATION[session_id] = {
        "content": str(arguments.get("content") or ""),
        "title": str(arguments.get("title") or ""),
        "preferred_area": str(arguments.get("preferred_area") or "auto"),
        "choices": choices,
        "expires_at": time.monotonic() + WORKSHOP_TASK_APPROVAL_SECONDS,
    }


def memory_organization_choice_authorized(
    session_id: str,
    calls: list[dict[str, Any]],
) -> bool:
    pending = PENDING_MEMORY_ORGANIZATION.get(session_id)
    if not pending:
        return False
    if float(pending.get("expires_at") or 0) <= time.monotonic():
        PENDING_MEMORY_ORGANIZATION.pop(session_id, None)
        return False
    writes = workshop_memory_write_calls(calls)
    if len(writes) != 1 or str(writes[0].get("name") or "") not in DIRECT_MEMORY_SAVE_TOOLS:
        return False
    try:
        arguments = json.loads(str(writes[0].get("arguments") or "{}"))
    except json.JSONDecodeError:
        return False
    return (
        str(arguments.get("content") or "") == pending["content"]
        and str(arguments.get("title") or "") == pending["title"]
        and str(arguments.get("preferred_area") or "auto") == pending["preferred_area"]
        and (
            str(arguments.get("organization") or ""),
            str(arguments.get("destination_note") or ""),
        ) in pending["choices"]
    )


def clear_memory_organization_choice(session_id: str) -> None:
    PENDING_MEMORY_ORGANIZATION.pop(session_id, None)


def memory_save_phase_notice(calls: list[dict[str, Any]]) -> str:
    """Describe genuinely large explicit saves before their first write starts."""
    phases = 0
    total_bytes = 0
    for call in calls:
        if str(call.get("name") or "") not in DIRECT_MEMORY_SAVE_TOOLS:
            continue
        try:
            arguments = json.loads(str(call.get("arguments") or "{}"))
        except json.JSONDecodeError:
            arguments = {}
        content_bytes = len(str(arguments.get("content") or "").encode("utf-8"))
        total_bytes += content_bytes
        phases += 1
    if phases <= 1 or total_bytes <= LARGE_MEMORY_PHASE_BYTES:
        return ""
    return (
        f"This is a large Memory Database save. I will handle it in {phases} "
        f"bounded phase{'s' if phases != 1 else ''} and complete them without asking "
        "for approval again."
    )


def workshop_tool_display_name(name: str) -> str:
    return {
        "save_to_memory_database": "Save to Memory Database",
        "remember_automatically": "Save to Memory Database",
    }.get(name, name.replace("_", " ").strip().title() or "Memory Database change")


def workshop_memory_approval_prompt(calls: list[dict[str, Any]]) -> str:
    writes = workshop_memory_write_calls(calls)
    gmail_writes = _gmail_write_calls(calls)
    lines = [
        "Gmail Direct is requesting permission to create an unsent draft:"
        if gmail_writes else
        "Knowledge Memory is requesting permission to change permanent project data:"
    ]
    for call in writes[:5]:
        name = workshop_tool_display_name(str(call.get("name") or ""))
        arguments = summarize_workshop_memory_arguments(call.get("arguments") or "{}")
        lines.append(f"- **{name}** with `{arguments}`")
    if len(writes) > 5:
        lines.append(f"- …and {len(writes) - 5} more change(s)")
    lines.append(
        "The message will remain a draft and will not be sent. Reply **approve** to create it or **cancel** to deny."
        if gmail_writes else
        "Reply **approve** for this write, **approve task** to allow Knowledge Memory writes in this chat for 15 minutes, or **cancel** to deny."
    )
    return "\n".join(lines)


def store_workshop_memory_approval(
    session_id: str,
    response_id: str,
    calls: list[dict[str, Any]],
    *,
    request_message: str = "",
    cost_budget: dict[str, Any] | None = None,
) -> str:
    PENDING_WORKSHOP_APPROVALS[session_id] = {
        "response_id": response_id,
        "calls": calls,
        "request_message": request_message,
        "cost_budget": cost_budget,
    }
    return workshop_memory_approval_prompt(calls)
