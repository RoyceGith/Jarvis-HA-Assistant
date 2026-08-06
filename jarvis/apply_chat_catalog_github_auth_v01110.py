from pathlib import Path

ROOT = Path("/opt/jarvis")
INDEX = ROOT / "app/static/index.html"
MAIN = ROOT / "app/main.py"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"Jarvis v0.11.10 patch missing: {label}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    require(text, old, label)
    return text.replace(old, new, 1)


def patch_index() -> None:
    text = INDEX.read_text(encoding="utf-8")

    runtime_start = text.find(
        '(() => {\n  const byId = id => document.getElementById(id);\n'
        '  let catalogSearchTimer = null;'
    )
    if runtime_start >= 0:
        runtime_end = text.find("\n})();", runtime_start)
        if runtime_end < 0:
            raise RuntimeError("Jarvis v0.11.10 patch missing: v0.11.9 runtime end")
        text = text[:runtime_start] + text[runtime_end + len("\n})();"):]

    synthetic = '''    if (!chats.some(chat => chat.session_id === jarvisChatSessionId)) {
      chats.unshift({session_id: jarvisChatSessionId, title: "New chat", updated_at: Date.now() / 1000});
    }
'''
    require(text, synthetic, "synthetic chat-list entry")
    text = text.replace(synthetic, "", 1)

    old_new_chat = '''async function createNewChat() {
  if (activeRequest) return;
  const sessionId = createSessionId();
  await fetch("api/chats", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({session_id: sessionId}),
  });
  showPanel("chat");
  await openChat(sessionId);
}'''
    new_new_chat = '''async function createNewChat() {
  if (activeRequest) return;
  jarvisChatSessionId = createSessionId();
  updateSessionDisplay();
  showPanel("chat");
  showChatWelcome();
  input.value = "";
  input.dispatchEvent(new Event("input", {bubbles: true}));
  input.focus();
  await refreshChatList();
}'''
    text = replace_once(text, old_new_chat, new_new_chat, "single draft chat lifecycle")

    old_delete = '''async function deleteChat(sessionId) {
  if (activeRequest && sessionId === jarvisChatSessionId) return;
  await fetch(`api/chat/history/${encodeURIComponent(sessionId)}`, {method: "DELETE"});
  if (sessionId === jarvisChatSessionId) {
    await createNewChat();
  } else {
    await refreshChatList();
  }
}'''
    new_delete = '''async function deleteChat(sessionId) {
  if (activeRequest && sessionId === jarvisChatSessionId) return;
  const response = await fetch(
    `api/chat/history/${encodeURIComponent(sessionId)}`,
    {method: "DELETE"}
  );
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);

  if (sessionId !== jarvisChatSessionId) {
    await refreshChatList();
    return;
  }

  const listResponse = await fetch("api/chats");
  const listData = await listResponse.json().catch(() => ({}));
  const remaining = Array.isArray(listData.chats) ? listData.chats : [];
  const next = remaining.find(chat => chat.session_id !== sessionId);
  if (next) await openChat(next.session_id);
  else await createNewChat();
}'''
    text = replace_once(text, old_delete, new_delete, "targeted chat deletion")

    old_delete_listener = '''      deleteButton.addEventListener("click", () => deleteChat(chat.session_id));'''
    new_delete_listener = '''      deleteButton.addEventListener("click", async event => {
        event.preventDefault();
        event.stopPropagation();
        try {
          await deleteChat(chat.session_id);
        } catch (error) {
          deleteButton.title = `Delete failed: ${error.message || error}`;
        }
      });'''
    text = replace_once(
        text,
        old_delete_listener,
        new_delete_listener,
        "isolated delete button",
    )

    old_status = '''    catalogStatus.textContent=`${items.length} plugin${items.length===1?"":"s"} found${data.cached?" · cached":""}.`;'''
    new_status = '''    const registryNote=data.registry_error?` · Registry warning: ${data.registry_error}`:"";
    catalogStatus.textContent=`${items.length} plugin${items.length===1?"":"s"} found${data.cached?" · cached":""}${registryNote}.`;'''
    if old_status in text:
        text = text.replace(old_status, new_status, 1)

    runtime = r'''
(() => {
  let catalogSearchTimer = null;
  const catalogStatusNode = () => document.getElementById("catalog-status");

  document.addEventListener("input", event => {
    if (event.target?.id !== "catalog-search") return;
    clearTimeout(catalogSearchTimer);
    catalogSearchTimer = window.setTimeout(() => {
      if (typeof loadCatalog === "function") loadCatalog(false);
    }, 250);
  }, true);

  async function authorizeAndInstallGitHub(button) {
    const status = catalogStatusNode();
    button.disabled = true;
    let authWindow = null;
    try {
      authWindow = window.open("about:blank", "_blank");
      const start = await pApi(
        `api/plugin-catalog/${encodeURIComponent(button.dataset.catalogInstall)}/github-device/start`,
        {method: "POST"}
      );
      if (authWindow) authWindow.location = start.verification_uri;
      if (status) {
        status.innerHTML =
          `GitHub authorization code: <strong>${catalogEsc(start.user_code)}</strong> · ` +
          `<a href="${catalogEsc(start.verification_uri)}" target="_blank" rel="noopener">Open GitHub authorization</a>`;
      }

      const deadline = Date.now() + Number(start.expires_in || 900) * 1000;
      let interval = Math.max(5, Number(start.interval || 5));
      while (Date.now() < deadline) {
        await new Promise(resolve => setTimeout(resolve, interval * 1000));
        const result = await pApi(
          `api/plugin-catalog/github-device/${encodeURIComponent(start.flow_id)}/complete`,
          {method: "POST"}
        );
        if (result.pending) {
          interval = Math.max(interval, Number(result.interval || interval));
          continue;
        }
        if (result.installed) {
          if (status) status.textContent =
            "GitHub authorized and installed disabled. Review tools, then enable it.";
          if (typeof loadPlugins === "function") await loadPlugins();
          return;
        }
      }
      throw new Error("GitHub authorization expired");
    } catch (error) {
      if (authWindow && authWindow.location.href === "about:blank") authWindow.close();
      if (status) status.textContent = `GitHub authorization failed: ${error.message || error}`;
    } finally {
      button.disabled = false;
    }
  }

  document.addEventListener("click", event => {
    const button = event.target.closest?.("button[data-catalog-install]");
    if (!button) return;
    const card = button.closest(".catalog-card");
    const isGitHub = /github/i.test(card?.textContent || "");
    if (!isGitHub) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    authorizeAndInstallGitHub(button);
  }, true);
})();
'''
    last_script = text.rfind("</script>")
    if last_script < 0:
        raise RuntimeError("Jarvis v0.11.10 patch missing: final script close")
    text = text[:last_script] + runtime + "\n" + text[last_script:]

    text = text.replace("HUD 0.11.9", "HUD 0.11.10")
    INDEX.write_text(text, encoding="utf-8")


