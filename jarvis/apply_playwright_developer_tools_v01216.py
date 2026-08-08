from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.16 patch missing: {label}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    require(text, old, label)
    return text.replace(old, new, 1)


PLAYWRIGHT_BACKEND = r'''
PLAYWRIGHT_MCP_URL = os.getenv("PLAYWRIGHT_MCP_URL", "http://127.0.0.1:8931/mcp")
PLAYWRIGHT_LOCAL_ORIGIN = "http://127.0.0.1:8099"
PLAYWRIGHT_REQUIRED_TOOLS = {
    "browser_navigate",
    "browser_click",
    "browser_snapshot",
    "browser_console_messages",
    "browser_network_requests",
}
PLAYWRIGHT_OUTPUT_LIMITS = {
    "snapshot": 24000,
    "console": 6000,
    "network": 8000,
}
PLAYWRIGHT_SURFACE_SELECTORS = {
    "chat": None,
    "shared_files": "#shared-files-tab",
    "plugins": "#plugins-tab",
    "automations": "#automations-tab",
    "entities": "#entities-tab",
    "settings": "#settings-tab",
    "developer": "#developer-tab",
}


def _playwright_local_url(raw_path: str) -> str:
    """Resolve only ZBRANO-local paths; Playwright is not an arbitrary browser proxy."""
    from urllib.parse import urlsplit

    path = str(raw_path or "/").strip()
    parsed = urlsplit(path)
    segments = [segment for segment in parsed.path.split("/") if segment]
    if (
        not path.startswith("/")
        or parsed.scheme
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or ".." in segments
        or "\\" in path
    ):
        raise ValueError("Playwright can inspect only a query-free path on ZBRANO's local UI")
    return f"{PLAYWRIGHT_LOCAL_ORIGIN}{parsed.path or '/'}"


async def _playwright_rpc(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    request_id: int,
    method: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = await client.post(
        PLAYWRIGHT_MCP_URL,
        headers=headers,
        json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}},
    )
    if response.is_redirect:
        raise RuntimeError("Local Playwright MCP redirects are not allowed")
    if response.is_error:
        raise RuntimeError(f"Playwright MCP {method} returned HTTP {response.status_code}")
    payload = _mcp_response_json(response)
    if not isinstance(payload, dict):
        raise RuntimeError(f"Playwright MCP {method} returned invalid JSON")
    if payload.get("error"):
        error = payload["error"]
        message = error.get("message") if isinstance(error, dict) else str(error)
        raise RuntimeError(f"Playwright MCP {method} failed: {message}")
    result = payload.get("result")
    return result if isinstance(result, dict) else {}


@contextlib.asynccontextmanager
async def _playwright_session():
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    timeout = httpx.Timeout(30.0, connect=3.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        response = await client.post(
            PLAYWRIGHT_MCP_URL,
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "ZBRANO Developer Mode", "version": "0.12.16"},
                },
            },
        )
        if response.is_redirect or response.is_error:
            raise RuntimeError(f"Playwright MCP initialize returned HTTP {response.status_code}")
        payload = _mcp_response_json(response)
        if not isinstance(payload, dict) or payload.get("error"):
            raise RuntimeError("Playwright MCP initialization failed")
        session_id = response.headers.get("mcp-session-id")
        if session_id:
            headers["mcp-session-id"] = session_id
        initialized = await client.post(
            PLAYWRIGHT_MCP_URL,
            headers=headers,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
        if initialized.is_error:
            raise RuntimeError(f"Playwright MCP initialized notification returned HTTP {initialized.status_code}")
        try:
            yield client, headers
        finally:
            if session_id:
                with contextlib.suppress(httpx.HTTPError):
                    await client.delete(PLAYWRIGHT_MCP_URL, headers=headers)


def _playwright_text(result: dict[str, Any], limit: int) -> str:
    content = result.get("content") or []
    text_parts = [
        str(item.get("text") or "")
        for item in content
        if isinstance(item, dict) and item.get("type") == "text"
    ]
    text = "\n".join(part for part in text_parts if part)
    if result.get("isError"):
        raise RuntimeError(text[:1000] or "Playwright MCP tool returned an error")
    return text[:limit]


async def playwright_mcp_inventory() -> set[str]:
    async with _playwright_session() as (client, headers):
        result = await _playwright_rpc(client, headers, 2, "tools/list")
    return {
        str(tool.get("name") or "")
        for tool in result.get("tools") or []
        if isinstance(tool, dict) and tool.get("name")
    }


async def inspect_zbrano_ui_with_playwright(
    path: str = "/",
    surface: str = "chat",
    wait_ms: int = 750,
) -> dict[str, Any]:
    """Collect bounded browser evidence, with interaction limited to known navigation tabs."""
    if not developer_mode_enabled():
        raise RuntimeError("Developer Mode must be enabled before Playwright inspection")
    url = _playwright_local_url(path)
    normalized_surface = str(surface or "chat").strip().lower()
    if normalized_surface not in PLAYWRIGHT_SURFACE_SELECTORS:
        raise ValueError("Unknown ZBRANO surface requested for Playwright inspection")
    bounded_wait_ms = max(0, min(int(wait_ms), 5000))
    async with _playwright_session() as (client, headers):
        inventory = await _playwright_rpc(client, headers, 2, "tools/list")
        names = {
            str(tool.get("name") or "")
            for tool in inventory.get("tools") or []
            if isinstance(tool, dict)
        }
        missing = sorted(PLAYWRIGHT_REQUIRED_TOOLS - names)
        if missing:
            raise RuntimeError(f"Playwright MCP is missing required tools: {', '.join(missing)}")
        navigation = await _playwright_rpc(
            client,
            headers,
            3,
            "tools/call",
            {"name": "browser_navigate", "arguments": {"url": url}},
        )
        _playwright_text(navigation, 1000)
        selector = PLAYWRIGHT_SURFACE_SELECTORS[normalized_surface]
        if selector:
            tab_result = await _playwright_rpc(
                client,
                headers,
                4,
                "tools/call",
                {
                    "name": "browser_click",
                    "arguments": {
                        "target": selector,
                        "element": f"ZBRANO {normalized_surface.replace('_', ' ')} navigation tab",
                    },
                },
            )
            _playwright_text(tab_result, 1000)
        if bounded_wait_ms:
            await asyncio.sleep(bounded_wait_ms / 1000)
        snapshot = await _playwright_rpc(
            client, headers, 5, "tools/call", {"name": "browser_snapshot", "arguments": {}}
        )
        console = await _playwright_rpc(
            client,
            headers,
            6,
            "tools/call",
            {"name": "browser_console_messages", "arguments": {"level": "error"}},
        )
        network = await _playwright_rpc(
            client,
            headers,
            7,
            "tools/call",
            {"name": "browser_network_requests", "arguments": {"static": False}},
        )
    return {
        "success": True,
        "scope": "zbrano_local_ui",
        "url": url,
        "surface": normalized_surface,
        "wait_ms": bounded_wait_ms,
        "snapshot": _playwright_text(snapshot, PLAYWRIGHT_OUTPUT_LIMITS["snapshot"]),
        "console_errors": _playwright_text(console, PLAYWRIGHT_OUTPUT_LIMITS["console"]),
        "network_requests": _playwright_text(network, PLAYWRIGHT_OUTPUT_LIMITS["network"]),
        "interaction_scope": "navigation_tab_only" if selector else "navigation_only",
    }


async def playwright_builtin_plugin() -> dict[str, Any]:
    try:
        names = await asyncio.wait_for(playwright_mcp_inventory(), timeout=3.0)
        missing = sorted(PLAYWRIGHT_REQUIRED_TOOLS - names)
        healthy = not missing
        last_error = None if healthy else f"Missing required tools: {', '.join(missing)}"
    except Exception as exc:
        healthy = False
        last_error = str(exc)[:500]
    return {
        "id": "builtin-playwright",
        "name": "Playwright MCP",
        "url": "Local browser service · Developer Mode only",
        "icon_url": "https://cdn.simpleicons.org/playwright/2EAD33",
        "builtin": True,
        "enabled": True,
        "healthy": healthy,
        "last_error": last_error,
        "last_checked": time.time(),
        "has_secret": False,
        "auth_mode": "builtin",
        "oauth_connected": False,
        "oauth_provider": "",
        "tools": [{
            "name": "inspect_zbrano_ui_with_playwright",
            "description": "Inspect a ZBRANO UI surface's DOM, console errors, and network requests.",
            "permission": "read_only",
            "enabled": True,
        }],
        "enabled_tool_count": 1,
        "approval_tool_count": 0,
        "available_to_chat": bool(developer_mode_enabled() and healthy),
    }
'''


