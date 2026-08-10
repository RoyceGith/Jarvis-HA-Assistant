import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.54 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.54 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        "async def _oauth_discover(resource_url):",
        "async def _oauth_discover(resource_url, allow_pre_registered=False):",
        "OAuth discovery mode",
    )
    backend = replace_once(
        backend,
        '''    registration_endpoint = auth_metadata.get("registration_endpoint")
    if not registration_endpoint:
        raise ValueError("This provider requires a pre-registered OAuth client")
    auth_metadata["registration_endpoint"] = _oauth_validate_https_url(
        registration_endpoint, "OAuth registration endpoint"
    )''',
        '''    registration_endpoint = auth_metadata.get("registration_endpoint")
    if registration_endpoint:
        auth_metadata["registration_endpoint"] = _oauth_validate_https_url(
            registration_endpoint, "OAuth registration endpoint"
        )
    elif not allow_pre_registered:
        raise ValueError("This provider requires a pre-registered OAuth client")''',
        "optional dynamic client registration",
    )

    backend = replace_once(
        backend,
        '''    resource_url, resource_metadata, auth_metadata = await _oauth_discover(resource_url)
    client_data = await _oauth_register_client(auth_metadata, redirect_uri)
    verifier, challenge = _oauth_pkce()''',
        '''    google_connector = str(catalog_id) == "gmail-official"
    resource_url, resource_metadata, auth_metadata = await _oauth_discover(
        resource_url, allow_pre_registered=google_connector
    )
    if google_connector:
        google_client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
        google_client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
        if not google_client_id or not google_client_secret:
            raise ValueError("Configure Google OAuth client ID and secret in the ZBRANO add-on settings first")
        client_data = {
            "client_id": google_client_id,
            "client_secret": google_client_secret,
            "token_endpoint_auth_method": "client_secret_post",
        }
    else:
        client_data = await _oauth_register_client(auth_metadata, redirect_uri)
    verifier, challenge = _oauth_pkce()''',
        "Google pre-registered client selection",
    )

    backend = replace_once(
        backend,
        '''        "authorization_endpoint": auth_metadata["authorization_endpoint"],
        "issuer": str(auth_metadata["issuer"]),''',
        '''        "authorization_endpoint": auth_metadata["authorization_endpoint"],
        "issuer": str(auth_metadata["issuer"]),
        "google_connector": google_connector,
        "scope": " ".join(
            str(scope).strip() for scope in (
                resource_metadata.get("scopes_supported")
                or auth_metadata.get("scopes_supported") or []
            ) if str(scope).strip()
        )[:2000],''',
        "OAuth scope preservation",
    )
    backend = replace_once(
        backend,
        '''    query.update({
        "response_type": "code", "client_id": flow["client_id"],
        "redirect_uri": redirect_uri, "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256",
        "resource": flow["resource"],
    })
    authorization_url = urlunsplit''',
        '''    query.update({
        "response_type": "code", "client_id": flow["client_id"],
        "redirect_uri": redirect_uri, "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256",
        "resource": flow["resource"],
    })
    if flow.get("scope"):
        query["scope"] = flow["scope"]
    if flow.get("google_connector"):
        query.update({"access_type": "offline", "prompt": "consent", "include_granted_scopes": "true"})
    authorization_url = urlunsplit''',
        "Google offline authorization parameters",
    )

    backend = replace_once(
        backend,
        '''        elif item.get("auth_mode") == "oauth":
            item["oauth_available"] = bool(item.get("oauth_connectable"))''',
        '''        elif item.get("id") == "gmail-official":
            google_ready = bool(
                os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
                and os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
            )
            item["oauth_available"] = google_ready
            item["oauth_connectable"] = True
            item["setup_label"] = "Connect with Google" if google_ready else "Google OAuth setup required"
        elif item.get("auth_mode") == "oauth":
            item["oauth_available"] = bool(item.get("oauth_connectable"))''',
        "Gmail catalog readiness",
    )
    backend = replace_once(
        backend,
        '''        "auth_required": True, "auth_mode": "oauth", "installable": False, "publisher": "Google",
        "setup_label": "OAuth setup required", "availability": "Developer Preview",
        "icon_url": "plugin-icons/gmail.svg",''',
        '''        "auth_required": True, "auth_mode": "oauth", "installable": False, "oauth_connectable": True, "publisher": "Google",
        "setup_label": "Connect with Google", "availability": "Developer Preview",
        "icon_url": "plugin-icons/gmail.svg",''',
        "Gmail curated catalog connector",
    )

    backend = replace_once(
        backend,
        '''        add(
            "Plugin OAuth engine operational",
            "operational" if oauth_task_ready else "degraded",''',
        '''        google_oauth_ready = bool(
            os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
            and os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
        )
        add(
            "Gmail OAuth configuration",
            "operational" if google_oauth_ready else "setup_required",
            "Google OAuth client configured" if google_oauth_ready else "Add the Google OAuth client ID and secret in add-on settings",
            "plugins",
            "Create a Google Web OAuth client and register ZBRANO's exact callback URL.",
        )
        add(
            "Plugin OAuth engine operational",
            "operational" if oauth_task_ready else "degraded",''',
        "Gmail OAuth diagnostics",
    )

    frontend = replace_once(
        frontend,
        '''  }else if(item.installable===false){
    const guide=item.docs_url?`<a href="${catalogEsc(item.docs_url)}" target="_blank" rel="noopener noreferrer">Setup guide</a>`:"";
    actions=`<button type="button" disabled>${catalogEsc(item.setup_label||"Setup required")}</button>${guide}`;''',
        '''  }else if(item.id==="gmail-official"&&item.oauth_available===false){
    const guide=item.docs_url?`<a href="${catalogEsc(item.docs_url)}" target="_blank" rel="noopener noreferrer">Setup guide</a>`:"";
    actions=`<button type="button" data-copy-google-callback>Copy callback URL</button>${guide}`;
  }else if(item.installable===false){
    const guide=item.docs_url?`<a href="${catalogEsc(item.docs_url)}" target="_blank" rel="noopener noreferrer">Setup guide</a>`:"";
    actions=`<button type="button" disabled>${catalogEsc(item.setup_label||"Setup required")}</button>${guide}`;''',
        "Gmail callback helper action",
    )

    runtime = r'''
<script id="zbrano-v01254-gmail-oauth">
(() => {
  document.addEventListener("click", async event => {
    const button = event.target.closest?.("button[data-copy-google-callback]");
    if (!button) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const callback = new URL("api/plugin-oauth/callback", window.location.href).href;
    const status = document.getElementById("catalog-status") || document.getElementById("plugin-state");
    try {
      await navigator.clipboard.writeText(callback);
      if (status) status.textContent = "OAuth callback copied. Add it as an authorized redirect URI in Google Cloud.";
    } catch (_) {
      if (status) status.textContent = `Google OAuth callback: ${callback}`;
    }
  }, true);
})();
</script>
'''
    body_close = frontend.rfind("</body>")
    if body_close < 0:
        raise RuntimeError("ZBRANO v0.12.54 could not locate body close")
    frontend = frontend[:body_close] + runtime + frontend[body_close:]

    runtime_tools = '''def runtime_chat_tools(search_mode: str = "auto") -> list[dict[str, Any]]:
    if developer_mode_enabled():
        return developer_runtime_tools() + developer_mcp_tools()
    tools = WORKSHOP_TOOLS + workshop_memory_function_tools() + active_mcp_tools()
    search_tool = native_web_search_tool(search_mode)
    return tools + ([search_tool] if search_tool else [])
'''
    prioritized_runtime_tools = r'''HOME_ASSISTANT_PRIORITY_TOOL_NAMES = {
    "find_home_assistant_entities",
    "get_home_assistant_state",
    "turn_on_home_assistant_entity",
    "turn_off_home_assistant_entity",
}


def is_home_assistant_priority_intent(message: str) -> bool:
    import re

    normalized = " ".join(str(message or "").lower().split())
    if not normalized:
        return False
    non_device_context = (
        "developer mode", "repository", "github", "git branch", "commit", "push", "pull request",
        "source code", "plugin", "web search", "search mode", "speak replies", "voice playback",
        "notification", "setting", "diagnostic",
    )
    if any(term in normalized for term in non_device_context):
        return False
    return bool(
        re.search(r"\b(?:turn|switch)\s+(?:on|off)\b", normalized)
        or re.search(r"\b(?:power|shut)\s+(?:on|off|down)\b", normalized)
        or re.search(r"\btoggle\b", normalized)
    )


def home_assistant_priority_tools() -> list[dict[str, Any]]:
    return [
        tool for tool in WORKSHOP_TOOLS
        if str(tool.get("name") or "") in HOME_ASSISTANT_PRIORITY_TOOL_NAMES
    ]


def priority_system_instructions(base: str, message: str) -> str:
    if not is_home_assistant_priority_intent(message):
        return developer_system_instructions(base)
    return base + """

HOME ASSISTANT DEVICE CONTROL INTENT IS ACTIVE.
Resolve the requested device only with the provided Home Assistant entity tools. Do not inspect repositories,
plugins, Workshop Memory, or the web. If the entity name is ambiguous, search approved Home Assistant entities
and ask one concise clarification rather than selecting an unsafe device. Execute only the requested state change.
""".strip()


def runtime_chat_tools(search_mode: str = "auto", message: str = "") -> list[dict[str, Any]]:
    if is_home_assistant_priority_intent(message):
        return home_assistant_priority_tools()
    if developer_mode_enabled():
        return developer_runtime_tools() + developer_mcp_tools()
    tools = WORKSHOP_TOOLS + workshop_memory_function_tools() + active_mcp_tools()
    search_tool = native_web_search_tool(search_mode)
    return tools + ([search_tool] if search_tool else [])
'''
    backend = replace_once(
        backend,
        runtime_tools,
        prioritized_runtime_tools,
        "Home Assistant priority runtime",
    )

    backend = replace_once(
        backend,
        '''    allowed_function_tools = (
        developer_runtime_tools()
        if developer_mode_enabled()
        else WORKSHOP_TOOLS + workshop_memory_function_tools()
    )
    allowed_names = {tool["name"] for tool in allowed_function_tools}''',
        '''    allowed_function_tools = (
        developer_runtime_tools()
        if developer_mode_enabled()
        else WORKSHOP_TOOLS + workshop_memory_function_tools()
    )
    allowed_names = {tool["name"] for tool in allowed_function_tools}
    if developer_mode_enabled():
        allowed_names.update(HOME_ASSISTANT_PRIORITY_TOOL_NAMES)''',
        "Developer-mode HA execution allowlist",
    )

    fast_path_marker = '''    local_result = None if developer_mode_enabled() else await try_local_ha_route(message, session_id)
    if local_result:'''
    fast_path_replacement = '''    local_result = (
        await try_local_ha_route(message, session_id)
        if is_home_assistant_priority_intent(message) or not developer_mode_enabled()
        else None
    )
    if local_result:'''
    if backend.count(fast_path_marker) != 2:
        raise RuntimeError(
            f"ZBRANO v0.12.54 expected two Home Assistant fast paths; found {backend.count(fast_path_marker)}"
        )
    backend = backend.replace(fast_path_marker, fast_path_replacement)

    run_start = backend.find("async def run_jarvis(")
    run_end = backend.find("\n\nasync def _run_jarvis_stream_events(", run_start)
    if run_start < 0 or run_end < 0:
        raise RuntimeError("ZBRANO v0.12.54 could not locate non-streaming chat bounds")
    run_section = backend[run_start:run_end]
    if run_section.count("runtime_chat_tools()") != 4:
        raise RuntimeError("ZBRANO v0.12.54 expected four non-streaming runtime tool payloads")
    run_section = run_section.replace("runtime_chat_tools()", "runtime_chat_tools(message=message)")
    developer_instruction = "developer_system_instructions(effective_system_instructions())"
    if developer_instruction not in run_section:
        raise RuntimeError("ZBRANO v0.12.54 could not locate non-streaming system instructions")
    run_section = run_section.replace(
        developer_instruction,
        "priority_system_instructions(effective_system_instructions(), message)",
    )
    backend = backend[:run_start] + run_section + backend[run_end:]

    stream_start = backend.find("async def _run_jarvis_stream_events(")
    stream_end = backend.find("\n\nasync def run_jarvis_stream(", stream_start)
    if stream_start < 0 or stream_end < 0:
        raise RuntimeError("ZBRANO v0.12.54 could not locate streaming chat bounds")
    stream_section = backend[stream_start:stream_end]
    if stream_section.count("runtime_chat_tools(search_mode)") != 3:
        raise RuntimeError("ZBRANO v0.12.54 expected three streaming runtime tool payloads")
    stream_section = stream_section.replace(
        "runtime_chat_tools(search_mode)",
        "runtime_chat_tools(search_mode, message)",
    )
    if developer_instruction not in stream_section:
        raise RuntimeError("ZBRANO v0.12.54 could not locate streaming system instructions")
    stream_section = stream_section.replace(
        developer_instruction,
        "priority_system_instructions(effective_system_instructions(), message)",
    )
    backend = backend[:stream_start] + stream_section + backend[stream_end:]

    backend = replace_once(
        backend,
        '''        activity_id = f"function-round-{round_index}"
        write_calls = workshop_memory_write_calls(calls)
        activity_meta = local_tool_activity(tool_names_list, writing=bool(write_calls))
        yield stream_event("activity", id=activity_id, state="started", **activity_meta)''',
        '''        write_calls = workshop_memory_write_calls(calls)
        activity_meta = local_tool_activity(tool_names_list, writing=bool(write_calls))
        activity_id = (
            "local-home-assistant"
            if activity_meta.get("provider") == "home_assistant"
            else f"function-round-{round_index}"
        )
        yield stream_event("activity", id=activity_id, state="started", **activity_meta)''',
        "stable Home Assistant activity identity",
    )
    frontend = replace_once(
        frontend,
        '''  const id = String(eventData.id || `${eventData.provider || "tool"}-${eventData.label || "activity"}`);''',
        '''  const id = String(
    eventData.provider === "home_assistant"
      ? "local-home-assistant"
      : eventData.id || `${eventData.provider || "tool"}-${eventData.label || "activity"}`
  );''',
        "frontend Home Assistant activity coalescing",
    )

    backend = replace_once(
        backend,
        '''            "files": _tab_activity_revision(SHARED_FILE_ROOT),''',
        '''            "files": _tab_activity_value_revision([
                {
                    key: item.get(key)
                    for key in ("file_id", "name", "mime_type", "size", "sha256", "created_at")
                }
                for item in sorted(_list(SHARED_FILE_ROOT), key=lambda item: str(item.get("file_id") or ""))
            ]),''',
        "stable Shared Files activity revision",
    )

    frontend = replace_once(
        frontend,
        '''    #automations-panel::before { display: none; }''',
        '''    #automations-panel::before, #files-panel::before { display: none; }''',
        "Shared Files system label removal",
    )
    frontend = replace_once(
        frontend,
        '''      activityRevisions = revisions;
    } catch (_) {}''',
        '''      activityRevisions = revisions;
      for (const binding of bindings) {
        if (isViewed(binding.button, binding.panel)) clear(binding.button);
      }
    } catch (_) {}''',
        "active tab activity acknowledgement",
    )
    frontend = replace_once(
        frontend,
        '''  window.zbranoMarkTabChanged = tabId => markIfUnseen(document.getElementById(tabId));
  window.zbranoClearTabChanged = tabId => clear(document.getElementById(tabId));''',
        '''  window.zbranoMarkTabChanged = tabId => markIfUnseen(document.getElementById(tabId));
  window.zbranoClearTabChanged = tabId => clear(document.getElementById(tabId));
  document.addEventListener("click", event => {
    const button = event.target.closest?.(
      "#chat-tab,#files-tab,#plugins-tab,#entities-tab,#automations-tab,#settings-tab,#developer-tab,[data-auto-view],[data-notification-view],.settings-category-tab[data-settings-target],#plugins-installed-tab,#plugins-browse-tab"
    );
    if (!button) return;
    clear(button);
    requestAnimationFrame(() => clear(button));
  }, true);''',
        "delegated tab activity acknowledgement",
    )

    backend = backend.replace('version="0.12.53"', 'version="0.12.54"')
    backend = backend.replace('"version": "0.12.53"', '"version": "0.12.54"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.53"', '"X-ZBRANO-Frontend-Version": "0.12.54"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.53"', '"name": "ZBRANO Developer Mode", "version": "0.12.54"')
    frontend = frontend.replace("HUD 0.12.53", "HUD 0.12.54")

    for marker in (
        'version="0.12.54"',
        "allow_pre_registered=False",
        'os.getenv("GOOGLE_OAUTH_CLIENT_ID"',
        'os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"',
        '"token_endpoint_auth_method": "client_secret_post"',
        'query.update({"access_type": "offline", "prompt": "consent"',
        'item.get("id") == "gmail-official"',
        '"Gmail OAuth configuration"',
        "def is_home_assistant_priority_intent(message: str)",
        "return home_assistant_priority_tools()",
        "allowed_names.update(HOME_ASSISTANT_PRIORITY_TOOL_NAMES)",
        "priority_system_instructions(effective_system_instructions(), message)",
        '"local-home-assistant"',
        '"files": _tab_activity_value_revision([',
    ):
        require(backend, marker, marker)
    for marker in (
        "HUD 0.12.54",
        "zbrano-v01254-gmail-oauth",
        "data-copy-google-callback",
        "OAuth callback copied",
        'eventData.provider === "home_assistant"',
        '#automations-panel::before, #files-panel::before { display: none; }',
        'if (isViewed(binding.button, binding.panel)) clear(binding.button);',
    ):
        require(frontend, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
