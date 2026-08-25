from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import re
import secrets
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse


PLUGIN_OAUTH_PATH = Path("/data/plugins/oauth.json")
PLUGIN_OAUTH_FLOWS: dict[str, dict[str, Any]] = {}

_plugin_load: Callable[[Path], dict[str, Any]] = lambda path: {}
_validate_plugin_url: Callable[[str], str] = lambda url: url
_timeout: Any = 15.0
_runtime_version = ""


def configure_plugin_oauth_service(
    *,
    plugin_load_fn: Callable[[Path], dict[str, Any]],
    validate_plugin_url_fn: Callable[[str], str],
    timeout: Any,
    runtime_version: str,
) -> None:
    global _plugin_load, _validate_plugin_url, _timeout, _runtime_version
    _plugin_load = plugin_load_fn
    _validate_plugin_url = validate_plugin_url_fn
    _timeout = timeout
    _runtime_version = runtime_version


def plugin_oauth_records() -> dict[str, Any]:
    return _plugin_load(PLUGIN_OAUTH_PATH)


def oauth_safe_json(response: Any, label: str) -> dict[str, Any]:
    if len(response.content) > 131072:
        raise ValueError(f"{label} response is too large")
    try:
        payload = response.json()
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{label} did not return JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} returned an invalid document")
    return payload


def oauth_validate_https_url(raw: Any, label: str) -> str:
    try:
        return _validate_plugin_url(str(raw or ""))
    except ValueError as exc:
        raise ValueError(f"{label}: {exc}") from exc


def oauth_validate_redirect_uri(raw: Any) -> str:
    value = str(raw or "").strip()
    parsed = urlparse(value)
    local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if not (parsed.scheme == "https" or local_http):
        raise ValueError("OAuth callback must use HTTPS, or HTTP on localhost")
    if not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("OAuth callback URL is invalid")
    if parsed.query or not parsed.path.endswith("/api/plugin-oauth/callback"):
        raise ValueError("OAuth callback must end with /api/plugin-oauth/callback")
    return value


def oauth_well_known_url(issuer: str, suffix: str) -> str:
    parsed = urlparse(issuer)
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme, parsed.netloc, f"/.well-known/{suffix}{path}", "", "", ""))


def oauth_pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    return verifier, challenge


async def oauth_discover(resource_url: str, allow_pre_registered: bool = False) -> tuple[str, dict[str, Any], dict[str, Any]]:
    import httpx

    resource_url = oauth_validate_https_url(resource_url, "MCP resource URL")
    headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    initialize = {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "ZBRANO Plugin Manager", "version": _runtime_version},
        },
    }
    async with httpx.AsyncClient(timeout=_timeout, follow_redirects=False) as client:
        response = await client.post(resource_url, headers=headers, json=initialize)
        authenticate = str(response.headers.get("www-authenticate") or "")
        match = re.search(r'resource_metadata="([^"]+)"', authenticate, re.IGNORECASE)
        metadata_urls = []
        if match:
            metadata_urls.append(match.group(1))
        parsed = urlparse(resource_url)
        metadata_urls.extend([
            urlunparse((parsed.scheme, parsed.netloc, f"/.well-known/oauth-protected-resource{parsed.path}", "", "", "")),
            urlunparse((parsed.scheme, parsed.netloc, "/.well-known/oauth-protected-resource", "", "", "")),
        ])
        resource_metadata = None
        last_error = "OAuth protected-resource metadata was not advertised"
        for metadata_url in dict.fromkeys(metadata_urls):
            try:
                metadata_url = oauth_validate_https_url(metadata_url, "OAuth resource metadata URL")
                metadata_response = await client.get(metadata_url)
                if metadata_response.is_redirect:
                    raise ValueError("OAuth resource metadata redirects are blocked")
                if metadata_response.is_error:
                    last_error = f"OAuth resource metadata returned HTTP {metadata_response.status_code}"
                    continue
                resource_metadata = oauth_safe_json(metadata_response, "OAuth resource metadata")
                break
            except (httpx.HTTPError, ValueError) as exc:
                last_error = str(exc)
        if resource_metadata is None:
            raise ValueError(last_error)
        advertised_resource = str(resource_metadata.get("resource") or "").rstrip("/")
        if advertised_resource and advertised_resource != resource_url.rstrip("/"):
            raise ValueError("OAuth metadata resource does not match the selected MCP server")
        authorization_servers = resource_metadata.get("authorization_servers") or []
        if not isinstance(authorization_servers, list) or not authorization_servers:
            raise ValueError("OAuth metadata did not advertise an authorization server")
        issuer = oauth_validate_https_url(authorization_servers[0], "OAuth authorization server")
        auth_metadata_url = oauth_validate_https_url(
            oauth_well_known_url(issuer, "oauth-authorization-server"),
            "OAuth authorization metadata URL",
        )
        auth_response = await client.get(auth_metadata_url)
        if auth_response.is_redirect:
            raise ValueError("OAuth authorization metadata redirects are blocked")
        if auth_response.is_error:
            raise ValueError(f"OAuth authorization metadata returned HTTP {auth_response.status_code}")
        auth_metadata = oauth_safe_json(auth_response, "OAuth authorization metadata")
    if str(auth_metadata.get("issuer") or "").rstrip("/") != issuer.rstrip("/"):
        raise ValueError("OAuth authorization metadata issuer mismatch")
    for field in ("authorization_endpoint", "token_endpoint"):
        auth_metadata[field] = oauth_validate_https_url(auth_metadata.get(field), f"OAuth {field}")
    registration_endpoint = auth_metadata.get("registration_endpoint")
    if registration_endpoint:
        auth_metadata["registration_endpoint"] = oauth_validate_https_url(registration_endpoint, "OAuth registration endpoint")
    elif not allow_pre_registered:
        raise ValueError("This provider requires a pre-registered OAuth client")
    if "S256" not in (auth_metadata.get("code_challenge_methods_supported") or []):
        raise ValueError("OAuth provider does not advertise required PKCE S256 support")
    return resource_url, resource_metadata, auth_metadata