PLAYWRIGHT_TOOL = r'''    }, {
        "type": "function",
        "name": "inspect_zbrano_ui_with_playwright",
        "description": (
            "Open ZBRANO's own local UI in a headless Chromium browser and return a bounded "
            "accessibility snapshot, console errors, and network requests. It can switch only "
            "among known ZBRANO navigation tabs; it cannot browse external sites or operate feature controls."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "A query-free ZBRANO-local path beginning with /, normally /.",
                },
                "surface": {
                    "type": "string",
                    "enum": ["chat", "shared_files", "plugins", "automations", "entities", "settings", "developer"],
                    "description": "ZBRANO navigation surface to inspect after loading the local UI.",
                },
                "wait_ms": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 5000,
                    "description": "Time to wait after navigation before collecting evidence.",
                },
            },
            "required": ["path", "surface", "wait_ms"],
            "additionalProperties": False,
        },
        "strict": True,
'''


def patch_backend(backend: str) -> str:
    backend = backend.replace('version="0.12.15"', 'version="0.12.16"')
    backend = backend.replace('"version": "0.12.15"', '"version": "0.12.16"')

    execute_marker = "\nasync def execute_tool_calls(\n"
    backend = replace_once(backend, execute_marker, f"\n{PLAYWRIGHT_BACKEND}\n{execute_marker.lstrip()}", "tool executor")

    dispatch_marker = '''                elif name == "investigate_zbrano_feature":
                    result = await investigate_zbrano_feature(
                        arguments["feature"],
                        arguments["symptom"],
                    )'''
    dispatch_replacement = dispatch_marker + '''
                elif name == "inspect_zbrano_ui_with_playwright":
                    result = await inspect_zbrano_ui_with_playwright(
                        arguments["path"],
                        arguments["surface"],
                        arguments["wait_ms"],
                    )'''
    backend = replace_once(backend, dispatch_marker, dispatch_replacement, "Playwright tool dispatch")

    list_marker = '''    return {"plugins": [plugin_public(pid, plugin) for pid, plugin in registry.items()]}'''
    list_replacement = '''    installed = [plugin_public(pid, plugin) for pid, plugin in registry.items()]
    return {"plugins": [await playwright_builtin_plugin(), *installed]}'''
    backend = replace_once(backend, list_marker, list_replacement, "built-in plugin listing")

    instruction_marker = "While Developer Mode is active, Workshop Memory, Home Assistant, and non-GitHub MCP tools are unavailable."
    instruction_replacement = (
        "While Developer Mode is active, Workshop Memory, Home Assistant, and non-GitHub remote MCP tools are unavailable. "
        "The built-in Playwright inspection tool remains available only for read-only evidence from ZBRANO's local UI. "
        "After the single targeted diagnostic, use Playwright when the reported symptom requires browser DOM, console, or network evidence."
    )
    backend = replace_once(backend, instruction_marker, instruction_replacement, "Developer Mode tool policy")

    tool_end_marker = '''        "strict": True,
    }]'''
    tool_end_replacement = '''        "strict": True,
''' + PLAYWRIGHT_TOOL + '''    }]'''
    developer_start = backend.index("def developer_runtime_tools()")
    developer_tail = backend[developer_start:]
    require(developer_tail, tool_end_marker, "developer tool list end")
    developer_tail = developer_tail.replace(tool_end_marker, tool_end_replacement, 1)
    backend = backend[:developer_start] + developer_tail

    github_marker = '''    else:
        add("GitHub MCP readiness", "degraded", "GitHub plugin not installed", "developer", "Install and connect the official GitHub MCP plugin.")

    counts = {'''
    github_replacement = '''    else:
        add("GitHub MCP readiness", "degraded", "GitHub plugin not installed", "developer", "Install and connect the official GitHub MCP plugin.")

    try:
        playwright_tools = await asyncio.wait_for(playwright_mcp_inventory(), timeout=8.0)
        playwright_missing = sorted(PLAYWRIGHT_REQUIRED_TOOLS - playwright_tools)
        add(
            "Playwright MCP readiness",
            "operational" if not playwright_missing else "failed",
            f"{len(playwright_tools)} browser tools discovered" if not playwright_missing else f"missing: {', '.join(playwright_missing)}",
            "developer",
            "Inspect the local Playwright MCP startup log and Chromium installation.",
        )
    except Exception as exc:
        add("Playwright MCP readiness", "failed", str(exc)[:500], "developer", "Inspect the local Playwright MCP startup log and Chromium installation.")

    counts = {'''
    backend = replace_once(backend, github_marker, github_replacement, "Playwright diagnostic")

    targeted_marker = '''        github_tools = developer_mcp_tools()
        add("Developer GitHub tools", "operational" if github_tools else "degraded", f"{len(github_tools)} GitHub MCP server(s) exposed; Workshop Memory tools excluded", "developer")'''
    targeted_replacement = targeted_marker + '''
        try:
            playwright_tools = await asyncio.wait_for(playwright_mcp_inventory(), timeout=5.0)
            playwright_missing = sorted(PLAYWRIGHT_REQUIRED_TOOLS - playwright_tools)
            add(
                "Developer Playwright tools",
                "operational" if not playwright_missing else "failed",
                f"{len(playwright_tools)} local browser tools discovered" if not playwright_missing else f"missing: {', '.join(playwright_missing)}",
                "developer",
            )
        except Exception as exc:
            add("Developer Playwright tools", "failed", str(exc)[:500], "developer")'''
    backend = replace_once(backend, targeted_marker, targeted_replacement, "targeted Playwright diagnostic")
    return backend


