from __future__ import annotations

import json
from typing import Any

import httpx

from .plugin_policy import _github_discovered_permission, _is_github_plugin


PLUGIN_TIMEOUT: Any = httpx.Timeout(15.0, connect=4.0)


def configure_plugin_discovery(*, timeout: Any) -> None:
    global PLUGIN_TIMEOUT
    PLUGIN_TIMEOUT = timeout


def _mcp_response_json(response: Any) -> dict[str, Any]:
    content_type = str(response.headers.get("content-type") or "").lower()
    if "text/event-stream" not in content_type:
        return response.json()
    for line in response.text.splitlines():
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        return json.loads(payload)
    raise ValueError("MCP server returned no JSON event data")


async def discover_plugin_tools(url: str, token: str = "") -> list[dict[str, Any]]:
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(timeout=PLUGIN_TIMEOUT, follow_redirects=False) as client:
        response = await client.post(
            url,
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "ZBRANO Plugin Manager",
                        "version": "0.10.1",
                    },
                },
            },
        )
        if response.is_redirect:
            raise ValueError("MCP redirects are blocked")
        if response.is_error:
            raise ValueError(f"MCP initialize returned HTTP {response.status_code}")
        session_id = response.headers.get("mcp-session-id")
        if session_id:
            headers["mcp-session-id"] = session_id
        await client.post(
            url,
            headers=headers,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
        response = await client.post(
            url,
            headers=headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        if response.is_redirect:
            raise ValueError("MCP redirects are blocked")
        if response.is_error:
            raise ValueError(f"MCP tools/list returned HTTP {response.status_code}")
        try:
            tools = _mcp_response_json(response).get("result", {}).get("tools", [])
        except (ValueError, TypeError) as exc:
            raise ValueError("MCP server did not return JSON tool metadata") from exc

    result = []
    for tool in tools[:100]:
        name = str(tool.get("name") or "").strip()
        if name:
            is_github = _is_github_plugin(url=url)
            permission = (
                _github_discovered_permission(tool)
                if is_github
                else (
                    "read_only"
                    if (tool.get("annotations") or {}).get("readOnlyHint") is True
                    else "blocked"
                )
            )
            result.append({
                "name": name[:128],
                "description": str(tool.get("description") or "")[:1000],
                "permission": permission,
                "enabled": bool(is_github and permission in {"read_only", "write"}),
            })
    return result
