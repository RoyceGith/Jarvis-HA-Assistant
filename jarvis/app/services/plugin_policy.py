from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urlparse


PLUGIN_ICON_RULES = (
    (("gmail", "gmailmcp.googleapis.com"), "plugin-icons/gmail.svg"),
    (("google drive", "drivemcp.googleapis.com"), "plugin-icons/googledrive.svg"),
    (("google calendar", "calendarmcp.googleapis.com"), "plugin-icons/googlecalendar.svg"),
    (("google chat", "chatmcp.googleapis.com"), "plugin-icons/googlechat.svg"),
    (("google people", "people.googleapis.com/mcp"), ""),
    (("google workspace", "workspacemcp.googleapis.com"), ""),
    (("github", "githubcopilot.com/mcp"), "plugin-icons/github.svg"),
    (("canva", "mcp.canva.com"), ""),
    (("cloudflare", "mcp.cloudflare.com"), "plugin-icons/cloudflare.svg"),
    (("adobe", "aa-mcp.adobe.io"), ""),
)


def validate_plugin_url(raw: str) -> str:
    url = raw.strip()
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only credential-free public HTTPS URLs are accepted")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise ValueError("Local MCP endpoints are blocked")
    try:
        addresses = socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("MCP hostname could not be resolved") from exc
    if any(not ipaddress.ip_address(address[4][0]).is_global for address in addresses):
        raise ValueError("MCP endpoint resolves to a private, loopback, reserved, or link-local address")
    return url


def plugin_icon_url(name: str = "", url: str = "") -> str:
    identity = f"{name} {url}".lower()
    for terms, icon_url in PLUGIN_ICON_RULES:
        if any(term in identity for term in terms):
            return icon_url
    return ""


def _plugin_url_key(url: Any) -> str:
    return str(url or "").strip().rstrip("/").lower()


def _is_github_plugin(url: str = "", name: str = "") -> bool:
    value = f"{url} {name}".lower()
    return "github" in value or "githubcopilot.com/mcp" in value


def _github_discovered_permission(tool: dict[str, Any]) -> str:
    annotations = tool.get("annotations") or {}
    return "read_only" if annotations.get("readOnlyHint") is True else "write"


def _apply_github_tool_policy(registry: dict[str, Any]) -> bool:
    """Migrate installed GitHub plugins to the v0.11.29 approval policy."""
    changed = False
    for plugin in registry.values():
        if not isinstance(plugin, dict) or not _is_github_plugin(
            str(plugin.get("url") or ""), str(plugin.get("name") or "")
        ):
            continue
        if not plugin.get("enabled"):
            plugin["enabled"] = True
            changed = True
        for tool in plugin.get("tools") or []:
            if not isinstance(tool, dict):
                continue
            permission = str(tool.get("permission") or "blocked")
            desired = "read_only" if permission == "read_only" else "write"
            if tool.get("permission") != desired:
                tool["permission"] = desired
                changed = True
            if not tool.get("enabled"):
                tool["enabled"] = True
                changed = True
    return changed
