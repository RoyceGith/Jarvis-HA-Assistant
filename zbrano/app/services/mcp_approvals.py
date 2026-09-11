from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any


PENDING_MCP_APPROVALS: dict[str, dict[str, Any]] = {}
_plugin_registry: Callable[[], dict[str, Any]] = lambda: {}


def configure_mcp_approvals(*, plugin_registry_fn: Callable[[], dict[str, Any]]) -> None:
    global _plugin_registry
    _plugin_registry = plugin_registry_fn


def mcp_approval_requests(response: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item for item in response.get("output", [])
        if item.get("type") == "mcp_approval_request"
    ]


def mcp_approval_decision(message: str) -> bool | None:
    normalized = " ".join(message.strip().lower().split())
    if normalized in {"approve", "approved", "confirm", "yes", "yes approve", "proceed", "go ahead"}:
        return True
    if normalized in {"cancel", "deny", "denied", "no", "reject", "do not", "don't"}:
        return False
    return None


def mcp_approval_plugin_id(request: dict[str, Any]) -> str:
    server_label = str(request.get("server_label") or "")
    return server_label.removeprefix("plugin_") if server_label.startswith("plugin_") else ""


def mcp_approval_provider(request: dict[str, Any]) -> str:
    server_label = str(request.get("server_label") or "").strip()
    plugin_id = mcp_approval_plugin_id(request)
    if plugin_id:
        plugin = _plugin_registry().get(plugin_id)
        if isinstance(plugin, dict):
            name = " ".join(str(plugin.get("name") or "").split())
            if name:
                return name[:80]
    fallback = server_label.removeprefix("plugin_").replace("_", " ").strip()
    return fallback.title()[:80] if fallback else "Plugin"


def mcp_approval_summary(request: dict[str, Any]) -> str:
    provider = mcp_approval_provider(request)
    name = " ".join(str(request.get("name") or "plugin action").replace("_", " ").split())[:100]
    arguments = request.get("arguments")
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
        except (TypeError, ValueError):
            parsed = {}
    else:
        parsed = arguments if isinstance(arguments, dict) else {}
    method = str(parsed.get("method") or "").upper()
    path = str(parsed.get("path") or "")
    code = str(parsed.get("code") or "")
    if code:
        method_match = re.search(r"\bmethod\s*:\s*[\"']([A-Za-z]+)[\"']", code)
        path_match = re.search(r"\bpath\s*:\s*[\"']([^\"']+)[\"']", code)
        method = method or (method_match.group(1).upper() if method_match else "")
        path = path or (path_match.group(1) if path_match else "")
    operation = " ".join(part for part in (method, path) if part)
    return f"{provider} · {operation or name}"[:180]


def mcp_approval_prompt(requests: list[dict[str, Any]]) -> str:
    providers = []
    for request in requests:
        provider = mcp_approval_provider(request)
        if provider not in providers:
            providers.append(provider)
    subject = providers[0] if len(providers) == 1 else "Installed plugins"
    lines = [f"{subject} requests approval for an action its tools can use to change data:"]
    for request in requests[:5]:
        lines.append(f"- **{mcp_approval_summary(request)}**")
    if len(requests) > 5:
        lines.append(f"- …and {len(requests) - 5} more approval request(s)")
    lines.append("No action has run. Reply **approve** to continue or **cancel** to deny it.")
    return "\n".join(lines)
