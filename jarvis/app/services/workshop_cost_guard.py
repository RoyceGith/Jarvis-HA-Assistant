from __future__ import annotations

import hashlib
import json
from typing import Any


MAX_MODEL_RESPONSES = 6
MAX_TOOL_CALLS = 8
MAX_CALLS_PER_RESPONSE = 3
MAX_SINGLE_TOOL_OUTPUT_CHARS = 32_000
MAX_TOTAL_TOOL_OUTPUT_CHARS = 64_000
MAX_INPUT_TOKENS = 80_000
MAX_CACHE_WRITE_TOKENS = 40_000
MAX_OUTPUT_TOKENS_TOTAL = 16_000
RESPONSE_MAX_OUTPUT_TOKENS = 8_192

WORKSHOP_CORE_TOOL_NAMES = {
    "list_projects",
    "get_project_context",
    "get_latest_handoff",
    "get_open_decisions",
    "get_profile_summary",
}

_LAST_STATUS: dict[str, Any] = {
    "state": "idle",
    "limits": {
        "model_responses": MAX_MODEL_RESPONSES,
        "tool_calls": MAX_TOOL_CALLS,
        "calls_per_response": MAX_CALLS_PER_RESPONSE,
        "single_tool_output_chars": MAX_SINGLE_TOOL_OUTPUT_CHARS,
        "total_tool_output_chars": MAX_TOTAL_TOOL_OUTPUT_CHARS,
        "input_tokens": MAX_INPUT_TOKENS,
        "cache_write_tokens": MAX_CACHE_WRITE_TOKENS,
    },
}


def is_workshop_memory_intent(message: str) -> bool:
    normalized = " ".join(str(message or "").casefold().split())
    explicit = (
        "workshop memory",
        "workshop note",
        "project note",
        "project memory",
        "obsidian",
        "latest handoff",
        "open decision",
        "project requirements",
        "project progress",
        "release and change log",
    )
    return any(term in normalized for term in explicit)


def has_workshop_tool_calls(
    calls: list[dict[str, Any]],
    permission_fn: Any,
    ignored_names: set[str] | None = None,
) -> bool:
    ignored_names = ignored_names or set()
    return any(
        name not in ignored_names
        and (
            name in WORKSHOP_CORE_TOOL_NAMES
            or permission_fn(name) in {"read_only", "write"}
        )
        for call in calls
        for name in [str(call.get("name") or "")]
    )


