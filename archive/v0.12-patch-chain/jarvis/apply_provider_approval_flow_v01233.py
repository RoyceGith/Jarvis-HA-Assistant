import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.33 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.33 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    approval_start = backend.find("def mcp_approval_requests(")
    approval_end = backend.find("\n\ndef _tool_progress_phases(", approval_start)
    if approval_start < 0 or approval_end < 0:
        raise RuntimeError("ZBRANO v0.12.33 patch could not locate MCP approval helpers")

    approval_helpers = r'''def mcp_approval_requests(response: dict[str, Any]) -> list[dict[str, Any]]:
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
        plugin = plugin_registry().get(plugin_id)
        if isinstance(plugin, dict):
            name = " ".join(str(plugin.get("name") or "").split())
            if name:
                return name[:80]
    fallback = server_label.removeprefix("plugin_").replace("_", " ").strip()
    return fallback.title()[:80] if fallback else "Plugin"


def mcp_approval_summary(request: dict[str, Any]) -> str:
    import re

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
'''
    backend = backend[:approval_start] + approval_helpers + backend[approval_end:]

    backend = replace_once(
        backend,
        '''        label = str(item.get("name") or "Plugin action")[:120]
        server_label = str(item.get("server_label") or "")''',
        '''        label = mcp_approval_summary(item)
        server_label = str(item.get("server_label") or "")''',
        "provider-aware approval activity",
    )

    branch_start = backend.find("    if pending_approval and approval_decision is not None:")
    continuation_marker = "        continued_response: dict[str, Any] | None = None"
    branch_continuation = backend.find(continuation_marker, branch_start)
    if branch_start < 0 or branch_continuation < 0:
        raise RuntimeError("ZBRANO v0.12.33 patch could not locate approval continuation branch")
    branch_prefix = backend[branch_start:branch_continuation]
    pop_marker = "        PENDING_MCP_APPROVALS.pop(session_id, None)\n"
    if branch_prefix.count(pop_marker) != 1:
        raise RuntimeError("ZBRANO v0.12.33 patch could not locate pending approval removal")
    replacement_prefix = '''    if pending_approval and approval_decision is not None:
        PENDING_MCP_APPROVALS.pop(session_id, None)
        requests = pending_approval["requests"]
        approval_provider = mcp_approval_provider(requests[0]) if requests else "Plugin"
        if approval_decision is False:
            yield stream_event("status", message=f"{approval_provider} action cancelled.")
            for request in requests[:5]:
                yield stream_event(
                    "activity",
                    id=str(request.get("id") or "cancelled-plugin-action"),
                    label=mcp_approval_summary(request),
                    state="cancelled",
                    provider="plugin",
                    plugin_id=mcp_approval_plugin_id(request),
                )
            yield stream_event("delta", text=f"{approval_provider} action cancelled. No action was performed.")
            yield stream_event("done", tool_calls=[])
            return
        yield stream_event("status", message=f"Executing approved {approval_provider} action…")
'''
    backend = backend[:branch_start] + replacement_prefix + backend[branch_continuation:]

    frontend = replace_once(
        frontend,
        '''    .tool-activity[data-state="failed"] .tool-activity-dot { background: #d35d62; }''',
        '''    .tool-activity[data-state="failed"] .tool-activity-dot { background: #d35d62; }
    .tool-activity[data-state="cancelled"] .tool-activity-dot { background: var(--text-muted); }''',
        "cancelled activity state",
    )

    backend = backend.replace('version="0.12.32"', 'version="0.12.33"')
    backend = backend.replace('"version": "0.12.32"', '"version": "0.12.33"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.32"', '"X-ZBRANO-Frontend-Version": "0.12.33"')
    frontend = frontend.replace("HUD 0.12.32", "HUD 0.12.33")

    require(backend, "def mcp_approval_provider", "provider-aware approvals")
    require(backend, "def mcp_approval_summary", "redacted approval summaries")
    require(backend, "No action was performed.", "terminal cancellation response")
    require(backend, 'state="cancelled"', "cancelled activity event")
    require(frontend, 'data-state="cancelled"', "cancelled activity styling")
    require(backend, 'version="0.12.33"', "backend version")
    require(frontend, "HUD 0.12.33", "HUD version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
