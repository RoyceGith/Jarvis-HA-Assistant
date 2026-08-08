from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.9 patch missing: {label}")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")

    fastapi_import = "from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect"
    require(text, fastapi_import, "FastAPI imports")
    text = text.replace(
        fastapi_import,
        "from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect",
        1,
    )

    model_marker = '''class CatalogInstallRequest(BaseModel):
    bearer_token: str = Field(default="", max_length=4000)


'''
    require(text, model_marker, "catalog request model")
    text = text.replace(
        model_marker,
        model_marker
        + '''class PluginOAuthStartRequest(BaseModel):
    redirect_uri: str = Field(min_length=12, max_length=1000)


''',
        1,
    )

    public_secret = '        "has_secret": bool(plugin_secrets().get(pid)),\n'
    require(text, public_secret, "plugin public authentication state")
    text = text.replace(
        public_secret,
        '''        "has_secret": bool(plugin_secrets().get(pid)),
        "auth_mode": str(p.get("auth_mode") or ("bearer" if plugin_secrets().get(pid) else "none")),
        "oauth_connected": bool(p.get("auth_mode") == "oauth" and plugin_secrets().get(pid)),
        "oauth_provider": str(p.get("oauth_provider") or ""),
''',
        1,
    )

    oauth_marker = "GITHUB_DEVICE_FLOWS = {}\n"
    require(text, oauth_marker, "OAuth backend insertion point")
    backend = r'''PLUGIN_OAUTH_PATH = Path("/data/plugins/oauth.json")
PLUGIN_OAUTH_FLOWS = {}
PLUGIN_OAUTH_REFRESH_TASK = None


def plugin_oauth_records():
    return _plugin_load(PLUGIN_OAUTH_PATH)


def _oauth_safe_json(response, label):
    if len(response.content) > 131072:
        raise ValueError(f"{label} response is too large")
    try:
        payload = response.json()
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{label} did not return JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} returned an invalid document")
    return payload


def _oauth_validate_https_url(raw, label):
    try:
        return validate_plugin_url(str(raw or ""))
    except ValueError as exc:
        raise ValueError(f"{label}: {exc}") from exc


def _oauth_validate_redirect_uri(raw):
    from urllib.parse import urlparse

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


def _oauth_well_known_url(issuer, suffix):
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(issuer)
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme, parsed.netloc, f"/.well-known/{suffix}{path}", "", "", ""))


def _oauth_pkce():
    import base64
    import hashlib
    import secrets

    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    return verifier, challenge


async def _oauth_discover(resource_url):
    import re
    from urllib.parse import urlparse, urlunparse

    resource_url = _oauth_validate_https_url(resource_url, "MCP resource URL")
    headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    initialize = {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "ZBRANO Plugin Manager", "version": "0.12.9"},
        },
    }
    async with httpx.AsyncClient(timeout=PLUGIN_TIMEOUT, follow_redirects=False) as client:
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
                metadata_url = _oauth_validate_https_url(metadata_url, "OAuth resource metadata URL")
                metadata_response = await client.get(metadata_url)
                if metadata_response.is_redirect:
                    raise ValueError("OAuth resource metadata redirects are blocked")
                if metadata_response.is_error:
                    last_error = f"OAuth resource metadata returned HTTP {metadata_response.status_code}"
                    continue
                resource_metadata = _oauth_safe_json(metadata_response, "OAuth resource metadata")
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
        issuer = _oauth_validate_https_url(authorization_servers[0], "OAuth authorization server")
        auth_metadata_url = _oauth_validate_https_url(
            _oauth_well_known_url(issuer, "oauth-authorization-server"),
            "OAuth authorization metadata URL",
        )
        auth_response = await client.get(auth_metadata_url)
        if auth_response.is_redirect:
            raise ValueError("OAuth authorization metadata redirects are blocked")
        if auth_response.is_error:
            raise ValueError(f"OAuth authorization metadata returned HTTP {auth_response.status_code}")
        auth_metadata = _oauth_safe_json(auth_response, "OAuth authorization metadata")

    if str(auth_metadata.get("issuer") or "").rstrip("/") != issuer.rstrip("/"):
        raise ValueError("OAuth authorization metadata issuer mismatch")
    for field in ("authorization_endpoint", "token_endpoint"):
        auth_metadata[field] = _oauth_validate_https_url(auth_metadata.get(field), f"OAuth {field}")
    registration_endpoint = auth_metadata.get("registration_endpoint")
    if not registration_endpoint:
        raise ValueError("This provider requires a pre-registered OAuth client")
    auth_metadata["registration_endpoint"] = _oauth_validate_https_url(
        registration_endpoint, "OAuth registration endpoint"
    )
    methods = auth_metadata.get("code_challenge_methods_supported") or []
    if "S256" not in methods:
        raise ValueError("OAuth provider does not advertise required PKCE S256 support")
    return resource_url, resource_metadata, auth_metadata


async def _oauth_register_client(auth_metadata, redirect_uri):
    registration = {
        "client_name": "ZBRANO Home Assistant",
        "redirect_uris": [redirect_uri],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }
    async with httpx.AsyncClient(timeout=PLUGIN_TIMEOUT, follow_redirects=False) as client:
        response = await client.post(auth_metadata["registration_endpoint"], json=registration)
    if response.is_redirect:
        raise ValueError("OAuth client registration redirects are blocked")
    if response.is_error:
        detail = ""
        with contextlib.suppress(ValueError, TypeError):
            payload = response.json()
            detail = str(payload.get("error_description") or payload.get("error") or "")[:300]
        raise ValueError(detail or f"OAuth client registration returned HTTP {response.status_code}")
    client_data = _oauth_safe_json(response, "OAuth client registration")
    client_id = str(client_data.get("client_id") or "")
    if not client_id:
        raise ValueError("OAuth registration returned no client ID")
    return {
        "client_id": client_id,
        "client_secret": str(client_data.get("client_secret") or ""),
        "token_endpoint_auth_method": str(client_data.get("token_endpoint_auth_method") or "none"),
    }


def _oauth_token_request_auth(data, record):
    method = str(record.get("token_endpoint_auth_method") or "none")
    secret = str(record.get("client_secret") or "")
    if method == "client_secret_basic" and secret:
        return httpx.BasicAuth(str(record["client_id"]), secret)
    data["client_id"] = str(record["client_id"])
    if method == "client_secret_post" and secret:
        data["client_secret"] = secret
    return None


async def _oauth_exchange_token(record, data):
    auth = _oauth_token_request_auth(data, record)
    async with httpx.AsyncClient(timeout=PLUGIN_TIMEOUT, follow_redirects=False) as client:
        response = await client.post(record["token_endpoint"], data=data, auth=auth)
    if response.is_redirect:
        raise ValueError("OAuth token redirects are blocked")
    payload = _oauth_safe_json(response, "OAuth token endpoint")
    if response.is_error or payload.get("error"):
        raise ValueError(str(payload.get("error_description") or payload.get("error") or f"HTTP {response.status_code}")[:500])
    if str(payload.get("token_type") or "Bearer").lower() != "bearer":
        raise ValueError("OAuth provider returned an unsupported token type")
    if not payload.get("access_token"):
        raise ValueError("OAuth provider returned no access token")
    return payload


def _oauth_popup_response(success, message, plugin_id=""):
    payload = json.dumps({
        "type": "zbrano-plugin-oauth", "success": bool(success),
        "message": str(message)[:500], "plugin_id": str(plugin_id),
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


async def _oauth_start_for_target(name, resource_url, redirect_uri, catalog_id="", plugin_id=""):
    import secrets
    from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

    redirect_uri = _oauth_validate_redirect_uri(redirect_uri)
    if len(PLUGIN_OAUTH_FLOWS) >= 20:
        expired = [key for key, flow in PLUGIN_OAUTH_FLOWS.items() if flow.get("expires_at", 0) <= time.time()]
        for key in expired:
            PLUGIN_OAUTH_FLOWS.pop(key, None)
    if len(PLUGIN_OAUTH_FLOWS) >= 20:
        raise ValueError("Too many OAuth authorizations are already pending")

    resource_url, resource_metadata, auth_metadata = await _oauth_discover(resource_url)
    client_data = await _oauth_register_client(auth_metadata, redirect_uri)
    verifier, challenge = _oauth_pkce()
    state = secrets.token_urlsafe(32)
    flow = {
        "name": str(name or "MCP Plugin")[:80], "resource_url": resource_url,
        "resource": str(resource_metadata.get("resource") or resource_url),
        "redirect_uri": redirect_uri, "catalog_id": str(catalog_id), "plugin_id": str(plugin_id),
        "state": state, "code_verifier": verifier, "expires_at": time.time() + 600,
        "authorization_endpoint": auth_metadata["authorization_endpoint"],
        "issuer": str(auth_metadata["issuer"]),
        "token_endpoint": auth_metadata["token_endpoint"],
        "revocation_endpoint": str(auth_metadata.get("revocation_endpoint") or ""),
        **client_data,
    }
    PLUGIN_OAUTH_FLOWS[state] = flow
    parts = urlsplit(flow["authorization_endpoint"])
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update({
        "response_type": "code", "client_id": flow["client_id"],
        "redirect_uri": redirect_uri, "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256",
        "resource": flow["resource"],
    })
    authorization_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    return {"authorization_url": authorization_url, "expires_in": 600}


@app.post("/api/plugin-catalog/{catalog_id}/oauth/start")
async def plugin_catalog_oauth_start(catalog_id: str, request: PluginOAuthStartRequest):
    entry = await _catalog_entry(catalog_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Catalog plugin not found")
    if not entry.get("oauth_connectable"):
        raise HTTPException(status_code=409, detail="This plugin requires manual OAuth client configuration")
    try:
        return await _oauth_start_for_target(
            entry.get("title") or entry.get("name"), entry.get("url"),
            request.redirect_uri, catalog_id=catalog_id,
        )
    except (ValueError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/plugins/{plugin_id}/oauth/start")
async def installed_plugin_oauth_start(plugin_id: str, request: PluginOAuthStartRequest):
    plugin = plugin_registry().get(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    if plugin.get("auth_mode") != "oauth":
        raise HTTPException(status_code=409, detail="Plugin does not use OAuth")
    try:
        return await _oauth_start_for_target(
            plugin.get("name"), plugin.get("url"), request.redirect_uri, plugin_id=plugin_id,
        )
    except (ValueError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/plugin-oauth/callback")
async def plugin_oauth_callback(
    state: str = "", code: str = "", iss: str = "",
    error: str = "", error_description: str = "",
):
    flow = PLUGIN_OAUTH_FLOWS.pop(state, None)
    if not flow:
        return _oauth_popup_response(False, "OAuth state is missing, expired, or already used")
    if flow.get("expires_at", 0) <= time.time():
        return _oauth_popup_response(False, "OAuth authorization expired")
    if iss and iss.rstrip("/") != str(flow.get("issuer") or "").rstrip("/"):
        return _oauth_popup_response(False, "OAuth authorization-server issuer mismatch")
    if error:
        return _oauth_popup_response(False, error_description or error)
    if not code:
        return _oauth_popup_response(False, "OAuth provider returned no authorization code")
    try:
        token = await _oauth_exchange_token(flow, {
            "grant_type": "authorization_code", "code": code,
            "redirect_uri": flow["redirect_uri"], "code_verifier": flow["code_verifier"],
            "resource": flow["resource"],
        })
        access_token = str(token["access_token"])
        tools = await discover_plugin_tools(flow["resource_url"], access_token)
        for tool in tools:
            if tool.get("permission") == "blocked":
                tool["permission"] = "write"
            tool["enabled"] = tool.get("permission") in {"read_only", "write"}

        import hashlib
        plugin_id = hashlib.sha256(flow["resource_url"].encode()).hexdigest()[:16]
        registry = plugin_registry()
        if plugin_id not in registry and len(registry) >= 20:
            raise ValueError("Plugin limit reached (20)")
        registry[plugin_id] = {
            "name": flow["name"], "url": flow["resource_url"], "enabled": True,
            "healthy": True, "last_error": None, "last_checked": time.time(),
            "tools": tools, "auth_mode": "oauth",
            "oauth_provider": str(flow.get("authorization_endpoint") or "").split("/")[2],
            "oauth_connected_at": time.time(),
        }
        _plugin_save(PLUGIN_REGISTRY_PATH, registry)
        secrets_store = plugin_secrets()
        secrets_store[plugin_id] = access_token
        _plugin_save(PLUGIN_SECRETS_PATH, secrets_store)
        oauth_records = plugin_oauth_records()
        expires_in = max(0, int(token.get("expires_in") or 0))
        oauth_records[plugin_id] = {
            "resource": flow["resource"], "token_endpoint": flow["token_endpoint"],
            "revocation_endpoint": flow.get("revocation_endpoint") or "",
            "client_id": flow["client_id"], "client_secret": flow.get("client_secret") or "",
            "token_endpoint_auth_method": flow.get("token_endpoint_auth_method") or "none",
            "refresh_token": str(token.get("refresh_token") or ""),
            "scope": str(token.get("scope") or ""),
            "expires_at": time.time() + expires_in if expires_in else 0,
        }
        _plugin_save(PLUGIN_OAUTH_PATH, oauth_records)
        return _oauth_popup_response(True, "Plugin authorized and connected", plugin_id)
    except (ValueError, httpx.HTTPError) as exc:
        return _oauth_popup_response(False, str(exc))


async def _refresh_plugin_oauth_token(plugin_id, force=False):
    records = plugin_oauth_records()
    record = records.get(plugin_id)
    if not isinstance(record, dict) or not record.get("refresh_token"):
        return False
    expires_at = float(record.get("expires_at") or 0)
    if not force and (not expires_at or expires_at > time.time() + 300):
        return False
    token = await _oauth_exchange_token(record, {
        "grant_type": "refresh_token", "refresh_token": record["refresh_token"],
        "resource": record.get("resource") or "",
    })
    secrets_store = plugin_secrets()
    secrets_store[plugin_id] = str(token["access_token"])
    _plugin_save(PLUGIN_SECRETS_PATH, secrets_store)
    if token.get("refresh_token"):
        record["refresh_token"] = str(token["refresh_token"])
    expires_in = max(0, int(token.get("expires_in") or 0))
    record["expires_at"] = time.time() + expires_in if expires_in else 0
    record["scope"] = str(token.get("scope") or record.get("scope") or "")
    records[plugin_id] = record
    _plugin_save(PLUGIN_OAUTH_PATH, records)
    return True


async def refresh_plugin_oauth_tokens():
    for plugin_id in list(plugin_oauth_records()):
        with contextlib.suppress(ValueError, httpx.HTTPError, OSError):
            await _refresh_plugin_oauth_token(plugin_id)


async def _plugin_oauth_refresh_loop():
    while True:
        await asyncio.sleep(60)
        await refresh_plugin_oauth_tokens()


@app.post("/api/plugins/{plugin_id}/oauth/disconnect")
async def disconnect_plugin_oauth(plugin_id: str):
    registry = plugin_registry()
    plugin = registry.get(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    record = plugin_oauth_records().get(plugin_id) or {}
    access_token = str(plugin_secrets().get(plugin_id) or "")
    revocation_endpoint = str(record.get("revocation_endpoint") or "")
    if revocation_endpoint and access_token:
        with contextlib.suppress(ValueError, httpx.HTTPError):
            endpoint = _oauth_validate_https_url(revocation_endpoint, "OAuth revocation endpoint")
            data = {"token": access_token, "token_type_hint": "access_token"}
            auth = _oauth_token_request_auth(data, record)
            async with httpx.AsyncClient(timeout=PLUGIN_TIMEOUT, follow_redirects=False) as client:
                await client.post(endpoint, data=data, auth=auth)
    secrets_store = plugin_secrets()
    secrets_store.pop(plugin_id, None)
    _plugin_save(PLUGIN_SECRETS_PATH, secrets_store)
    records = plugin_oauth_records()
    records.pop(plugin_id, None)
    _plugin_save(PLUGIN_OAUTH_PATH, records)
    plugin.update({
        "enabled": False, "healthy": False, "last_error": "OAuth disconnected",
        "last_checked": time.time(), "auth_mode": "oauth",
    })
    registry[plugin_id] = plugin
    _plugin_save(PLUGIN_REGISTRY_PATH, registry)
    return {"disconnected": True, "plugin": plugin_public(plugin_id, plugin)}


'''
    text = text.replace(oauth_marker, backend + oauth_marker, 1)

    remove_line = '    registry.pop(plugin_id);_plugin_save(PLUGIN_REGISTRY_PATH,registry);secrets=plugin_secrets();secrets.pop(plugin_id,None);_plugin_save(PLUGIN_SECRETS_PATH,secrets);return {"removed":True}'
    require(text, remove_line, "plugin removal cleanup")
    text = text.replace(
        remove_line,
        '''    registry.pop(plugin_id);_plugin_save(PLUGIN_REGISTRY_PATH,registry)
    secrets=plugin_secrets();secrets.pop(plugin_id,None);_plugin_save(PLUGIN_SECRETS_PATH,secrets)
    oauth_records=plugin_oauth_records();oauth_records.pop(plugin_id,None);_plugin_save(PLUGIN_OAUTH_PATH,oauth_records)
    return {"removed":True}''',
        1,
    )

    startup = '''@app.on_event("startup")
async def start_ha_websocket() -> None:
    load_chat_sessions()
    prune_expired_chats()
'''
    require(text, startup, "startup token refresh")
    text = text.replace(
        startup,
        '''@app.on_event("startup")
async def start_ha_websocket() -> None:
    global PLUGIN_OAUTH_REFRESH_TASK
    load_chat_sessions()
    prune_expired_chats()
    await refresh_plugin_oauth_tokens()
    if PLUGIN_OAUTH_REFRESH_TASK is None or PLUGIN_OAUTH_REFRESH_TASK.done():
        PLUGIN_OAUTH_REFRESH_TASK = asyncio.create_task(
            _plugin_oauth_refresh_loop(), name="zbrano-plugin-oauth-refresh"
        )
''',
        1,
    )

    shutdown = '''@app.on_event("shutdown")
async def stop_ha_websocket() -> None:
    await ha_ws.close()
    await close_mcp_client()
'''
    require(text, shutdown, "shutdown token refresh")
    text = text.replace(
        shutdown,
        '''@app.on_event("shutdown")
async def stop_ha_websocket() -> None:
    global PLUGIN_OAUTH_REFRESH_TASK
    if PLUGIN_OAUTH_REFRESH_TASK is not None:
        PLUGIN_OAUTH_REFRESH_TASK.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await PLUGIN_OAUTH_REFRESH_TASK
        PLUGIN_OAUTH_REFRESH_TASK = None
    await ha_ws.close()
    await close_mcp_client()
''',
        1,
    )

    cloudflare_old = '''        "auth_required": True, "auth_mode": "oauth", "installable": False, "publisher": "Cloudflare",
        "setup_label": "OAuth setup required",'''
    cloudflare_new = '''        "auth_required": True, "auth_mode": "oauth", "installable": False, "oauth_connectable": True, "publisher": "Cloudflare",
        "setup_label": "Connect with Cloudflare",'''
    canva_old = '''        "auth_required": True, "auth_mode": "oauth", "installable": False, "publisher": "Canva",
        "setup_label": "OAuth setup required", "availability": "Access may require approval",'''
    canva_new = '''        "auth_required": True, "auth_mode": "oauth", "installable": False, "oauth_connectable": True, "publisher": "Canva",
        "setup_label": "Connect with Canva", "availability": "Access may require approval",'''
    require(text, cloudflare_old, "Cloudflare automatic OAuth")
    require(text, canva_old, "Canva automatic OAuth")
    text = text.replace(cloudflare_old, cloudflare_new, 1).replace(canva_old, canva_new, 1)

    oauth_availability = '''        elif item.get("auth_mode") == "oauth":
            item["oauth_available"] = False'''
    require(text, oauth_availability, "catalog OAuth availability")
    text = text.replace(
        oauth_availability,
        '''        elif item.get("auth_mode") == "oauth":
            item["oauth_available"] = bool(item.get("oauth_connectable"))''',
        1,
    )

    diagnostics_marker = '''        await probe(
            "Plugins API operational",
            "/api/plugins",
            lambda payload: (
                "operational" if isinstance(payload, dict) and isinstance(payload.get("plugins"), list) else "failed",
                f"{len(payload.get('plugins', [])) if isinstance(payload, dict) else 0} installed plugins",
            ),
            "plugins",
        )
'''
    require(text, diagnostics_marker, "OAuth general diagnostics")
    text = text.replace(
        diagnostics_marker,
        diagnostics_marker + '''        oauth_records = plugin_oauth_records()
        oauth_task_ready = PLUGIN_OAUTH_REFRESH_TASK is not None and not PLUGIN_OAUTH_REFRESH_TASK.done()
        add(
            "Plugin OAuth engine operational",
            "operational" if oauth_task_ready else "degraded",
            f"refresh worker={'active' if oauth_task_ready else 'inactive'}; {len(oauth_records)} OAuth connection record(s)",
            "plugins",
            "Restart the add-on if the OAuth refresh worker is inactive.",
        )
''',
        1,
    )

    targeted_plugins = '''    elif feature_key == "plugins":
        await probe("Plugins API operational", list_plugins, lambda p: (isinstance(p.get("plugins"), list), f"{len(p.get('plugins', []))} installed plugins"), "plugins")'''
    require(text, targeted_plugins, "OAuth targeted diagnostics")
    text = text.replace(
        targeted_plugins,
        targeted_plugins + '''
        oauth_task_ready = PLUGIN_OAUTH_REFRESH_TASK is not None and not PLUGIN_OAUTH_REFRESH_TASK.done()
        add("Plugin OAuth engine operational", "operational" if oauth_task_ready else "degraded", f"refresh worker={'active' if oauth_task_ready else 'inactive'}; {len(plugin_oauth_records())} OAuth connection record(s)", "plugins")''',
        1,
    )

    text = text.replace('version="0.12.8"', 'version="0.12.9"')
    text = text.replace('"version": "0.12.8"', '"version": "0.12.9"')
    MAIN.write_text(text, encoding="utf-8")


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    actions = '''  if(item.installed){
    actions=`<button type="button" disabled>${item.installed_enabled?"Installed · enabled":"Installed · disabled"}</button>`;
  }else if(item.installable===false){'''
    require(text, actions, "catalog OAuth connect action")
    text = text.replace(
        actions,
        '''  if(item.installed){
    actions=`<button type="button" disabled>${item.installed_enabled?"Installed · enabled":"Installed · disabled"}</button>`;
  }else if(item.auth_mode==="oauth"&&item.oauth_available){
    actions=`<button type="button" data-oauth-connect="${catalogEsc(item.id)}">${catalogEsc(item.setup_label||"Connect")}</button>`;
  }else if(item.installable===false){''',
        1,
    )

    tools_line = '      const tools=(p.tools||[]).map(t=>`<label class="plugin-tool">'
    tools_pos = text.find(tools_line)
    if tools_pos < 0:
        raise RuntimeError("ZBRANO v0.12.9 patch missing: installed plugin tools")
    row_line = '      row.innerHTML=`<div class="plugin-head">'
    row_pos = text.find(row_line, tools_pos)
    if row_pos < 0:
        raise RuntimeError("ZBRANO v0.12.9 patch missing: installed plugin actions")
    text = text[:row_pos] + '''      const oauthActions=p.auth_mode==="oauth"
        ?`<button data-a="oauth" data-id="${esc(p.id)}">${p.oauth_connected?"Reauthorize":"Connect"}</button>${p.oauth_connected?`<button data-a="oauth-disconnect" data-id="${esc(p.id)}">Sign out</button>`:""}`
        :"";
''' + text[row_pos:]
    plugin_actions = '<div class="plugin-actions"><button data-a="toggle"'
    require(text, plugin_actions, "installed plugin action buttons")
    text = text.replace(
        plugin_actions,
        '<div class="plugin-actions">${oauthActions}<button data-a="toggle"',
        1,
    )

    runtime = r'''
<script id="zbrano-v0129-plugin-oauth">
(() => {
  const statusNode=()=>document.getElementById("catalog-status")||document.getElementById("plugin-state");
  const callbackUrl=()=>new URL("api/plugin-oauth/callback",window.location.href).href;

  async function startPluginOAuth(endpoint){
    const popup=window.open("about:blank","zbrano-plugin-oauth","popup,width=680,height=760");
    if(!popup){throw new Error("Allow pop-ups for ZBRANO, then press Connect again")}
    const status=statusNode();
    try{
      if(status)status.textContent="Preparing secure authorization…";
      const result=await pApi(endpoint,{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({redirect_uri:callbackUrl()})
      });
      popup.location.replace(result.authorization_url);
      if(status)status.textContent="Complete authorization in the provider window.";
    }catch(error){
      popup.close();
      throw error;
    }
  }

  document.addEventListener("click",async event=>{
    const catalogButton=event.target.closest?.("button[data-oauth-connect]");
    const installedButton=event.target.closest?.('button[data-a="oauth"]');
    const disconnectButton=event.target.closest?.('button[data-a="oauth-disconnect"]');
    if(!catalogButton&&!installedButton&&!disconnectButton)return;
    event.preventDefault();event.stopImmediatePropagation();
    const button=catalogButton||installedButton||disconnectButton;
    button.disabled=true;
    try{
      if(disconnectButton){
        if(!window.confirm("Sign out and remove this plugin's stored OAuth tokens?"))return;
        await pApi(`api/plugins/${encodeURIComponent(disconnectButton.dataset.id)}/oauth/disconnect`,{method:"POST"});
        const status=statusNode();if(status)status.textContent="OAuth disconnected.";
        await Promise.all([loadPlugins(),loadCatalog(false)]);
      }else if(catalogButton){
        await startPluginOAuth(`api/plugin-catalog/${encodeURIComponent(catalogButton.dataset.oauthConnect)}/oauth/start`);
      }else{
        await startPluginOAuth(`api/plugins/${encodeURIComponent(installedButton.dataset.id)}/oauth/start`);
      }
    }catch(error){
      const status=statusNode();if(status)status.textContent=`OAuth failed: ${error.message||error}`;
    }finally{button.disabled=false}
  },true);

  window.addEventListener("message",async event=>{
    if(event.origin!==window.location.origin||event.data?.type!=="zbrano-plugin-oauth")return;
    const status=statusNode();
    if(status)status.textContent=event.data.success
      ?"Authorized and connected. Tools are enabled with write actions approval-gated."
      :`Authorization failed: ${event.data.message||"Unknown error"}`;
    await Promise.all([loadPlugins(),loadCatalog(false)]);
  });
})();
</script>
'''
    body_close = text.rfind("</body>")
    if body_close < 0:
        raise RuntimeError("ZBRANO v0.12.9 patch missing: body close")
    text = text[:body_close] + runtime + text[body_close:]
    text = text.replace("HUD 0.12.8", "HUD 0.12.9")
    INDEX.write_text(text, encoding="utf-8")


def verify() -> None:
    main = MAIN.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    required_main = (
        'version="0.12.9"', "class PluginOAuthStartRequest", "async def _oauth_discover(",
        "resource_metadata=", "def _oauth_pkce(", '"code_challenge_method": "S256"',
        '"/api/plugin-oauth/callback"', "async def _refresh_plugin_oauth_token(",
        '"/api/plugins/{plugin_id}/oauth/disconnect"', '"oauth_connectable": True',
        'item["oauth_available"] = bool(item.get("oauth_connectable"))',
        '"Plugin OAuth engine operational"',
    )
    required_index = (
        "data-oauth-connect", "startPluginOAuth", "zbrano-plugin-oauth",
        "Preparing secure authorization", "Reauthorize", "Sign out", "HUD 0.12.9",
    )
    missing = [marker for marker in required_main if marker not in main]
    missing += [marker for marker in required_index if marker not in index]
    if missing:
        raise RuntimeError("ZBRANO v0.12.9 verification failed: " + ", ".join(missing))


if __name__ == "__main__":
    patch_main()
    patch_index()
    verify()