def workshop_tools(
    static_tools: list[dict[str, Any]],
    dynamic_tools: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose only Workshop Memory schemas for a Workshop Memory request."""
    selected = [
        tool for tool in static_tools
        if str(tool.get("name") or "") in WORKSHOP_CORE_TOOL_NAMES
    ]
    seen = {str(tool.get("name") or "") for tool in selected}
    for tool in dynamic_tools:
        name = str(tool.get("name") or "")
        if name and name not in seen:
            selected.append(tool)
            seen.add(name)
    return selected


def new_workshop_budget(request_message: str = "") -> dict[str, Any]:
    budget = {
        "request_message": str(request_message or "")[:4_000],
        "model_responses": 0,
        "tool_calls": 0,
        "tool_output_chars": 0,
        "input_tokens": 0,
        "cached_tokens": 0,
        "cache_write_tokens": 0,
        "output_tokens": 0,
        "seen_calls": [],
        "state": "active",
        "stop_reason": "",
    }
    _publish(budget)
    return budget


def workshop_response_controls(active: bool) -> dict[str, Any]:
    if not active:
        return {}
    return {
        "parallel_tool_calls": False,
        "max_output_tokens": RESPONSE_MAX_OUTPUT_TOKENS,
    }


def record_workshop_response_usage(
    budget: dict[str, Any] | None,
    response: dict[str, Any] | None,
) -> str | None:
    if budget is None or response is None:
        return None
    usage = response.get("usage") or {}
    details = usage.get("input_tokens_details") or {}
    budget["model_responses"] = int(budget.get("model_responses") or 0) + 1
    budget["input_tokens"] = int(budget.get("input_tokens") or 0) + int(usage.get("input_tokens") or 0)
    budget["cached_tokens"] = int(budget.get("cached_tokens") or 0) + int(details.get("cached_tokens") or 0)
    budget["cache_write_tokens"] = int(budget.get("cache_write_tokens") or 0) + int(details.get("cache_write_tokens") or 0)
    budget["output_tokens"] = int(budget.get("output_tokens") or 0) + int(usage.get("output_tokens") or 0)
    reason = _limit_reason(budget)
    if reason:
        stop_workshop_budget(budget, reason)
    else:
        _publish(budget)
    return reason


def reserve_workshop_call(
    budget: dict[str, Any] | None,
    call: dict[str, Any],
    index_in_response: int,
) -> str | None:
    if budget is None:
        return None
    if str(budget.get("state") or "") == "stopped":
        return str(budget.get("stop_reason") or "the cost-safety budget was reached")
    if index_in_response >= MAX_CALLS_PER_RESPONSE:
        reason = "the model requested too many tools in one response"
        stop_workshop_budget(budget, reason)
        return reason
    if int(budget.get("tool_calls") or 0) >= MAX_TOOL_CALLS:
        reason = "the per-task tool-call limit was reached"
        stop_workshop_budget(budget, reason)
        return reason
    fingerprint_source = json.dumps(
        {
            "name": str(call.get("name") or ""),
            "arguments": str(call.get("arguments") or "{}"),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()
    seen = list(budget.get("seen_calls") or [])
    if fingerprint in seen:
        return "an exact duplicate tool call was suppressed"
    seen.append(fingerprint)
    budget["seen_calls"] = seen[-MAX_TOOL_CALLS:]
    budget["tool_calls"] = int(budget.get("tool_calls") or 0) + 1
    _publish(budget)
    return None


def reject_oversized_workshop_batch(
    budget: dict[str, Any] | None,
    calls: list[dict[str, Any]],
) -> str | None:
    """Reject an oversized response before any write in that response executes."""
    if budget is None:
        return None
    if len(calls) > MAX_CALLS_PER_RESPONSE:
        reason = "the model requested too many tools in one response"
    elif int(budget.get("tool_calls") or 0) + len(calls) > MAX_TOOL_CALLS:
        reason = "the per-task tool-call limit was reached"
    else:
        return None
    stop_workshop_budget(budget, reason)
    return reason


def note_workshop_write_completed(budget: dict[str, Any] | None) -> None:
    """Allow a post-write read-back even if the same note was read before writing."""
    if budget is None:
        return
    budget["seen_calls"] = []
    _publish(budget)


def bound_workshop_result(
    budget: dict[str, Any] | None,
    result: dict[str, Any],
    *,
    permission: str | None,
) -> dict[str, Any]:
    if budget is None:
        return result
    candidate = _compact_write_result(result) if permission == "write" else result
    rendered = json.dumps(candidate, ensure_ascii=False)
    if len(rendered) > MAX_SINGLE_TOOL_OUTPUT_CHARS:
        return {
            "error": (
                f"Workshop Memory returned {len(rendered)} characters, above the "
                f"{MAX_SINGLE_TOOL_OUTPUT_CHARS}-character safety limit. Narrow the request "
                "to one note or a smaller section; the oversized result was not sent to the model."
            )
        }
    projected = int(budget.get("tool_output_chars") or 0) + len(rendered)
    if projected > MAX_TOTAL_TOOL_OUTPUT_CHARS:
        reason = "the cumulative tool-output limit was reached"
        stop_workshop_budget(budget, reason)
        return {"error": workshop_budget_stop_reply(reason)}
    budget["tool_output_chars"] = projected
    _publish(budget)
    return candidate


def stop_workshop_budget(budget: dict[str, Any], reason: str) -> None:
    budget["state"] = "stopped"
    budget["stop_reason"] = reason
    _publish(budget)


def workshop_budget_stop_reply(reason: str) -> str:
    return (
        "Workshop Memory stopped because its cost-safety budget was reached: "
        f"{reason}. No further tools were run. Narrow the request to one note or "
        "one specific change, then start a new task."
    )


def workshop_cost_guard_status() -> dict[str, Any]:
    return json.loads(json.dumps(_LAST_STATUS))


def workshop_budget_reason(budget: dict[str, Any] | None) -> str:
    if not isinstance(budget, dict) or str(budget.get("state") or "") != "stopped":
        return ""
    return str(budget.get("stop_reason") or "the cost-safety budget was reached")


def _limit_reason(budget: dict[str, Any]) -> str | None:
    if int(budget.get("model_responses") or 0) >= MAX_MODEL_RESPONSES:
        return "the model-response limit was reached"
    if int(budget.get("input_tokens") or 0) >= MAX_INPUT_TOKENS:
        return "the cumulative input-token limit was reached"
    if int(budget.get("cache_write_tokens") or 0) >= MAX_CACHE_WRITE_TOKENS:
        return "the cache-write token limit was reached"
    if int(budget.get("output_tokens") or 0) >= MAX_OUTPUT_TOKENS_TOTAL:
        return "the cumulative output-token limit was reached"
    return None


def _compact_write_result(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return "<nested result omitted>"
    if isinstance(value, str):
        if len(value) <= 1_000:
            return value
        return f"<written content omitted: {len(value)} characters>"
    if isinstance(value, list):
        return [_compact_write_result(item, depth + 1) for item in value[:20]]
    if isinstance(value, dict):
        return {
            str(key): _compact_write_result(item, depth + 1)
            for key, item in list(value.items())[:30]
        }
    return value


def _publish(budget: dict[str, Any]) -> None:
    global _LAST_STATUS
    _LAST_STATUS = {
        "state": str(budget.get("state") or "active"),
        "model_responses": int(budget.get("model_responses") or 0),
        "tool_calls": int(budget.get("tool_calls") or 0),
        "tool_output_chars": int(budget.get("tool_output_chars") or 0),
        "input_tokens": int(budget.get("input_tokens") or 0),
        "cached_tokens": int(budget.get("cached_tokens") or 0),
        "cache_write_tokens": int(budget.get("cache_write_tokens") or 0),
        "output_tokens": int(budget.get("output_tokens") or 0),
        "stop_reason": str(budget.get("stop_reason") or ""),
        "limits": {
            "model_responses": MAX_MODEL_RESPONSES,
            "tool_calls": MAX_TOOL_CALLS,
            "calls_per_response": MAX_CALLS_PER_RESPONSE,
            "single_tool_output_chars": MAX_SINGLE_TOOL_OUTPUT_CHARS,
            "total_tool_output_chars": MAX_TOTAL_TOOL_OUTPUT_CHARS,
            "input_tokens": MAX_INPUT_TOKENS,
            "cache_write_tokens": MAX_CACHE_WRITE_TOKENS,
        },
    }