def patch_frontend(frontend: str) -> str:
    frontend = frontend.replace("HUD 0.12.15", "HUD 0.12.16")
    checkbox = '${t.permission==="blocked"?"disabled":""}'
    frontend = replace_once(frontend, checkbox, '${p.builtin||t.permission==="blocked"?"disabled":""}', "built-in tool lock")

    oauth = '''      const oauthActions=p.auth_mode==="oauth"
        ?`<button data-a="oauth" data-id="${esc(p.id)}">${p.oauth_connected?"Reauthorize":"Connect"}</button>${p.oauth_connected?`<button data-a="oauth-disconnect" data-id="${esc(p.id)}">Sign out</button>`:""}`
        :"";'''
    actions = oauth + '''
      const pluginActions=p.builtin
        ?'<button type="button" disabled>Built-in · Developer Mode</button>'
        :`${oauthActions}<button data-a="toggle" data-id="${esc(p.id)}">${p.enabled?"Disable":"Enable"}</button><button data-a="refresh" data-id="${esc(p.id)}">Refresh</button><button data-a="remove" data-id="${esc(p.id)}">Remove</button>`;
      const pluginStateSummary=p.builtin
        ?`${p.available_to_chat?"Available in Developer Mode":"Enable Developer Mode to use"} · ${p.healthy?"Healthy":"Unavailable"}`
        :`${p.enabled?"Enabled":"Installed · disabled"} · ${p.available_to_chat?"Available to chat":"Not available to chat"} · ${p.enabled_tool_count||0} tool${(p.enabled_tool_count||0)===1?"":"s"} enabled · ${p.approval_tool_count||0} require approval · ${p.healthy?"Healthy":"Unhealthy"} · token ${p.has_secret?"stored":"not set"}`;'''
    frontend = replace_once(frontend, oauth, actions, "built-in plugin actions")

    row_start = '''<span class="plugin-meta">${p.enabled?"Enabled":"Installed · disabled"} · ${p.available_to_chat?"Available to chat":"Not available to chat"} · ${p.enabled_tool_count||0} tool${(p.enabled_tool_count||0)===1?"":"s"} enabled · ${p.approval_tool_count||0} require approval · ${p.healthy?"Healthy":"Unhealthy"} · token ${p.has_secret?"stored":"not set"}</span></div></div><div class="plugin-actions">${oauthActions}<button data-a="toggle" data-id="${esc(p.id)}">${p.enabled?"Disable":"Enable"}</button><button data-a="refresh" data-id="${esc(p.id)}">Refresh</button><button data-a="remove" data-id="${esc(p.id)}">Remove</button></div>'''
    row_new = '''<span class="plugin-meta">${pluginStateSummary}</span>${p.last_error?`<span class="plugin-meta">${esc(p.last_error)}</span>`:""}</div></div><div class="plugin-actions">${pluginActions}</div>'''
    frontend = replace_once(frontend, row_start, row_new, "built-in plugin card")
    return frontend


def main() -> None:
    backend = patch_backend(MAIN.read_text(encoding="utf-8"))
    frontend = patch_frontend(INDEX.read_text(encoding="utf-8"))
    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


def verify() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")
    for marker in (
        'version="0.12.16"',
        '"version": "0.12.16"',
        "async def inspect_zbrano_ui_with_playwright",
        '"name": "inspect_zbrano_ui_with_playwright"',
        "PLAYWRIGHT_REQUIRED_TOOLS",
        "await playwright_builtin_plugin()",
        "Playwright MCP readiness",
        "Developer Playwright tools",
    ):
        require(backend, marker, marker)
    for marker in ("HUD 0.12.16", "Built-in · Developer Mode", "pluginStateSummary", "p.builtin||"):
        require(frontend, marker, marker)


if __name__ == "__main__":
    main()
    verify()