async def oauth_register_client(auth_metadata: dict[str, Any], redirect_uri: str) -> dict[str, str]:
    import httpx

    registration = {
        "client_name": "ZBRANO Home Assistant",
        "redirect_uris": [redirect_uri],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }
    async with httpx.AsyncClient(timeout=_timeout, follow_redirects=False) as client:
        response = await client.post(auth_metadata["registration_endpoint"], json=registration)
    if response.is_redirect:
        raise ValueError("OAuth client registration redirects are blocked")
    if response.is_error:
        detail = ""
        with contextlib.suppress(ValueError, TypeError):
            payload = response.json()
            detail = str(payload.get("error_description") or payload.get("error") or "")[:300]
        raise ValueError(detail or f"OAuth client registration returned HTTP {response.status_code}")
    client_data = oauth_safe_json(response, "OAuth client registration")
    client_id = str(client_data.get("client_id") or "")
    if not client_id:
        raise ValueError("OAuth registration returned no client ID")
    return {
        "client_id": client_id,
        "client_secret": str(client_data.get("client_secret") or ""),
        "token_endpoint_auth_method": str(client_data.get("token_endpoint_auth_method") or "none"),
    }


def oauth_token_request_auth(data: dict[str, Any], record: dict[str, Any]) -> Any:
    import httpx

    method = str(record.get("token_endpoint_auth_method") or "none")
    secret = str(record.get("client_secret") or "")
    if method == "client_secret_basic" and secret:
        return httpx.BasicAuth(str(record["client_id"]), secret)
    data["client_id"] = str(record["client_id"])
    if method == "client_secret_post" and secret:
        data["client_secret"] = secret
    return None


async def oauth_exchange_token(record: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    import httpx

    data = {key: value for key, value in data.items() if value not in {"", None}}
    auth = oauth_token_request_auth(data, record)
    async with httpx.AsyncClient(timeout=_timeout, follow_redirects=False) as client:
        response = await client.post(record["token_endpoint"], data=data, auth=auth)
    if response.is_redirect:
        raise ValueError("OAuth token redirects are blocked")
    payload = oauth_safe_json(response, "OAuth token endpoint")
    if response.is_error or payload.get("error"):
        raise ValueError(str(payload.get("error_description") or payload.get("error") or f"HTTP {response.status_code}")[:500])
    if str(payload.get("token_type") or "Bearer").lower() != "bearer":
        raise ValueError("OAuth provider returned an unsupported token type")
    if not payload.get("access_token"):
        raise ValueError("OAuth provider returned no access token")
    return payload


def oauth_popup_response(success: bool, message: str, plugin_id: str = "") -> Any:
    from fastapi.responses import Response

    payload = json.dumps({
        "type": "zbrano-plugin-oauth",
        "success": bool(success),
        "message": str(message)[:500],
        "plugin_id": str(plugin_id),
    }).replace("</", "<\\/")
    title = "Authorization complete" if success else "Authorization failed"
    body = "You can close this window." if success else "Return to ZBRANO and try again."
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>{title}</title></head>
<body style="font:16px system-ui;background:#071015;color:#d9fbff;padding:2rem">
<h1>{title}</h1><p>{body}</p><script>
if(window.opener)window.opener.postMessage({payload}, window.location.origin);
window.setTimeout(()=>window.close(),700);
</script></body></html>"""
    return Response(
        content=html,
        media_type="text/html",
        headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'",
            "X-Content-Type-Options": "nosniff",
        },
    )


def oauth_scope_set(raw: str) -> set[str]:
    return {scope for scope in str(raw or "").split() if scope}
