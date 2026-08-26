from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any

import httpx

from ..services.mcp_protocol import MCPError, _find_result, _read_mcp_response, decode_workshop_tool_result


WORKSHOP_MEMORY_INTERNAL_URL = ""
WORKSHOP_MEMORY_URL = ""
WORKSHOP_STATIC_TOOL_NAMES: set[str] = set()
GMAIL_DIRECT_TOOL_NAMES: set[str] = set()
GMAIL_DIRECT_WRITE_TOOLS: set[str] = set()


def configure_workshop_memory_domain(
    *, internal_url: str, external_url: str, static_tool_names: set[str],
    direct_tool_names: set[str], direct_write_tools: set[str],
) -> None:
    global WORKSHOP_MEMORY_INTERNAL_URL, WORKSHOP_MEMORY_URL
    global WORKSHOP_STATIC_TOOL_NAMES, GMAIL_DIRECT_TOOL_NAMES, GMAIL_DIRECT_WRITE_TOOLS
    WORKSHOP_MEMORY_INTERNAL_URL = internal_url
    WORKSHOP_MEMORY_URL = external_url
    WORKSHOP_STATIC_TOOL_NAMES = set(static_tool_names)
    GMAIL_DIRECT_TOOL_NAMES = set(direct_tool_names)
    GMAIL_DIRECT_WRITE_TOOLS = set(direct_write_tools)

MCP_HTTP_TIMEOUT = httpx.Timeout(30.0, connect=2.0)

MCP_HTTP_LIMITS = httpx.Limits(
    max_connections=10,
    max_keepalive_connections=5,
    keepalive_expiry=60.0,
)

MCP_CLIENT: httpx.AsyncClient | None = None

MCP_ACTIVE_URL: str | None = None

MCP_LAST_ERROR: str | None = None

MCP_LAST_LATENCY_MS: float | None = None

MCP_LAST_SUCCESS_AT: float | None = None

MCP_ENDPOINT_LATENCY_MS: dict[str, float] = {}

MCP_TOOL_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}

MCP_CACHE_TTLS = {
    "get_profile_summary": 900.0,
    "get_project_context": 300.0,
    "get_latest_handoff": 120.0,
    "get_open_decisions": 120.0,
    "list_projects": 120.0,
}

MCP_LOCK = asyncio.Lock()

def workshop_memory_candidates() -> list[str]:
    candidates: list[str] = []
    for value in (WORKSHOP_MEMORY_INTERNAL_URL, WORKSHOP_MEMORY_URL):
        cleaned = value.strip().rstrip("/")
        if cleaned and cleaned not in candidates:
            candidates.append(cleaned)
    return candidates

