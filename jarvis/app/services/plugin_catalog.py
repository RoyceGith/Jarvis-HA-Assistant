from __future__ import annotations

import hashlib
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any


PLUGIN_CATALOG_CACHE_PATH = Path("/data/plugins/catalog-cache.json")
PLUGIN_CATALOG_TTL = 3600
MCP_REGISTRY_API = "https://registry.modelcontextprotocol.io/v0.1/servers"

FEATURED_REMOTE_PLUGINS = [
    {
        "id": "github-official", "name": "io.github.github/github-mcp-server", "title": "GitHub",
        "description": "Official GitHub MCP server for repositories, code, issues, pull requests, users, and workflows.",
        "url": "https://api.githubcopilot.com/mcp/", "category": "developer-tools", "verified": True,
        "auth_required": True, "auth_mode": "github-oauth", "installable": True, "publisher": "GitHub",
        "icon_url": "plugin-icons/github.svg", "docs_url": "https://docs.github.com/en/copilot/customizing-copilot/extending-copilot-chat-with-mcp",
    },
    {
        "id": "gmail-official", "name": "zbrano.gmail-direct", "title": "Gmail Direct",
        "description": "Built-in least-privilege connector using the standard Gmail REST API. Search, read, list labels, and create approval-gated drafts without the Workspace Developer Preview MCP.",
        "url": "https://gmailmcp.googleapis.com/mcp/v1", "category": "productivity", "verified": True,
        "auth_required": True, "auth_mode": "oauth", "installable": False, "oauth_connectable": True, "publisher": "ZBRANO + Google Gmail API",
        "setup_label": "Connect with Google", "availability": "Standard Gmail API",
        "icon_url": "plugin-icons/gmail.svg", "docs_url": "https://developers.google.com/workspace/gmail/api/guides/configure-mcp-server",
    },
    {
        "id": "google-drive-official", "name": "com.google.workspace/drive", "title": "Google Drive",
        "description": "Official Google Drive remote MCP server for file search, metadata, reading, downloads, and file creation.",
        "url": "https://drivemcp.googleapis.com/mcp/v1", "category": "productivity", "verified": True,
        "auth_required": True, "auth_mode": "oauth", "installable": False, "publisher": "Google",
        "setup_label": "OAuth setup required", "availability": "Developer Preview",
        "icon_url": "plugin-icons/googledrive.svg", "docs_url": "https://developers.google.com/workspace/drive/api/guides/configure-mcp-server",
    },
    {
        "id": "google-calendar-official", "name": "zbrano.google-calendar-direct", "title": "Google Calendar Direct",
        "description": "Two-way synchronization between Google Calendar and ZBRANO's visual calendar while preserving local Telegram reminders.",
        "url": "https://calendarmcp.googleapis.com/mcp/v1", "category": "productivity", "verified": True,
        "auth_required": True, "auth_mode": "oauth", "installable": False, "oauth_connectable": True, "publisher": "ZBRANO + Google Calendar API",
        "setup_label": "Connect with Google", "availability": "Standard Calendar API",
        "icon_url": "plugin-icons/googlecalendar.svg", "docs_url": "https://developers.google.com/workspace/calendar/api/guides/configure-mcp-server",
    },
    {
        "id": "google-chat-official", "name": "com.google.workspace/chat", "title": "Google Chat",
        "description": "Official Google Chat remote MCP server for conversations, messages, search, and sending messages.",
        "url": "https://chatmcp.googleapis.com/mcp/v1", "category": "productivity", "verified": True,
        "auth_required": True, "auth_mode": "oauth", "installable": False, "publisher": "Google",
        "setup_label": "OAuth setup required", "availability": "Developer Preview",
        "icon_url": "plugin-icons/googlechat.svg", "docs_url": "https://developers.google.com/workspace/guides/configure-mcp-servers",
    },
    {
        "id": "google-people-official", "name": "com.google.workspace/people", "title": "Google People",
        "description": "Official People API remote MCP server for user profiles, contacts, and directory search.",
        "url": "https://people.googleapis.com/mcp/v1", "category": "productivity", "verified": True,
        "auth_required": True, "auth_mode": "oauth", "installable": False, "publisher": "Google",
        "setup_label": "OAuth setup required", "availability": "Developer Preview",
        "icon_url": "", "docs_url": "https://developers.google.com/people/v1/configure-mcp-server",
    },
    {
        "id": "google-workspace-search-official", "name": "com.google.workspace/search", "title": "Google Workspace Search",
        "description": "Official universal search MCP server across Gmail, Drive, Calendar, and Google Chat.",
        "url": "https://workspacemcp.googleapis.com/mcp/v1", "category": "productivity", "verified": True,
        "auth_required": True, "auth_mode": "oauth", "installable": False, "publisher": "Google",
        "setup_label": "OAuth setup required", "availability": "Developer Preview",
        "icon_url": "", "docs_url": "https://developers.google.com/workspace/guides/universal-search-mcp",
    },
    {
        "id": "canva-official", "name": "com.canva/mcp", "title": "Canva",
        "description": "Official Canva remote MCP server for designs, assets, brand resources, exports, and collaboration.",
        "url": "https://mcp.canva.com/mcp", "category": "creative", "verified": True,
        "auth_required": True, "auth_mode": "oauth", "installable": False, "oauth_connectable": True, "publisher": "Canva",
        "setup_label": "Connect with Canva", "availability": "Access may require approval",
        "icon_url": "", "docs_url": "https://www.canva.dev/docs/mcp/",
    },
    {
        "id": "cloudflare-official", "name": "com.cloudflare/api-mcp", "title": "Cloudflare",
        "description": "Official Cloudflare API MCP server for Workers, DNS, R2, Zero Trust, security, and account configuration.",
        "url": "https://mcp.cloudflare.com/mcp", "category": "infrastructure", "verified": True,
        "auth_required": True, "auth_mode": "oauth", "installable": False, "oauth_connectable": True, "publisher": "Cloudflare",
        "setup_label": "Connect with Cloudflare",
        "icon_url": "plugin-icons/cloudflare.svg", "docs_url": "https://developers.cloudflare.com/agents/model-context-protocol/cloudflare/servers-for-cloudflare/",
    },
    {
        "id": "adobe-analytics-official", "name": "com.adobe/analytics-mcp", "title": "Adobe Analytics",
        "description": "Official Adobe Analytics remote MCP server for report suites, metrics, dimensions, segments, and reports.",
        "url": "https://aa-mcp.adobe.io/mcp", "category": "data", "verified": True,
        "auth_required": True, "auth_mode": "oauth", "installable": False, "publisher": "Adobe",
        "setup_label": "OAuth setup required",
        "icon_url": "", "docs_url": "https://developer.adobe.com/analytics-mcp/docs/aa/",
    },
]

