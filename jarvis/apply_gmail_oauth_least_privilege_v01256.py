import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.56 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.56 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    oauth_policy = r'''GMAIL_MCP_OAUTH_SCOPES = (
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
)
GMAIL_MCP_RESOURCE_URL = "https://gmailmcp.googleapis.com/mcp/v1"


def _gmail_plugin_id() -> str:
    import hashlib

    return hashlib.sha256(GMAIL_MCP_RESOURCE_URL.encode()).hexdigest()[:16]


def _oauth_scope_set(raw: str) -> set[str]:
    return {scope for scope in str(raw or "").split() if scope}


async def _revoke_rejected_oauth_token(record: dict[str, Any], token: dict[str, Any]) -> None:
    endpoint_raw = str(record.get("revocation_endpoint") or "")
    candidate = str(token.get("refresh_token") or token.get("access_token") or "")
    if not endpoint_raw or not candidate:
        return
    with contextlib.suppress(ValueError, httpx.HTTPError):
        endpoint = _oauth_validate_https_url(endpoint_raw, "OAuth revocation endpoint")
        async with httpx.AsyncClient(timeout=PLUGIN_TIMEOUT, follow_redirects=False) as client:
            await client.post(endpoint, data={"token": candidate})


async def _validate_gmail_oauth_grant(flow: dict[str, Any], token: dict[str, Any]) -> str:
    if not flow.get("google_connector"):
        return ""
    required = set(GMAIL_MCP_OAUTH_SCOPES)
    granted = _oauth_scope_set(token.get("scope"))
    if granted != required:
        await _revoke_rejected_oauth_token(flow, token)
        missing = sorted(required - granted)
        unexpected = sorted(granted - required)
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if unexpected:
            details.append("unexpected " + ", ".join(unexpected))
        if not granted:
            details.append("provider returned no granted-scope list")
        raise ValueError(
            "Gmail authorization was rejected by ZBRANO's least-privilege policy: "
            + "; ".join(details)
        )
    access_token = str(token.get("access_token") or "")
    async with httpx.AsyncClient(timeout=PLUGIN_TIMEOUT, follow_redirects=False) as client:
        response = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/profile",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.is_error:
        await _revoke_rejected_oauth_token(flow, token)
        raise ValueError(f"Gmail profile verification returned HTTP {response.status_code}")
    profile = _oauth_safe_json(response, "Gmail profile")
    account = str(profile.get("emailAddress") or "").strip()
    if not account or "@" not in account:
        await _revoke_rejected_oauth_token(flow, token)
        raise ValueError("Gmail profile verification returned no account identity")
    return account[:320]


async def enforce_stored_gmail_scope_policy() -> None:
    plugin_id = _gmail_plugin_id()
    records = plugin_oauth_records()
    record = records.get(plugin_id)
    if not isinstance(record, dict):
        return
    granted = _oauth_scope_set(record.get("scope"))
    if granted == set(GMAIL_MCP_OAUTH_SCOPES):
        return
    access_token = str(plugin_secrets().get(plugin_id) or "")
    if access_token:
        await _revoke_rejected_oauth_token(record, {"access_token": access_token})
    secrets = plugin_secrets()
    secrets.pop(plugin_id, None)
    _plugin_save(PLUGIN_SECRETS_PATH, secrets)
    records.pop(plugin_id, None)
    _plugin_save(PLUGIN_OAUTH_PATH, records)
    registry = plugin_registry()
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
        _plugin_save(PLUGIN_REGISTRY_PATH, registry)


'''
    backend = replace_once(
        backend,
        "async def _oauth_start_for_target(name, resource_url, redirect_uri, catalog_id=\"\", plugin_id=\"\"):\n",
        oauth_policy + "async def _oauth_start_for_target(name, resource_url, redirect_uri, catalog_id=\"\", plugin_id=\"\"):\n",
        "Gmail OAuth least-privilege policy helpers",
    )

    backend = replace_once(
        backend,
        '''        "scope": " ".join(
            str(scope).strip() for scope in (
                resource_metadata.get("scopes_supported")
                or auth_metadata.get("scopes_supported") or []
            ) if str(scope).strip()
        )[:2000],''',
        '''        "scope": (
            " ".join(GMAIL_MCP_OAUTH_SCOPES)
            if google_connector else
            " ".join(
                str(scope).strip() for scope in (
                    resource_metadata.get("scopes_supported")
                    or auth_metadata.get("scopes_supported") or []
                ) if str(scope).strip()
            )[:2000]
        ),''',
        "exact Gmail authorization scopes",
    )
    backend = replace_once(
        backend,
        '''        query.update({"access_type": "offline", "prompt": "consent", "include_granted_scopes": "true"})''',
        '''        query.update({"access_type": "offline", "prompt": "select_account consent"})''',
        "Google account selection without incremental scopes",
    )
    backend = replace_once(
        backend,
        '''        access_token = str(token["access_token"])
        tools = await discover_plugin_tools(flow["resource_url"], access_token)''',
        '''        oauth_account = await _validate_gmail_oauth_grant(flow, token)
        access_token = str(token["access_token"])
        tools = await discover_plugin_tools(flow["resource_url"], access_token)''',
        "Gmail grant validation before tool discovery",
    )
    backend = replace_once(
        backend,
        '''            "oauth_provider": str(flow.get("authorization_endpoint") or "").split("/")[2],
            "oauth_connected_at": time.time(),''',
        '''            "oauth_provider": str(flow.get("authorization_endpoint") or "").split("/")[2],
            "oauth_connected_at": time.time(),
            "oauth_account": oauth_account,''',
        "connected Gmail account identity",
    )
    backend = replace_once(
        backend,
        '''        "oauth_provider": str(p.get("oauth_provider") or ""),''',
        '''        "oauth_provider": str(p.get("oauth_provider") or ""),
        "oauth_account": str(p.get("oauth_account") or ""),
        "oauth_scopes": sorted(_oauth_scope_set((plugin_oauth_records().get(pid) or {}).get("scope"))),''',
        "safe OAuth account and scope response",
    )
    backend = replace_once(
        backend,
        '''    prune_expired_chats()
    await refresh_plugin_oauth_tokens()''',
        '''    prune_expired_chats()
    await enforce_stored_gmail_scope_policy()
    await refresh_plugin_oauth_tokens()''',
        "stored Gmail token quarantine",
    )

    frontend = replace_once(
        frontend,
        '''<span class="plugin-meta">${pluginStateSummary}</span>${p.last_error?''',
        '''<span class="plugin-meta">${pluginStateSummary}</span>${p.oauth_connected?`<span class="plugin-meta">OAuth account: ${esc(p.oauth_account||"not reported")} · Granted scopes: ${esc((p.oauth_scopes||[]).join(", ")||"not reported")}</span>`:""}${p.last_error?''',
        "safe installed-plugin OAuth details",
    )
    frontend = replace_once(
        frontend,
        '''          const status=statusNode();
          if(status)status.textContent="Completing authorization through Home Assistant…";
          popup.location.replace(popupUrl.href);''',
        '''          const status=statusNode();
          if(status)status.textContent="Completing authorization through Home Assistantâ€¦";
          if(popup.document.body){
            popup.document.title="Completing authorization";
            popup.document.body.style.cssText="font:16px system-ui;background:#071015;color:#d9fbff;padding:2rem";
            popup.document.body.innerHTML="<h1>Completing authorization</h1><p>Returning securely through Home Assistantâ€¦</p>";
          }
          popup.location.replace(popupUrl.href);''',
        "Ingress callback transition screen",
    )

    backend = backend.replace('version="0.12.55"', 'version="0.12.56"')
    backend = backend.replace('"version": "0.12.55"', '"version": "0.12.56"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.55"', '"X-ZBRANO-Frontend-Version": "0.12.56"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.55"', '"name": "ZBRANO Developer Mode", "version": "0.12.56"')
    frontend = frontend.replace("HUD 0.12.55", "HUD 0.12.56")

    for marker in (
        'version="0.12.56"',
        "GMAIL_MCP_OAUTH_SCOPES = (",
        '"https://www.googleapis.com/auth/gmail.readonly"',
        '"https://www.googleapis.com/auth/gmail.compose"',
        '"prompt": "select_account consent"',
        "await _validate_gmail_oauth_grant(flow, token)",
        "await enforce_stored_gmail_scope_policy()",
        '"oauth_account": oauth_account',
        '"oauth_scopes": sorted(',
    ):
        require(backend, marker, marker)
    for marker in (
        "HUD 0.12.56",
        "OAuth account: ${esc(p.oauth_account",
        "Granted scopes: ${esc((p.oauth_scopes",
        'popup.document.title="Completing authorization"',
    ):
        require(frontend, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