def mcp_cache_key(tool_name: str, arguments: dict[str, Any]) -> str:
    return json.dumps(
        {"tool": tool_name, "arguments": arguments},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

def get_cached_mcp_result(
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any] | None:
    ttl = MCP_CACHE_TTLS.get(tool_name)
    if not ttl:
        return None
    entry = MCP_TOOL_CACHE.get(mcp_cache_key(tool_name, arguments))
    if not entry:
        return None
    created_at, result = entry
    if time.monotonic() - created_at > ttl:
        MCP_TOOL_CACHE.pop(mcp_cache_key(tool_name, arguments), None)
        return None
    return result

def set_cached_mcp_result(
    tool_name: str,
    arguments: dict[str, Any],
    result: dict[str, Any],
) -> None:
    if tool_name in MCP_CACHE_TTLS:
        MCP_TOOL_CACHE[mcp_cache_key(tool_name, arguments)] = (
            time.monotonic(),
            result,
        )

async def get_mcp_client() -> httpx.AsyncClient:
    global MCP_CLIENT
    if MCP_CLIENT is None or MCP_CLIENT.is_closed:
        MCP_CLIENT = httpx.AsyncClient(
            timeout=MCP_HTTP_TIMEOUT,
            limits=MCP_HTTP_LIMITS,
            http2=False,
        )
    return MCP_CLIENT

async def close_mcp_client() -> None:
    global MCP_CLIENT
    if MCP_CLIENT is not None and not MCP_CLIENT.is_closed:
        await MCP_CLIENT.aclose()
    MCP_CLIENT = None

async def _mcp_post(
    client: httpx.AsyncClient,
    endpoint_url: str,
    payload: dict[str, Any],
    session_id: str | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    response = await client.post(
        endpoint_url,
        headers=headers,
        json=payload,
    )
    messages = await _read_mcp_response(response)
    returned_session_id = response.headers.get("mcp-session-id") or session_id
    return messages, returned_session_id

async def _call_workshop_memory_endpoint(
    endpoint_url: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    client = await get_mcp_client()

    initialize_id = 1
    initialize_payload = {
        "jsonrpc": "2.0",
        "id": initialize_id,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {
                "name": "zbrano-workshop-assistant",
                "version": "0.7.0",
            },
        },
    }

    init_messages, session_id = await _mcp_post(
        client,
        endpoint_url,
        initialize_payload,
    )
    _find_result(init_messages, initialize_id)

    await _mcp_post(
        client,
        endpoint_url,
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        },
        session_id,
    )

    call_id = 2
    call_messages, _ = await _mcp_post(
        client,
        endpoint_url,
        {
            "jsonrpc": "2.0",
            "id": call_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        },
        session_id,
    )
    result = _find_result(call_messages, call_id)
    return decode_workshop_tool_result(result)

WORKSHOP_DYNAMIC_TOOLS: dict[str, dict[str, Any]] = {}

WORKSHOP_DYNAMIC_TOOLS_REFRESHED_AT = 0.0

WORKSHOP_DYNAMIC_TOOLS_TTL = 60.0

async def _list_workshop_memory_endpoint_tools(endpoint_url: str) -> list[dict[str, Any]]:
    client = await get_mcp_client()
    initialize_id = 1
    init_messages, session_id = await _mcp_post(
        client,
        endpoint_url,
        {
            "jsonrpc": "2.0",
            "id": initialize_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {
                    "name": "zbrano-workshop-assistant",
                    "version": "0.13.46",
                },
            },
        },
    )
    _find_result(init_messages, initialize_id)
    await _mcp_post(
        client,
        endpoint_url,
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        session_id,
    )
    list_id = 2
    list_messages, _ = await _mcp_post(
        client,
        endpoint_url,
        {"jsonrpc": "2.0", "id": list_id, "method": "tools/list", "params": {}},
        session_id,
    )
    tools = _find_result(list_messages, list_id).get("tools") or []
    return [tool for tool in tools if isinstance(tool, dict)]

def _workshop_tool_permission(tool: dict[str, Any]) -> str:
    annotations = tool.get("annotations") or {}
    return "read_only" if annotations.get("readOnlyHint") is True else "write"

async def refresh_workshop_memory_tools(force: bool = False) -> dict[str, dict[str, Any]]:
    """Discover local MCP tools; unknown or unannotated tools default to write."""
    global WORKSHOP_DYNAMIC_TOOLS, WORKSHOP_DYNAMIC_TOOLS_REFRESHED_AT
    if (
        not force
        and WORKSHOP_DYNAMIC_TOOLS_REFRESHED_AT
        and time.monotonic() - WORKSHOP_DYNAMIC_TOOLS_REFRESHED_AT < WORKSHOP_DYNAMIC_TOOLS_TTL
    ):
        return WORKSHOP_DYNAMIC_TOOLS
    try:
        endpoint_url = await select_workshop_memory_endpoint()
        discovered = await _list_workshop_memory_endpoint_tools(endpoint_url)
    except (MCPError, httpx.HTTPError, OSError, RuntimeError, ValueError):
        return WORKSHOP_DYNAMIC_TOOLS

    static_names = WORKSHOP_STATIC_TOOL_NAMES
    catalog: dict[str, dict[str, Any]] = {}
    for tool in discovered:
        name = str(tool.get("name") or "").strip()
        if (
            not name
            or len(name) > 64
            or not re.fullmatch(r"[A-Za-z0-9_-]+", name)
            or name in static_names
        ):
            continue
        parameters = tool.get("inputSchema")
        if not isinstance(parameters, dict) or parameters.get("type") != "object":
            parameters = {"type": "object", "properties": {}}
        parameters = dict(parameters)
        parameters.pop("$schema", None)
        catalog[name] = {
            "name": name,
            "description": str(tool.get("description") or f"Workshop Memory tool: {name}")[:1000],
            "parameters": parameters,
            "permission": _workshop_tool_permission(tool),
        }
    WORKSHOP_DYNAMIC_TOOLS = catalog
    WORKSHOP_DYNAMIC_TOOLS_REFRESHED_AT = time.monotonic()
    return catalog