_plugin_load: Callable[[Path], dict[str, Any]] = lambda path: {}
_plugin_save: Callable[[Path, dict[str, Any]], Any] = lambda path, data: None
_validate_plugin_url: Callable[[str], Any] = lambda url: url
_plugin_icon_url: Callable[[str, str], str] = lambda name, url: ""
_plugin_registry: Callable[[], dict[str, dict[str, Any]]] = lambda: {}
_plugin_url_key: Callable[[Any], str] = lambda url: str(url or "")
_gmail_plugin_id: Callable[[], str] = lambda: ""
_google_calendar_plugin_id: Callable[[], str] = lambda: ""
_github_oauth_client_id: Callable[[], str] = lambda: ""


def configure_plugin_catalog_service(
    *,
    plugin_load_fn: Callable[[Path], dict[str, Any]],
    plugin_save_fn: Callable[[Path, dict[str, Any]], Any],
    validate_plugin_url_fn: Callable[[str], Any],
    plugin_icon_url_fn: Callable[[str, str], str],
    plugin_registry_fn: Callable[[], dict[str, dict[str, Any]]],
    plugin_url_key_fn: Callable[[Any], str],
    gmail_plugin_id_fn: Callable[[], str],
    google_calendar_plugin_id_fn: Callable[[], str],
    github_oauth_client_id_fn: Callable[[], str],
) -> None:
    global _plugin_load, _plugin_save, _validate_plugin_url, _plugin_icon_url
    global _plugin_registry, _plugin_url_key, _gmail_plugin_id
    global _google_calendar_plugin_id, _github_oauth_client_id
    _plugin_load = plugin_load_fn
    _plugin_save = plugin_save_fn
    _validate_plugin_url = validate_plugin_url_fn
    _plugin_icon_url = plugin_icon_url_fn
    _plugin_registry = plugin_registry_fn
    _plugin_url_key = plugin_url_key_fn
    _gmail_plugin_id = gmail_plugin_id_fn
    _google_calendar_plugin_id = google_calendar_plugin_id_fn
    _github_oauth_client_id = github_oauth_client_id_fn


