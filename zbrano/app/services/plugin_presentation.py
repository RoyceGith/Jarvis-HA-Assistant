from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .plugin_policy import plugin_icon_url


_plugin_secrets: Callable[[], dict[str, Any]] = lambda: {}
_plugin_oauth_records: Callable[[], dict[str, Any]] = lambda: {}
_oauth_scope_set: Callable[[Any], set[str]] = lambda raw: set()


def configure_plugin_presentation(
    *,
    plugin_secrets_fn: Callable[[], dict[str, Any]],
    plugin_oauth_records_fn: Callable[[], dict[str, Any]],
    oauth_scope_set_fn: Callable[[Any], set[str]],
) -> None:
    global _plugin_secrets, _plugin_oauth_records, _oauth_scope_set
    _plugin_secrets = plugin_secrets_fn
    _plugin_oauth_records = plugin_oauth_records_fn
    _oauth_scope_set = oauth_scope_set_fn


def plugin_public(plugin_id: str, plugin: dict[str, Any]) -> dict[str, Any]:
    tools = list(plugin.get("tools") or [])
    enabled_tools = [
        tool for tool in tools
        if tool.get("enabled") and tool.get("permission") in {"read_only", "write"}
    ]
    enabled_tool_count = len(enabled_tools)
    approval_tool_count = sum(
        1 for tool in enabled_tools if tool.get("permission") == "write"
    )
    secrets = _plugin_secrets()
    oauth_records = _plugin_oauth_records()
    return {
        "id": plugin_id,
        "name": plugin.get("name", plugin_id),
        "url": plugin.get("url", ""),
        "icon_url": plugin_icon_url(
            str(plugin.get("name") or plugin_id), str(plugin.get("url") or "")
        ),
        "enabled": bool(plugin.get("enabled")),
        "healthy": bool(plugin.get("healthy")),
        "last_error": plugin.get("last_error"),
        "last_checked": plugin.get("last_checked"),
        "has_secret": bool(secrets.get(plugin_id)),
        "auth_mode": str(
            plugin.get("auth_mode") or ("bearer" if secrets.get(plugin_id) else "none")
        ),
        "oauth_connected": bool(
            plugin.get("auth_mode") == "oauth" and secrets.get(plugin_id)
        ),
        "oauth_provider": str(plugin.get("oauth_provider") or ""),
        "oauth_account": str(plugin.get("oauth_account") or ""),
        "oauth_scopes": sorted(
            _oauth_scope_set((oauth_records.get(plugin_id) or {}).get("scope"))
        ),
        "tools": tools,
        "enabled_tool_count": enabled_tool_count,
        "approval_tool_count": approval_tool_count,
        "available_to_chat": bool(plugin.get("enabled") and enabled_tool_count),
    }
