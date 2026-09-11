from __future__ import annotations

import json
import secrets
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Awaitable


GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"
GITHUB_DEVICE_FLOWS: dict[str, dict[str, Any]] = {}

_timeout: Any = 15.0
_catalog_entry: Callable[[str], Awaitable[dict[str, Any] | None]] | None = None
_install_plugin: Callable[[str, str, str], Awaitable[dict[str, Any]]] | None = None


class GitHubDeviceFlowError(RuntimeError):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def configure_github_device_oauth(
    *,
    timeout: Any,
    catalog_entry_fn: Callable[[str], Awaitable[dict[str, Any] | None]],
    install_plugin_fn: Callable[[str, str, str], Awaitable[dict[str, Any]]],
) -> None:
    global _timeout, _catalog_entry, _install_plugin
    _timeout = timeout
    _catalog_entry = catalog_entry_fn
    _install_plugin = install_plugin_fn


def github_oauth_client_id() -> str:
    try:
        options = json.loads(Path("/data/options.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return str(options.get("github_oauth_client_id") or "").strip()


async def start_github_device_flow(catalog_id: str) -> dict[str, Any]:
    if _catalog_entry is None:
        raise RuntimeError("GitHub Device Flow service is not configured")
    entry = await _catalog_entry(catalog_id)
    if not entry:
        raise GitHubDeviceFlowError(404, "Catalog plugin not found")
    if "github" not in f"{entry.get('name', '')} {entry.get('title', '')} {entry.get('url', '')}".lower():
        raise GitHubDeviceFlowError(400, "GitHub authorization is only available for GitHub plugins")
    client_id = github_oauth_client_id()
    if not client_id:
        raise GitHubDeviceFlowError(
            503,
            "GitHub OAuth is not configured. Add github_oauth_client_id to the ZBRANO add-on configuration using a GitHub OAuth App or GitHub App with Device Flow enabled, then reload the plugin catalog.",
        )
    import httpx

    async with httpx.AsyncClient(timeout=_timeout) as client:
        response = await client.post(
            "https://github.com/login/device/code",
            headers={"Accept": "application/json"},
            data={"client_id": client_id, "scope": "repo read:org"},
        )
        response.raise_for_status()
        payload = response.json()
    if payload.get("error"):
        raise GitHubDeviceFlowError(400, payload.get("error_description") or payload["error"])
    flow_id = secrets.token_urlsafe(24)
    now = time.time()
    interval = max(5, int(payload.get("interval") or 5))
    GITHUB_DEVICE_FLOWS[flow_id] = {
        "catalog_id": catalog_id,
        "device_code": payload["device_code"],
        "expires_at": now + int(payload.get("expires_in") or 900),
        "interval": interval,
        "next_poll": now + interval,
    }
    return {
        "flow_id": flow_id,
        "user_code": payload["user_code"],
        "verification_uri": payload.get("verification_uri") or "https://github.com/login/device",
        "expires_in": int(payload.get("expires_in") or 900),
        "interval": interval,
    }


async def complete_github_device_flow(flow_id: str) -> dict[str, Any]:
    if _catalog_entry is None or _install_plugin is None:
        raise RuntimeError("GitHub Device Flow service is not configured")
    flow = GITHUB_DEVICE_FLOWS.get(flow_id)
    if not flow:
        raise GitHubDeviceFlowError(404, "GitHub authorization flow not found")
    now = time.time()
    if now >= flow["expires_at"]:
        GITHUB_DEVICE_FLOWS.pop(flow_id, None)
        raise GitHubDeviceFlowError(410, "GitHub authorization expired")
    if now < flow["next_poll"]:
        return {"pending": True, "interval": max(1, int(flow["next_poll"] - now))}
    client_id = github_oauth_client_id()
    import httpx

    async with httpx.AsyncClient(timeout=_timeout) as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": client_id,
                "device_code": flow["device_code"],
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
        )
        response.raise_for_status()
        payload = response.json()
    error = payload.get("error")
    if error == "authorization_pending":
        flow["next_poll"] = time.time() + flow["interval"]
        return {"pending": True, "interval": flow["interval"]}
    if error == "slow_down":
        flow["interval"] += 5
        flow["next_poll"] = time.time() + flow["interval"]
        return {"pending": True, "interval": flow["interval"]}
    if error:
        GITHUB_DEVICE_FLOWS.pop(flow_id, None)
        raise GitHubDeviceFlowError(400, payload.get("error_description") or error)
    access_token = str(payload.get("access_token") or "")
    if not access_token:
        raise GitHubDeviceFlowError(502, "GitHub returned no access token")
    entry = await _catalog_entry(flow["catalog_id"])
    if not entry:
        raise GitHubDeviceFlowError(404, "Catalog plugin not found")
    result = await _install_plugin(
        str(entry.get("title") or entry.get("name") or "GitHub"),
        GITHUB_MCP_URL,
        access_token,
    )
    GITHUB_DEVICE_FLOWS.pop(flow_id, None)
    return {"pending": False, **result}