def catalog_cache_read() -> list[dict[str, Any]] | None:
    data = _plugin_load(PLUGIN_CATALOG_CACHE_PATH)
    if not data:
        return None
    if time.time() - float(data.get("saved_at") or 0) > PLUGIN_CATALOG_TTL:
        return None
    plugins = data.get("plugins")
    return plugins if isinstance(plugins, list) else None


def catalog_remote_entry(server: Any) -> dict[str, Any] | None:
    if not isinstance(server, dict):
        return None
    wrapper = server
    if isinstance(server.get("server"), dict):
        server = server["server"]
    name = str(server.get("name") or "").strip()
    description = str(server.get("description") or "").strip()
    version = str(server.get("version") or "").strip()
    title = str(server.get("title") or name).strip()
    if not name:
        return None
    remotes = server.get("remotes") or []
    if isinstance(remotes, dict):
        remotes = [remotes]
    url = ""
    auth_required = False
    for remote in remotes:
        if not isinstance(remote, dict):
            continue
        candidate = str(remote.get("url") or remote.get("endpoint") or remote.get("uri") or "").strip()
        if not candidate.startswith("https://"):
            continue
        try:
            _validate_plugin_url(candidate)
        except ValueError:
            continue
        url = candidate
        auth_required = bool(remote.get("authentication") or remote.get("auth") or remote.get("headers"))
        break
    packages = server.get("packages") or []
    if isinstance(packages, dict):
        packages = [packages]
    package_labels = []
    for package in packages:
        if not isinstance(package, dict):
            continue
        identifier = str(package.get("identifier") or package.get("name") or package.get("package") or "").strip()
        registry_type = str(package.get("registryType") or package.get("registry_type") or package.get("type") or "").strip()
        if identifier:
            package_labels.append(f"{registry_type}:{identifier}" if registry_type else identifier)
    package_ref = ", ".join(package_labels[:4])
    lower = f"{name} {title} {description} {package_ref}".lower()
    if any(word in lower for word in ("github", "gitlab", "code", "developer", "repository")):
        category = "developer-tools"
    elif any(word in lower for word in ("calendar", "mail", "task", "docs", "productivity")):
        category = "productivity"
    elif any(word in lower for word in ("database", "data", "analytics", "search", "redis", "sql")):
        category = "data"
    else:
        category = "other"
    meta = wrapper.get("_meta") or wrapper.get("meta") or {}
    identity = url or package_ref or name
    return {
        "id": hashlib.sha256(f"{name}|{version}|{identity}".encode()).hexdigest()[:20],
        "name": name,
        "title": title[:120],
        "description": description[:1000],
        "version": version[:80],
        "url": url,
        "package_ref": package_ref[:500],
        "installable": bool(url),
        "category": category,
        "verified": bool(server.get("verified") or server.get("official") or meta.get("official")),
        "auth_required": auth_required,
        "publisher": str(server.get("publisher") or "")[:120],
        "icon_url": _plugin_icon_url(title, url),
        "docs_url": str((server.get("repository") or {}).get("url") or "")[:500] if isinstance(server.get("repository"), dict) else "",
    }


def catalog_with_featured(items: Any) -> list[dict[str, Any]]:
    merged = [dict(item) for item in FEATURED_REMOTE_PLUGINS]
    seen = {str(item.get("url") or item.get("id") or "") for item in merged}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        key = str(item.get("url") or item.get("id") or "")
        if key and key in seen:
            continue
        merged.append(item)
        if key:
            seen.add(key)
    return merged


