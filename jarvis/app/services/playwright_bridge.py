from __future__ import annotations

import asyncio
import contextlib
import os
from pathlib import Path
import re
import time
from typing import Any
from urllib.parse import urlsplit

import httpx


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
PLAYWRIGHT_MCP_LOG = Path("/tmp/zbrano-playwright-mcp.log")
PLAYWRIGHT_CHROMIUM_CANDIDATES = (
    Path("/usr/bin/chromium-browser"),
    Path("/usr/bin/chromium"),
)

developer_mode_enabled = None
mcp_response_json = None
RUNTIME_VERSION = ""


def configure_playwright_bridge(
    *, developer_mode_enabled_fn, mcp_response_json_fn, runtime_version: str,
) -> None:
    global developer_mode_enabled, mcp_response_json, RUNTIME_VERSION
    developer_mode_enabled = developer_mode_enabled_fn
    mcp_response_json = mcp_response_json_fn
    RUNTIME_VERSION = runtime_version


def _playwright_local_url(raw_path: str) -> str:
    """Resolve only ZBRANO-local paths; Playwright is not an arbitrary browser proxy."""
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


def playwright_redact_evidence(value: str, *, limit: int) -> str:
    compact = " ".join(value.split())
    compact = re.sub(r"(?i)\bBearer\s+\S+", "Bearer [redacted]", compact)
    compact = re.sub(
        r"(?i)\b(authorization|api[_-]?key|token|secret|cookie)\s*[:=]\s*\S+",
        r"\1=[redacted]",
        compact,
    )
    return compact[:limit]


def playwright_chromium_executable() -> str:
    return next(
        (str(path) for path in PLAYWRIGHT_CHROMIUM_CANDIDATES if path.is_file()),
        "not found",
    )


def playwright_process_available() -> bool:
    proc = Path("/proc")
    if not proc.is_dir():
        return False
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", errors="replace"
            )
        except (OSError, PermissionError):
            continue
        if "playwright-mcp" in command and "8931" in command:
            return True
    return False


def playwright_startup_log_tail(*, max_bytes: int = 4096, max_lines: int = 12) -> str:
    try:
        with PLAYWRIGHT_MCP_LOG.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - max_bytes))
            data = handle.read(max_bytes)
    except OSError:
        return "unavailable"
    lines = data.decode("utf-8", errors="replace").splitlines()[-max_lines:]
    evidence = " | ".join(line.strip() for line in lines if line.strip())
    return playwright_redact_evidence(evidence, limit=240) or "empty"


def playwright_preflight_summary(*, include_log: bool = False) -> str:
    summary = (
        f"chromium={playwright_chromium_executable()}; "
        f"process={'available' if playwright_process_available() else 'not detected'}"
    )
    if include_log:
        summary += f"; startup log tail={playwright_startup_log_tail()}"
    return summary


def playwright_http_error(operation: str, response: httpx.Response) -> RuntimeError:
    response_detail = playwright_redact_evidence(response.text, limit=160) or "empty response"
    return RuntimeError(
        f"Playwright MCP {operation} returned HTTP {response.status_code}; "
        f"response={response_detail}; {playwright_preflight_summary(include_log=True)}"
    )


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
        raise playwright_http_error(method, response)
    payload = mcp_response_json(response)
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
                    "clientInfo": {"name": "ZBRANO Developer Mode", "version": RUNTIME_VERSION},
                },
            },
        )
        if response.is_redirect:
            raise RuntimeError("Local Playwright MCP initialize redirect is not allowed")
        if response.is_error:
            raise playwright_http_error("initialize", response)
        payload = mcp_response_json(response)
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
            raise playwright_http_error("initialized notification", initialized)
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
    """Collect browser-only evidence with a 30-second end-to-end deadline."""
    if not developer_mode_enabled():
        raise RuntimeError("Developer Mode must be enabled before Playwright inspection")
    url = _playwright_local_url(path)
    inspection_url = f"{url}?zbrano_inspection=1"
    normalized_surface = str(surface or "chat").strip().lower()
    if normalized_surface not in PLAYWRIGHT_SURFACE_SELECTORS:
        raise ValueError("Unknown ZBRANO surface requested for Playwright inspection")
    bounded_wait_ms = max(0, min(int(wait_ms), 5000))
    step = {"name": "session initialization"}

    async def collect() -> dict[str, Any]:
        async with _playwright_session() as (client, headers):
            step["name"] = "tool inventory"
            inventory = await _playwright_rpc(client, headers, 2, "tools/list")
            names = {
                str(tool.get("name") or "")
                for tool in inventory.get("tools") or []
                if isinstance(tool, dict)
            }
            missing = sorted(PLAYWRIGHT_REQUIRED_TOOLS - names)
            if missing:
                raise RuntimeError(f"Playwright MCP is missing required tools: {', '.join(missing)}")
            step["name"] = "browser navigation"
            navigation = await _playwright_rpc(
                client,
                headers,
                3,
                "tools/call",
                {"name": "browser_navigate", "arguments": {"url": inspection_url}},
            )
            _playwright_text(navigation, 1000)
            selector = PLAYWRIGHT_SURFACE_SELECTORS[normalized_surface]
            if selector:
                step["name"] = f"{normalized_surface} tab navigation"
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
                step["name"] = "post-navigation wait"
                await asyncio.sleep(bounded_wait_ms / 1000)
            step["name"] = "accessibility snapshot"
            snapshot = await _playwright_rpc(
                client, headers, 5, "tools/call", {"name": "browser_snapshot", "arguments": {}}
            )
            step["name"] = "console error collection"
            console = await _playwright_rpc(
                client,
                headers,
                6,
                "tools/call",
                {"name": "browser_console_messages", "arguments": {"level": "error"}},
            )
            step["name"] = "network request collection"
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

    try:
        return await asyncio.wait_for(collect(), timeout=30.0)
    except (asyncio.TimeoutError, httpx.TimeoutException) as exc:
        raise RuntimeError(
            f"Playwright inspection timed out during {step['name']}; "
            f"{playwright_preflight_summary(include_log=True)}"
        ) from exc


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
        "icon_url": "plugin-icons/playwright.svg",
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