def workshop_memory_function_tools() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["parameters"],
            "strict": False,
        }
        for tool in WORKSHOP_DYNAMIC_TOOLS.values()
    ]

def workshop_memory_tool_permission(name: str) -> str | None:
    if name in GMAIL_DIRECT_WRITE_TOOLS:
        return "write"
    if name in GMAIL_DIRECT_TOOL_NAMES:
        return "read_only"
    tool = WORKSHOP_DYNAMIC_TOOLS.get(name)
    return str(tool.get("permission")) if tool else None

async def probe_workshop_memory_endpoint(endpoint_url: str) -> tuple[bool, float, str | None]:
    started = time.perf_counter()
    try:
        await _call_workshop_memory_endpoint(
            endpoint_url,
            "check_server_status",
            {},
        )
        latency_ms = (time.perf_counter() - started) * 1000
        MCP_ENDPOINT_LATENCY_MS[endpoint_url] = round(latency_ms, 2)
        return True, latency_ms, None
    except (MCPError, httpx.HTTPError, OSError, RuntimeError) as exc:
        return False, (time.perf_counter() - started) * 1000, str(exc)

async def select_workshop_memory_endpoint(force: bool = False) -> str:
    global MCP_ACTIVE_URL, MCP_LAST_ERROR, MCP_LAST_LATENCY_MS

    if MCP_ACTIVE_URL and not force:
        return MCP_ACTIVE_URL

    errors: list[str] = []
    for endpoint_url in workshop_memory_candidates():
        ok, latency_ms, error = await probe_workshop_memory_endpoint(endpoint_url)
        if ok:
            MCP_ACTIVE_URL = endpoint_url
            MCP_LAST_LATENCY_MS = round(latency_ms, 2)
            MCP_LAST_ERROR = None
            return endpoint_url
        errors.append(f"{endpoint_url}: {error}")

    MCP_ACTIVE_URL = None
    MCP_LAST_ERROR = " | ".join(errors) or "No Workshop Memory endpoint configured"
    raise MCPError(MCP_LAST_ERROR)

async def call_workshop_memory_tool(
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    global MCP_ACTIVE_URL, MCP_LAST_ERROR, MCP_LAST_LATENCY_MS, MCP_LAST_SUCCESS_AT

    cached = get_cached_mcp_result(tool_name, arguments)
    if cached is not None:
        return {**cached, "_jarvis_cache": "hit"}

    async with MCP_LOCK:
        endpoint_url = await select_workshop_memory_endpoint()
        started = time.perf_counter()

        try:
            result = await _call_workshop_memory_endpoint(
                endpoint_url,
                tool_name,
                arguments,
            )
        except (MCPError, httpx.HTTPError, OSError, RuntimeError) as first_error:
            MCP_LAST_ERROR = str(first_error)
            MCP_ACTIVE_URL = None
            endpoint_url = await select_workshop_memory_endpoint(force=True)
            started = time.perf_counter()
            result = await _call_workshop_memory_endpoint(
                endpoint_url,
                tool_name,
                arguments,
            )

        MCP_LAST_LATENCY_MS = round((time.perf_counter() - started) * 1000, 2)
        MCP_LAST_SUCCESS_AT = time.time()
        MCP_LAST_ERROR = None
        set_cached_mcp_result(tool_name, arguments, result)
        return result

async def call_workshop_memory_tool_uncached(
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Call Workshop Memory without using a possibly stale post-write cache."""
    async with MCP_LOCK:
        endpoint_url = await select_workshop_memory_endpoint(force=True)
        return await _call_workshop_memory_endpoint(
            endpoint_url,
            tool_name,
            arguments,
        )


def workshop_memory_runtime_status() -> dict[str, Any]:
    return {
        "active_url": MCP_ACTIVE_URL,
        "candidates": workshop_memory_candidates(),
        "last_latency_ms": MCP_LAST_LATENCY_MS,
        "endpoint_latency_ms": dict(MCP_ENDPOINT_LATENCY_MS),
        "last_success_at_unix": MCP_LAST_SUCCESS_AT,
        "last_error": MCP_LAST_ERROR,
        "http_pool_open": bool(MCP_CLIENT and not MCP_CLIENT.is_closed),
        "cache_entries": len(MCP_TOOL_CACHE),
    }