async def fetch_plugin_catalog(force: bool = False) -> tuple[list[dict[str, Any]], bool, str | None]:
    import httpx

    if not force:
        cached = catalog_cache_read()
        if cached is not None:
            return catalog_with_featured(cached), True, None
    plugins = list(FEATURED_REMOTE_PLUGINS)
    registry_error = None
    try:
        cursor = None
        pages = 0
        async with httpx.AsyncClient(timeout=httpx.Timeout(4.0, connect=2.0), follow_redirects=False) as client:
            while pages < 10:
                params: dict[str, Any] = {"limit": 100}
                if cursor:
                    params["cursor"] = cursor
                response = await client.get(MCP_REGISTRY_API, params=params)
                if response.is_redirect:
                    raise ValueError("Registry redirects are blocked")
                response.raise_for_status()
                payload = response.json()
                for server in payload.get("servers") or payload.get("items") or []:
                    entry = catalog_remote_entry(server)
                    if entry and not any(item["url"] == entry["url"] for item in plugins):
                        plugins.append(entry)
                metadata = payload.get("metadata") or payload.get("_meta") or {}
                cursor = metadata.get("nextCursor") or metadata.get("next_cursor")
                pages += 1
                if not cursor:
                    break
    except Exception as exc:
        registry_error = str(exc)
        cached = catalog_cache_read()
        if cached is not None:
            return catalog_with_featured(cached), True, registry_error
    _plugin_save(PLUGIN_CATALOG_CACHE_PATH, {"saved_at": time.time(), "plugins": plugins})
    return plugins, False, registry_error


def verify_catalog_result_contract(result: Any) -> tuple[list[dict[str, Any]], bool, str | None]:
    if not isinstance(result, tuple) or len(result) != 3:
        raise RuntimeError("Plugin catalog result must be a 3-item tuple")
    plugins, cached, registry_error = result
    if not isinstance(plugins, list):
        raise RuntimeError("Plugin catalog plugins must be a list")
    if not isinstance(cached, bool):
        raise RuntimeError("Plugin catalog cached flag must be boolean")
    if registry_error is not None and not isinstance(registry_error, str):
        raise RuntimeError("Plugin catalog registry error must be text or null")
    return plugins, cached, registry_error


async def catalog_entry(catalog_id: str) -> dict[str, Any] | None:
    plugins, _, _ = verify_catalog_result_contract(await fetch_plugin_catalog(force=False))
    return next((item for item in plugins if item.get("id") == catalog_id), None)


async def plugin_catalog_payload(q: str = "", category: str = "", refresh: bool = False) -> dict[str, Any]:
    plugins, cached, registry_error = verify_catalog_result_contract(await fetch_plugin_catalog(force=refresh))
    query = q.strip().lower()
    result = []
    for plugin in plugins:
        haystack = " ".join(str(plugin.get(key) or "") for key in ("name", "title", "description", "publisher")).lower()
        if query and query not in haystack:
            continue
        if category and plugin.get("category") != category:
            continue
        result.append(plugin)
    result.sort(key=lambda item: (not bool(item.get("verified")), str(item.get("title") or item.get("name")).lower()))
    registry = _plugin_registry()
    installed_by_url = {_plugin_url_key(plugin.get("url")): plugin for plugin in registry.values()}
    installed_plugins = list(registry.values())
    for item in result:
        installed = installed_by_url.get(_plugin_url_key(item.get("url")))
        if item.get("id") == "gmail-official":
            installed = registry.get(_gmail_plugin_id()) or installed
        elif item.get("id") == "google-calendar-official":
            installed = registry.get(_google_calendar_plugin_id()) or installed
        if not installed and "github" in f"{item.get('name','')} {item.get('title','')} {item.get('url','')}".lower():
            installed = next((plugin for plugin in installed_plugins if "github" in f"{plugin.get('name','')} {plugin.get('url','')}".lower()), None)
        item["installed"] = bool(installed)
        item["installed_enabled"] = bool(installed and installed.get("enabled"))
        if item.get("id") == "github-official":
            item["auth_mode"] = "github-oauth"
            item["oauth_available"] = bool(_github_oauth_client_id())
        elif item.get("id") in {"gmail-official", "google-calendar-official"}:
            google_ready = bool(os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip() and os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip())
            item["oauth_available"] = google_ready
            item["oauth_connectable"] = True
            item["setup_label"] = "Connect with Google" if google_ready else "Google OAuth setup required"
        elif item.get("auth_mode") == "oauth":
            item["oauth_available"] = bool(item.get("oauth_connectable"))
        else:
            item["auth_mode"] = "bearer" if item.get("auth_required") else "none"
            item["oauth_available"] = False
    return {
        "plugins": result[:500],
        "cached": cached,
        "registry_error": registry_error,
        "source": "Official MCP Registry plus curated official remote connectors",
    }