def patch_main() -> None:
    text = MAIN.read_text(encoding="utf-8")

    text = text.replace(
        'MCP_REGISTRY_API = "https://registry.modelcontextprotocol.io/v0/servers"',
        'MCP_REGISTRY_API = "https://registry.modelcontextprotocol.io/v0.1/servers"',
        1,
    )

    start = text.find("def _catalog_remote_entry(server):")
    end = text.find("\n\nasync def _fetch_plugin_catalog", start)
    if start < 0 or end < 0:
        raise RuntimeError("Jarvis v0.11.10 patch missing: catalog parser bounds")
    parser = r'''def _catalog_remote_entry(server):
    if not isinstance(server, dict):
        return None

    wrapper = server
    if isinstance(server.get("server"), dict):
        server = server["server"]

    name = str(server.get("name") or "").strip()
    description = str(server.get("description") or "").strip()
    version = str(server.get("version") or "").strip()
    title = str(server.get("title") or name).strip()

    remotes = server.get("remotes") or []
    if isinstance(remotes, dict):
        remotes = [remotes]

    url = ""
    auth_required = False
    for remote in remotes:
        if not isinstance(remote, dict):
            continue
        candidate = str(
            remote.get("url")
            or remote.get("endpoint")
            or remote.get("uri")
            or ""
        ).strip()
        if not candidate.startswith("https://"):
            continue
        url = candidate
        headers = remote.get("headers") or []
        auth_required = bool(
            remote.get("authentication")
            or remote.get("auth")
            or headers
        )
        break

    if not name or not url:
        return None

    try:
        validate_plugin_url(url)
    except ValueError:
        return None

    lower = f"{name} {title} {description}".lower()
    if any(word in lower for word in ("github", "gitlab", "code", "developer", "repository")):
        category = "developer-tools"
    elif any(word in lower for word in ("calendar", "mail", "task", "docs", "productivity")):
        category = "productivity"
    elif any(word in lower for word in ("database", "data", "analytics", "search", "redis", "sql")):
        category = "data"
    else:
        category = "other"

    meta = wrapper.get("_meta") or wrapper.get("meta") or {}
    return {
        "id": hashlib.sha256(f"{name}|{version}|{url}".encode()).hexdigest()[:20],
        "name": name,
        "title": title[:120],
        "description": description[:1000],
        "version": version[:80],
        "url": url,
        "category": category,
        "verified": bool(
            server.get("verified")
            or server.get("official")
            or meta.get("official")
        ),
        "auth_required": auth_required,
        "publisher": str(server.get("publisher") or "")[:120],
    }'''
    text = text[:start] + parser + text[end:]

    start = text.find("async def _fetch_plugin_catalog(")
    end = text.find('\n\n\ndef _verify_catalog_result_contract', start)
    if end < 0:
        end = text.find('\n\n@app.get("/api/plugin-catalog")', start)
    if start < 0 or end < 0:
        raise RuntimeError("Jarvis v0.11.10 patch missing: catalog fetch bounds")
    fetcher = r'''async def _fetch_plugin_catalog(force=False):
    if not force:
        cached = _catalog_cache_read()
        if cached is not None:
            return cached, True, None

    plugins = list(FEATURED_REMOTE_PLUGINS)
    registry_error = None
    try:
        cursor = None
        pages = 0
        async with httpx.AsyncClient(
            timeout=PLUGIN_TIMEOUT,
            follow_redirects=False,
        ) as client:
            while pages < 5:
                params = {"limit": 100}
                if cursor:
                    params["cursor"] = cursor
                response = await client.get(MCP_REGISTRY_API, params=params)
                if response.is_redirect:
                    raise ValueError("Registry redirects are blocked")
                response.raise_for_status()
                payload = response.json()
                servers = payload.get("servers") or payload.get("items") or []
                for server in servers:
                    entry = _catalog_remote_entry(server)
                    if entry and not any(item["url"] == entry["url"] for item in plugins):
                        plugins.append(entry)
                metadata = payload.get("metadata") or payload.get("_meta") or {}
                cursor = metadata.get("nextCursor") or metadata.get("next_cursor")
                pages += 1
                if not cursor:
                    break
    except Exception as exc:
        registry_error = str(exc)
        cached = _catalog_cache_read()
        if cached is not None:
            return cached, True, registry_error

    _plugin_save(
        PLUGIN_CATALOG_CACHE_PATH,
        {"saved_at": time.time(), "plugins": plugins},
    )
    return plugins, False, registry_error'''
    text = text[:start] + fetcher + text[end:]

    marker = '@app.get("/api/plugins")'
    require(text, marker, "plugin API marker")
    device_backend = r'''
GITHUB_DEVICE_FLOWS = {}


def _github_oauth_client_id():
    try:
        options = json.loads(Path("/data/options.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return str(options.get("github_oauth_client_id") or "").strip()


async def _catalog_entry(catalog_id):
    plugins, _, _ = _verify_catalog_result_contract(
        await _fetch_plugin_catalog(force=False)
    )
    return next((item for item in plugins if item.get("id") == catalog_id), None)


@app.post("/api/plugin-catalog/{catalog_id}/github-device/start")
async def github_device_start(catalog_id: str):
    import secrets

    entry = await _catalog_entry(catalog_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Catalog plugin not found")
    if "github" not in (
        f"{entry.get('name', '')} {entry.get('title', '')} {entry.get('url', '')}"
    ).lower():
        raise HTTPException(
            status_code=400,
            detail="GitHub authorization is only available for GitHub plugins",
        )

    client_id = _github_oauth_client_id()
    if not client_id:
        raise HTTPException(
            status_code=503,
            detail=(
                "Set github_oauth_client_id in the add-on configuration. "
                "The GitHub App or OAuth App must have Device Flow enabled."
            ),
        )

    async with httpx.AsyncClient(timeout=PLUGIN_TIMEOUT) as client:
        response = await client.post(
            "https://github.com/login/device/code",
            headers={"Accept": "application/json"},
            data={"client_id": client_id, "scope": "repo read:org"},
        )
        response.raise_for_status()
        payload = response.json()

    if payload.get("error"):
        raise HTTPException(
            status_code=400,
            detail=payload.get("error_description") or payload["error"],
        )

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
        "verification_uri": payload.get("verification_uri")
        or "https://github.com/login/device",
        "expires_in": int(payload.get("expires_in") or 900),
        "interval": interval,
    }


@app.post("/api/plugin-catalog/github-device/{flow_id}/complete")
async def github_device_complete(flow_id: str):
    flow = GITHUB_DEVICE_FLOWS.get(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="GitHub authorization flow not found")

    now = time.time()
    if now >= flow["expires_at"]:
        GITHUB_DEVICE_FLOWS.pop(flow_id, None)
        raise HTTPException(status_code=410, detail="GitHub authorization expired")
    if now < flow["next_poll"]:
        return {
            "pending": True,
            "interval": max(1, int(flow["next_poll"] - now)),
        }

    client_id = _github_oauth_client_id()
    async with httpx.AsyncClient(timeout=PLUGIN_TIMEOUT) as client:
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
        raise HTTPException(
            status_code=400,
            detail=payload.get("error_description") or error,
        )

    access_token = str(payload.get("access_token") or "")
    if not access_token:
        raise HTTPException(status_code=502, detail="GitHub returned no access token")

    entry = await _catalog_entry(flow["catalog_id"])
    if not entry:
        raise HTTPException(status_code=404, detail="Catalog plugin not found")

    result = await install_plugin(
        PluginInstallRequest(
            name=str(entry.get("title") or entry.get("name") or "GitHub"),
            url=str(entry.get("url") or ""),
            bearer_token=access_token,
        )
    )
    GITHUB_DEVICE_FLOWS.pop(flow_id, None)
    return {"pending": False, **result}


'''
    text = text.replace(marker, device_backend + marker, 1)

    text = text.replace('version="0.11.9"', 'version="0.11.10"')
    text = text.replace('"version": "0.11.9"', '"version": "0.11.10"')
    MAIN.write_text(text, encoding="utf-8")


def verify() -> None:
    index = INDEX.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")

    required_index = (
        "async function createNewChat()",
        "await refreshChatList();",
        "authorizeAndInstallGitHub",
        "github-device/start",
        "GitHub authorization code:",
    )
    required_main = (
        "/v0.1/servers",
        'metadata.get("nextCursor")',
        "GITHUB_DEVICE_FLOWS",
        "github_oauth_client_id",
        "/github-device/{flow_id}/complete",
        "0.11.10",
    )
    missing = [item for item in required_index if item not in index]
    missing += [item for item in required_main if item not in main]

    if "chats.unshift({session_id: jarvisChatSessionId" in index:
        missing.append("synthetic New chat entry still present")
    section = index[index.find("async function createNewChat()"):index.find("async function deleteChat(")]
    if 'await fetch("api/chats", {' in section:
        missing.append("New Chat still persists an empty backend chat")
    if "const newChat = event.target.closest" in index:
        missing.append("duplicate v0.11.9 New Chat handler still present")

    if missing:
        raise RuntimeError(
            "Jarvis v0.11.10 verification failed: " + ", ".join(missing)
        )


if __name__ == "__main__":
    patch_index()
    patch_main()
    verify()
