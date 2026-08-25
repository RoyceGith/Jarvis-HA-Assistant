from __future__ import annotations

import contextlib
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Awaitable


_timeout: Any = 15.0
_gmail_scopes: tuple[str, ...] = ()
_calendar_scopes: tuple[str, ...] = ()
_gmail_plugin_id: Callable[[], str] = lambda: ""
_oauth_records: Callable[[], dict[str, Any]] = lambda: {}
_oauth_scope_set: Callable[[str], set[str]] = lambda raw: set()
_oauth_safe_json: Callable[[Any, str], dict[str, Any]] = lambda response, label: {}
_oauth_validate_url: Callable[[Any, str], str] = lambda raw, label: str(raw or "")
_plugin_registry: Callable[[], dict[str, Any]] = lambda: {}
_plugin_secrets: Callable[[], dict[str, Any]] = lambda: {}
_plugin_save: Callable[[Path, dict[str, Any]], Any] = lambda path, data: None
_gmail_tool_records: Callable[[], list[dict[str, Any]]] = lambda: []
_registry_path = Path("/data/plugins/installed.json")
_secrets_path = Path("/data/plugins/secrets.json")
_oauth_path = Path("/data/plugins/oauth.json")


def configure_google_oauth_service(
    *,
    timeout: Any,
    gmail_scopes: tuple[str, ...],
    calendar_scopes: tuple[str, ...],
    gmail_plugin_id_fn: Callable[[], str],
    oauth_records_fn: Callable[[], dict[str, Any]],
    oauth_scope_set_fn: Callable[[str], set[str]],
    oauth_safe_json_fn: Callable[[Any, str], dict[str, Any]],
    oauth_validate_url_fn: Callable[[Any, str], str],
    plugin_registry_fn: Callable[[], dict[str, Any]],
    plugin_secrets_fn: Callable[[], dict[str, Any]],
    plugin_save_fn: Callable[[Path, dict[str, Any]], Any],
    gmail_tool_records_fn: Callable[[], list[dict[str, Any]]],
    registry_path: Path,
    secrets_path: Path,
    oauth_path: Path,
) -> None:
    global _timeout, _gmail_scopes, _calendar_scopes, _gmail_plugin_id
    global _oauth_records, _oauth_scope_set, _oauth_safe_json, _oauth_validate_url
    global _plugin_registry, _plugin_secrets, _plugin_save, _gmail_tool_records
    global _registry_path, _secrets_path, _oauth_path
    _timeout = timeout
    _gmail_scopes = gmail_scopes
    _calendar_scopes = calendar_scopes
    _gmail_plugin_id = gmail_plugin_id_fn
    _oauth_records = oauth_records_fn
    _oauth_scope_set = oauth_scope_set_fn
    _oauth_safe_json = oauth_safe_json_fn
    _oauth_validate_url = oauth_validate_url_fn
    _plugin_registry = plugin_registry_fn
    _plugin_secrets = plugin_secrets_fn
    _plugin_save = plugin_save_fn
    _gmail_tool_records = gmail_tool_records_fn
    _registry_path = registry_path
    _secrets_path = secrets_path
    _oauth_path = oauth_path


async def revoke_rejected_oauth_token(record: dict[str, Any], token: dict[str, Any]) -> None:
    import httpx

    endpoint_raw = str(record.get("revocation_endpoint") or "")
    candidate = str(token.get("refresh_token") or token.get("access_token") or "")
    if not endpoint_raw or not candidate:
        return
    with contextlib.suppress(ValueError, httpx.HTTPError):
        endpoint = _oauth_validate_url(endpoint_raw, "OAuth revocation endpoint")
        async with httpx.AsyncClient(timeout=_timeout, follow_redirects=False) as client:
            await client.post(endpoint, data={"token": candidate})


async def validate_gmail_oauth_grant(flow: dict[str, Any], token: dict[str, Any]) -> str:
    import httpx

    if flow.get("google_service") != "gmail":
        return ""
    required = set(_gmail_scopes)
    granted = _oauth_scope_set(token.get("scope"))
    if granted != required:
        await revoke_rejected_oauth_token(flow, token)
        missing = sorted(required - granted)
        unexpected = sorted(granted - required)
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if unexpected:
            details.append("unexpected " + ", ".join(unexpected))
        if not granted:
            details.append("provider returned no granted-scope list")
        raise ValueError("Gmail authorization was rejected by ZBRANO's least-privilege policy: " + "; ".join(details))
    access_token = str(token.get("access_token") or "")
    async with httpx.AsyncClient(timeout=_timeout, follow_redirects=False) as client:
        response = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/profile",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.is_error:
        await revoke_rejected_oauth_token(flow, token)
        raise ValueError(f"Gmail profile verification returned HTTP {response.status_code}")
    profile = _oauth_safe_json(response, "Gmail profile")
    account = str(profile.get("emailAddress") or "").strip()
    if not account or "@" not in account:
        await revoke_rejected_oauth_token(flow, token)
        raise ValueError("Gmail profile verification returned no account identity")
    return account[:320]


async def validate_google_calendar_oauth_grant(flow: dict[str, Any], token: dict[str, Any]) -> str:
    import httpx

    if flow.get("google_service") != "calendar":
        return ""
    required = set(_calendar_scopes)
    granted = _oauth_scope_set(token.get("scope"))
    if not required.issubset(granted):
        await revoke_rejected_oauth_token(flow, token)
        raise ValueError("Google Calendar authorization is missing required event or calendar-list access")
    access_token = str(token.get("access_token") or "")
    async with httpx.AsyncClient(timeout=_timeout, follow_redirects=False) as client:
        response = await client.get(
            "https://www.googleapis.com/calendar/v3/users/me/calendarList/primary",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.is_error:
        await revoke_rejected_oauth_token(flow, token)
        raise ValueError(f"Google Calendar verification returned HTTP {response.status_code}")
    profile = _oauth_safe_json(response, "Google Calendar profile")
    return str(profile.get("summary") or profile.get("id") or "Google Calendar")[:320]


async def enforce_stored_gmail_scope_policy() -> None:
    plugin_id = _gmail_plugin_id()
    records = _oauth_records()
    record = records.get(plugin_id)
    if not isinstance(record, dict):
        return
    granted = _oauth_scope_set(record.get("scope"))
    if granted == set(_gmail_scopes):
        registry = _plugin_registry()
        plugin = registry.get(plugin_id) or {}
        plugin.update({
            "name": "Gmail Direct",
            "url": "https://gmail.googleapis.com/gmail/v1",
            "catalog_id": "gmail-official",
            "enabled": True,
            "healthy": True,
            "last_error": None,
            "last_checked": time.time(),
            "tools": _gmail_tool_records(),
            "auth_mode": "oauth",
        })
        registry[plugin_id] = plugin
        _plugin_save(_registry_path, registry)
        return
    access_token = str(_plugin_secrets().get(plugin_id) or "")
    if access_token:
        await revoke_rejected_oauth_token(record, {"access_token": access_token})
    secrets = _plugin_secrets()
    secrets.pop(plugin_id, None)
    _plugin_save(_secrets_path, secrets)
    records.pop(plugin_id, None)
    _plugin_save(_oauth_path, records)
    registry = _plugin_registry()
    plugin = registry.get(plugin_id)
    if isinstance(plugin, dict):
        plugin.update({
            "enabled": False,
            "healthy": False,
            "last_error": "Gmail OAuth scope policy changed; reconnect required",
            "last_checked": time.time(),
            "oauth_account": "",
        })
        registry[plugin_id] = plugin
        _plugin_save(_registry_path, registry)
