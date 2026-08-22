import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.44 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.44 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    models = r'''class NotificationWatchRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    entity_id: str = Field(min_length=3, max_length=255, pattern=r"^[a-z0-9_]+\.[a-z0-9_]+$")
    trigger_state: str = Field(min_length=1, max_length=255)
    destination: str = Field(default="", max_length=255, pattern=r"^(|notify\.[a-z0-9_]+)$")
    severity: str = Field(default="information", pattern="^(information|suggestion|warning|critical)$")
    title: str = Field(default="ZBRANO notification", max_length=120)
    message: str = Field(min_length=1, max_length=2000)
    active_start: str = Field(default="", pattern=r"^(|([01]\d|2[0-3]):[0-5]\d)$")
    active_end: str = Field(default="", pattern=r"^(|([01]\d|2[0-3]):[0-5]\d)$")
    one_shot: bool = False
    expires_at: float = Field(default=0, ge=0)
    cooldown_minutes: int = Field(default=5, ge=0, le=10080)
    enabled: bool = True


class NotificationWatchStateRequest(BaseModel):
    enabled: bool


'''
    backend = replace_once(
        backend,
        "class SettingsRestoreRequest(BaseModel):\n",
        models + "class SettingsRestoreRequest(BaseModel):\n",
        "notification watch models",
    )

    tool = r'''    {
        "type": "function",
        "name": "create_notification_watch",
        "description": (
            "Create and arm a notification-only automation when the user explicitly asks "
            "to be notified when a Home Assistant entity reaches a state. Use an exact "
            "entity ID, normally found first with find_home_assistant_entities. The explicit "
            "request authorizes creation; future matching events notify automatically."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Short watch name."},
                "entity_id": {"type": "string", "description": "Exact Home Assistant entity ID to watch."},
                "trigger_state": {"type": "string", "description": "Exact state that triggers the notification, such as on, open, or finished."},
                "destination": {"type": "string", "description": "Optional notify entity; blank uses the Notification Center default."},
                "severity": {"type": "string", "enum": ["information", "suggestion", "warning", "critical"]},
                "title": {"type": "string", "description": "Notification title."},
                "message": {"type": "string", "description": "Message to deliver when triggered."},
                "active_start": {"type": "string", "description": "Optional local HH:MM start time."},
                "active_end": {"type": "string", "description": "Optional local HH:MM end time."},
                "one_shot": {"type": "boolean", "description": "Disable after the first successful delivery."},
                "expires_at": {"type": "number", "description": "Optional Unix expiry time; use 0 for no expiry."},
                "cooldown_minutes": {"type": "integer", "description": "Minimum minutes between repeat deliveries."},
                "enabled": {"type": "boolean", "description": "Arm immediately when true."}
            },
            "required": ["name", "entity_id", "trigger_state", "destination", "severity", "title", "message", "active_start", "active_end", "one_shot", "expires_at", "cooldown_minutes", "enabled"],
            "additionalProperties": False
        },
        "strict": True
    },
'''
    backend = replace_once(
        backend,
        "WORKSHOP_TOOLS: list[dict[str, Any]] = [\n",
        "WORKSHOP_TOOLS: list[dict[str, Any]] = [\n" + tool,
        "notification watch chat tool",
    )

    old_channels = r'''async def notification_channels() -> list[dict[str, Any]]:
    payload = await list_ha_entities()
    channels = []
    for entity in payload.get("entities") or []:
        entity_id = str(entity.get("entity_id") or "")
        if not entity_id.startswith("notify."):
            continue
        friendly_name = str(entity.get("friendly_name") or entity_id)
        identity = f"{entity_id} {friendly_name}".lower()
        channels.append({
            "entity_id": entity_id,
            "friendly_name": friendly_name,
            "platform": "telegram" if "telegram" in identity else "home_assistant",
            "available": bool(entity.get("available")),
            "state": entity.get("state"),
            "icon": entity.get("icon"),
        })
    channels.sort(key=lambda item: (item["platform"] != "telegram", item["friendly_name"].lower()))
    return channels
'''
    new_channels = r'''async def notification_channels() -> list[dict[str, Any]]:
    payload = await list_ha_entities()
    registry_platforms: dict[str, str] = {}
    try:
        registry = await ha_ws.command({"type": "config/entity_registry/list"})
        for entry in registry.get("result") or []:
            if isinstance(entry, dict) and entry.get("entity_id"):
                registry_platforms[str(entry["entity_id"])] = str(entry.get("platform") or "").lower()
    except (RuntimeError, OSError, asyncio.TimeoutError):
        pass

    channels = []
    for entity in payload.get("entities") or []:
        entity_id = str(entity.get("entity_id") or "")
        if not entity_id.startswith("notify."):
            continue
        friendly_name = str(entity.get("friendly_name") or entity_id)
        integration = registry_platforms.get(entity_id, "")
        identity = f"{integration} {entity_id} {friendly_name}".lower()
        platform = "telegram" if integration in {"telegram", "telegram_bot"} or "telegram" in identity else "home_assistant"
        channels.append({
            "entity_id": entity_id,
            "friendly_name": friendly_name,
            "platform": platform,
            "integration": integration or "unknown",
            "available": bool(entity.get("available")),
            "state": entity.get("state"),
            "icon": entity.get("icon"),
        })
    channels.sort(key=lambda item: (item["platform"] != "telegram", item["friendly_name"].lower()))
    return channels
'''
    backend = replace_once(backend, old_channels, new_channels, "metadata-backed channel discovery")

    watch_backend = r'''
NOTIFICATION_WATCH_TASK: asyncio.Task[Any] | None = None


def notification_watches(data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    store = data or automation_store()
    return [item for item in store.get("automations", []) if item.get("kind") == "notification_watch"]


def _notification_watch_payload(request: NotificationWatchRequest) -> dict[str, Any]:
    settings = notification_store()["settings"]
    destination = request.destination.strip().lower() or str(settings.get("default_channel") or "")
    if not destination:
        raise HTTPException(status_code=400, detail="Choose a default Notification Center channel or provide a destination")
    return {
        "kind": "notification_watch",
        "status": "armed" if request.enabled else "paused",
        "name": " ".join(request.name.split()),
        "objective": f"Notify when {request.entity_id} becomes {request.trigger_state.strip()}",
        "presence_entity": "",
        "signal_entities": [request.entity_id.strip().lower()],
        "context_notes": "Notification-only automation created from an explicit user request.",
        "proposal_template": request.message.strip(),
        "action_entity": destination,
        "action_service": "notify.send_message",
        "cooldown_minutes": request.cooldown_minutes,
        "confidence_threshold": 0.99,
        "risk_level": "informational" if request.severity in {"information", "suggestion"} else "controlled",
        "execution_policy": "autonomous",
        "notify_on_action": True,
        "reversible_only": True,
        "max_actions_per_hour": 60,
        "trigger_entity": request.entity_id.strip().lower(),
        "trigger_state": request.trigger_state.strip(),
        "destination": destination,
        "severity": request.severity,
        "title": request.title.strip() or "ZBRANO notification",
        "message": request.message.strip(),
        "active_start": request.active_start,
        "active_end": request.active_end,
        "one_shot": request.one_shot,
        "expires_at": request.expires_at,
        "enabled": request.enabled,
        "last_observed_state": None,
        "last_triggered_at": 0.0,
        "trigger_count": 0,
    }


async def _create_notification_watch(request: NotificationWatchRequest, source: str = "interface") -> dict[str, Any]:
    import secrets

    data = automation_store()
    if len(data["automations"]) >= 100:
        raise HTTPException(status_code=400, detail="Automation limit reached (100)")
    entity_id = request.entity_id.strip().lower()
    try:
        entity = await ha_ws.get_state(entity_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not entity:
        raise HTTPException(status_code=404, detail=f"Home Assistant entity not found: {entity_id}")
    channels = await notification_channels()
    destination = request.destination.strip().lower() or str(notification_store()["settings"].get("default_channel") or "")
    if not any(item["entity_id"] == destination for item in channels):
        raise HTTPException(status_code=400, detail="Notification destination is unavailable")
    now = time.time()
    watch = {
        "id": secrets.token_hex(12),
        "created_at": now,
        "updated_at": now,
        "source": source,
        **_notification_watch_payload(request),
    }
    data["automations"].insert(0, watch)
    _automation_event(data, "notification_watch", f"Notification watch armed: {watch['name']}", watch["objective"])
    _automation_save(data)
    return {"created": True, "watch": watch}


def _watch_time_active(watch: dict[str, Any], now: float) -> bool:
    start = str(watch.get("active_start") or "")
    end = str(watch.get("active_end") or "")
    if not start or not end:
        return True
    current = time.strftime("%H:%M", time.localtime(now))
    return start <= current <= end if start <= end else current >= start or current <= end


def _notification_quiet_now(severity: str, now: float) -> bool:
    settings = notification_store()["settings"]
    if not settings.get("quiet_hours_enabled"):
        return False
    if severity == "critical" and settings.get("critical_override", True):
        return False
    start = str(settings.get("quiet_hours_start") or "22:00")
    end = str(settings.get("quiet_hours_end") or "07:00")
    current = time.strftime("%H:%M", time.localtime(now))
    return start <= current <= end if start <= end else current >= start or current <= end


async def notification_watch_worker() -> None:
    while True:
        await asyncio.sleep(2.0)
        if not SUPERVISOR_TOKEN:
            continue
        if not ha_ws.connected:
            try:
                await ha_ws.connect()
            except RuntimeError:
                continue
        data = automation_store()
        changed = False
        now = time.time()
        for watch in notification_watches(data):
            if not watch.get("enabled"):
                continue
            expires_at = float(watch.get("expires_at") or 0)
            if expires_at and now >= expires_at:
                watch["enabled"] = False
                watch["status"] = "expired"
                watch["updated_at"] = now
                changed = True
                continue
            state = ha_ws.state_cache.get(str(watch.get("trigger_entity") or ""))
            if not state:
                if watch.get("status") != "unavailable":
                    watch["status"] = "unavailable"
                    changed = True
                continue
            current = str(state.get("state") or "")
            previous = watch.get("last_observed_state")
            if previous != current:
                watch["last_observed_state"] = current
                watch["updated_at"] = now
                changed = True
            if previous is None or previous == current or current != str(watch.get("trigger_state") or ""):
                if watch.get("status") == "unavailable":
                    watch["status"] = "armed"
                    changed = True
                continue
            if not _watch_time_active(watch, now):
                continue
            cooldown = max(0, int(watch.get("cooldown_minutes") or 0)) * 60
            if now - float(watch.get("last_triggered_at") or 0) < cooldown:
                continue
            if _notification_quiet_now(str(watch.get("severity") or "information"), now):
                notice = notification_store()
                _notification_delivery(
                    notice, target=str(watch.get("destination") or ""), severity=str(watch.get("severity") or "information"),
                    title=str(watch.get("title") or "ZBRANO notification"), status="suppressed", detail="Matched during configured quiet hours",
                )
                _notification_save(notice)
                watch["last_triggered_at"] = now
                changed = True
                continue
            try:
                await test_notification_channel(NotificationTestRequest(
                    target=str(watch.get("destination") or ""),
                    severity=str(watch.get("severity") or "information"),
                    title=str(watch.get("title") or "ZBRANO notification"),
                    message=str(watch.get("message") or watch.get("objective") or "Notification condition matched."),
                ))
                watch["last_triggered_at"] = now
                watch["trigger_count"] = int(watch.get("trigger_count") or 0) + 1
                watch["status"] = "triggered" if watch.get("one_shot") else "armed"
                if watch.get("one_shot"):
                    watch["enabled"] = False
                watch["updated_at"] = now
                _automation_event(data, "notification", f"Notification delivered: {watch.get('name')}", str(watch.get("destination") or ""))
                changed = True
            except (HTTPException, RuntimeError, ValueError) as exc:
                watch["status"] = "failed"
                watch["last_error"] = str(getattr(exc, "detail", exc))[:500]
                watch["updated_at"] = now
                changed = True
        if changed:
            _automation_save(data)


@app.post("/api/notifications/watches")
async def create_notification_watch(request: NotificationWatchRequest) -> dict[str, Any]:
    return await _create_notification_watch(request)


@app.put("/api/notifications/watches/{watch_id}/state")
async def set_notification_watch_state(watch_id: str, request: NotificationWatchStateRequest) -> dict[str, Any]:
    data = automation_store()
    watch = next((item for item in notification_watches(data) if item.get("id") == watch_id), None)
    if not watch:
        raise HTTPException(status_code=404, detail="Notification watch not found")
    watch["enabled"] = request.enabled
    watch["status"] = "armed" if request.enabled else "paused"
    watch["last_observed_state"] = None
    watch["updated_at"] = time.time()
    _automation_event(data, "notification_watch", f"Notification watch {'armed' if request.enabled else 'paused'}: {watch.get('name')}")
    _automation_save(data)
    return {"saved": True, "watch": watch}


@app.delete("/api/notifications/watches/{watch_id}")
async def delete_notification_watch(watch_id: str) -> dict[str, Any]:
    data = automation_store()
    watch = next((item for item in notification_watches(data) if item.get("id") == watch_id), None)
    if not watch:
        raise HTTPException(status_code=404, detail="Notification watch not found")
    data["automations"] = [item for item in data["automations"] if item.get("id") != watch_id]
    _automation_event(data, "notification_watch", f"Notification watch deleted: {watch.get('name')}")
    _automation_save(data)
    return {"deleted": True}


'''
    backend = replace_once(
        backend,
        '@app.get("/api/notifications")\n',
        watch_backend + '@app.get("/api/notifications")\n',
        "notification watch backend",
    )

    backend = replace_once(
        backend,
        '        "channels": channels,\n        "telegram_channels": sum(item["platform"] == "telegram" for item in channels),\n',
        '        "channels": channels,\n        "watches": notification_watches(),\n        "telegram_channels": sum(item["platform"] == "telegram" for item in channels),\n',
        "watchlist response",
    )

    handler_marker = '''                if name == "find_home_assistant_entities":
                    result = find_approved_entities(arguments["query"])
'''
    require(backend, handler_marker, "local tool handler")
    backend = backend.replace(
        handler_marker,
        '''                if name == "create_notification_watch":
                    result = await _create_notification_watch(NotificationWatchRequest(**arguments), source="chat")
                elif name == "find_home_assistant_entities":
                    result = find_approved_entities(arguments["query"])
''',
        1,
    )
    backend = replace_once(
        backend,
        "            except (asyncio.TimeoutError, MCPError, httpx.HTTPError, RuntimeError, PermissionError, ValueError) as exc:\n",
        "            except (asyncio.TimeoutError, MCPError, httpx.HTTPError, RuntimeError, PermissionError, ValueError, HTTPException) as exc:\n",
        "notification tool HTTP error handling",
    )

    backend = replace_once(
        backend,
        '''                f"{len(payload.get('channels', [])) if isinstance(payload, dict) else 0} Home Assistant notify channels; {payload.get('telegram_channels', 0) if isinstance(payload, dict) else 0} Telegram",
''',
        '''                f"{len(payload.get('channels', [])) if isinstance(payload, dict) else 0} Home Assistant notify channels; {payload.get('telegram_channels', 0) if isinstance(payload, dict) else 0} Telegram; {len(payload.get('watches', [])) if isinstance(payload, dict) else 0} event-driven watches",
''',
        "notification watch diagnostics",
    )

    backend = replace_once(
        backend,
        '''async def start_ha_websocket() -> None:
    global PLUGIN_OAUTH_REFRESH_TASK
''',
        '''async def start_ha_websocket() -> None:
    global PLUGIN_OAUTH_REFRESH_TASK, NOTIFICATION_WATCH_TASK
''',
        "watch worker startup global",
    )
    startup_marker = '''    with contextlib.suppress(HTTPException, OSError, RuntimeError):
        await list_ha_entities()
'''
    require(backend, startup_marker, "watch worker startup")
    backend = backend.replace(
        startup_marker,
        startup_marker + '''    if NOTIFICATION_WATCH_TASK is None or NOTIFICATION_WATCH_TASK.done():
        NOTIFICATION_WATCH_TASK = asyncio.create_task(notification_watch_worker(), name="zbrano-notification-watchlist")
''',
        1,
    )
    backend = replace_once(
        backend,
        '''async def stop_ha_websocket() -> None:
    global PLUGIN_OAUTH_REFRESH_TASK, RELEASE_SYNC_TASK
''',
        '''async def stop_ha_websocket() -> None:
    global PLUGIN_OAUTH_REFRESH_TASK, RELEASE_SYNC_TASK, NOTIFICATION_WATCH_TASK
    if NOTIFICATION_WATCH_TASK is not None:
        NOTIFICATION_WATCH_TASK.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await NOTIFICATION_WATCH_TASK
        NOTIFICATION_WATCH_TASK = None
''',
        "watch worker shutdown",
    )

    watch_panel = r'''        <article class="autonomy-card notification-watchlist-card">
          <div class="autonomy-card-head"><div><h3>Notification Watchlist</h3><p>Notification-only automations created from requests such as “notify me when the workshop door opens.”</p></div><span id="notification-watch-count" class="notification-platform">0 watches</span></div>
          <div id="notification-watchlist" class="notification-watch-list"><div class="autonomy-empty">No notification watches configured.</div></div>
          <p class="muted">Create watches naturally in Chat. An explicit request arms the rule; matching events can notify automatically without another approval.</p>
        </article>
'''
    backend_panel_marker = '        <div class="notification-center-grid notification-center-lower">\n'
    require(frontend, backend_panel_marker, "watchlist panel location")
    frontend = frontend.replace(backend_panel_marker, watch_panel + backend_panel_marker, 1)

    css = r'''
    .notification-watchlist-card { margin-top:.75rem; }
    .notification-watch-list { display:grid; gap:.5rem; margin-top:.65rem; }
    .notification-watch { display:grid; gap:.35rem; border:1px solid var(--line); border-radius:6px; padding:.7rem; min-width:0; }
    .notification-watch[data-status="failed"], .notification-watch[data-status="unavailable"] { border-color:rgba(255,100,90,.42); }
    .notification-watch[data-status="triggered"] { border-color:rgba(92,236,255,.38); }
    .notification-watch-head { display:flex; justify-content:space-between; align-items:flex-start; gap:.65rem; }
    .notification-watch-actions { display:flex; flex-wrap:wrap; gap:.35rem; }
    .notification-watch-meta { display:flex; flex-wrap:wrap; gap:.35rem; }
    .notification-watch-meta span { border:1px solid var(--line); border-radius:999px; padding:.14rem .42rem; font-size:.7rem; }
    @media(max-width:650px) { .notification-watch-head { display:grid; } .notification-watch-actions { width:100%; } }
'''
    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.44 patch could not locate stylesheet")
    frontend = frontend[:style_close] + css + frontend[style_close:]

    frontend = replace_once(
        frontend,
        '  let state = {settings:{}, channels:[], deliveries:[]};\n',
        '  let state = {settings:{}, channels:[], watches:[], deliveries:[]};\n',
        "watchlist frontend state",
    )
    frontend = replace_once(
        frontend,
        '''      const tags=["Draft",authorityLabel(item.execution_policy),`${Math.round(Number(item.confidence_threshold||0)*100)}% confidence`,`${item.cooldown_minutes} min cooldown`,item.risk_level];
      row.innerHTML=`<div class="autonomy-draft-head"><div><strong>${esc(item.name)}</strong><div>${esc(item.objective)}</div></div><div class="autonomy-draft-actions"><button type="button" data-auto-edit="${esc(item.id)}">Edit</button><button type="button" data-auto-delete="${esc(item.id)}">Delete</button></div></div><div class="autonomy-tags">${tags.map(tag=>`<span>${esc(tag)}</span>`).join("")}</div><small>Signals: ${esc((item.signal_entities||[]).join(", ")||"not selected")} · Proposed action: ${esc(item.action_service||"not specified")}</small>`;
''',
        '''      const isWatch=item.kind==="notification_watch";
      const tags=[isWatch?(item.status||"armed"):"Draft",authorityLabel(item.execution_policy),`${Math.round(Number(item.confidence_threshold||0)*100)}% confidence`,`${item.cooldown_minutes} min cooldown`,item.risk_level];
      const primaryAction=isWatch?`<button type="button" data-auto-watch="${esc(item.id)}">Notifications</button>`:`<button type="button" data-auto-edit="${esc(item.id)}">Edit</button>`;
      row.innerHTML=`<div class="autonomy-draft-head"><div><strong>${esc(item.name)}</strong><div>${esc(item.objective)}</div></div><div class="autonomy-draft-actions">${primaryAction}<button type="button" data-auto-delete="${esc(item.id)}">Delete</button></div></div><div class="autonomy-tags">${tags.map(tag=>`<span>${esc(tag)}</span>`).join("")}</div><small>Signals: ${esc((item.signal_entities||[]).join(", ")||"not selected")} · Action: ${esc(item.action_service||"not specified")}</small>`;
''',
        "notification rule Automation Library rendering",
    )
    frontend = replace_once(
        frontend,
        '''    const edit=event.target.closest("[data-auto-edit]");if(edit){const item=state.automations.find(value=>value.id===edit.dataset.autoEdit);if(item)fillEditor(item);return}
''',
        '''    const notificationWatch=event.target.closest("[data-auto-watch]");if(notificationWatch){showView("notifications");window.zbranoNotificationCenter?.load();return}
    const edit=event.target.closest("[data-auto-edit]");if(edit){const item=state.automations.find(value=>value.id===edit.dataset.autoEdit);if(item)fillEditor(item);return}
''',
        "Automation Library watch routing",
    )
    watch_runtime = r'''  function renderWatchlist() {
    const root = $("notification-watchlist"); root.replaceChildren();
    const watches = state.watches || [];
    $("notification-watch-count").textContent = `${watches.length} watch${watches.length === 1 ? "" : "es"}`;
    for (const watch of watches) {
      const row = document.createElement("div"); row.className = "notification-watch"; row.dataset.status = watch.status || "armed";
      const head = document.createElement("div"); head.className = "notification-watch-head";
      const summary = document.createElement("div");
      const name = document.createElement("strong"); name.textContent = watch.name || "Notification watch";
      const objective = document.createElement("div"); objective.textContent = watch.objective || "";
      summary.append(name, objective);
      const actions = document.createElement("div"); actions.className = "notification-watch-actions";
      const toggle = document.createElement("button"); toggle.type = "button"; toggle.dataset.watchToggle = watch.id; toggle.textContent = watch.enabled ? "Pause" : "Arm";
      const remove = document.createElement("button"); remove.type = "button"; remove.dataset.watchDelete = watch.id; remove.textContent = "Delete";
      actions.append(toggle, remove); head.append(summary, actions);
      const meta = document.createElement("div"); meta.className = "notification-watch-meta";
      const values = [watch.status || "armed", watch.severity || "information", watch.one_shot ? "one-time" : "repeating", `${watch.cooldown_minutes || 0} min cooldown`];
      if (watch.active_start && watch.active_end) values.push(`${watch.active_start}–${watch.active_end}`);
      for (const value of values) { const chip = document.createElement("span"); chip.textContent = value; meta.appendChild(chip); }
      const detail = document.createElement("small");
      const last = watch.last_triggered_at ? new Date(watch.last_triggered_at * 1000).toLocaleString() : "never";
      detail.textContent = `${watch.trigger_entity} → ${watch.trigger_state} · ${watch.destination} · triggered ${watch.trigger_count || 0} time(s) · last ${last}`;
      row.append(head, meta, detail); root.appendChild(row);
    }
    if (!watches.length) root.innerHTML = '<div class="autonomy-empty">No notification watches. In Chat, try “Notify me when the workshop door opens.”</div>';
  }

'''
    frontend = replace_once(
        frontend,
        "  function renderDeliveries() {\n",
        watch_runtime + "  function renderDeliveries() {\n",
        "watchlist renderer",
    )
    frontend = replace_once(
        frontend,
        "      renderChannels(); renderSettings(); renderDeliveries();\n",
        "      renderChannels(); renderSettings(); renderWatchlist(); renderDeliveries();\n",
        "watchlist load",
    )
    watch_events = r'''
  $("notification-watchlist").addEventListener("click", async event => {
    const toggle = event.target.closest("[data-watch-toggle]");
    if (toggle) {
      const watch = (state.watches || []).find(item => item.id === toggle.dataset.watchToggle);
      if (!watch) return;
      toggle.disabled = true;
      try { await api(`api/notifications/watches/${encodeURIComponent(watch.id)}/state`, {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({enabled:!watch.enabled})}); await load(); }
      catch (error) { $("notification-settings-status").textContent = `Watch update failed: ${error.message || error}`; toggle.disabled = false; }
      return;
    }
    const remove = event.target.closest("[data-watch-delete]");
    if (remove) {
      if (!confirm("Delete this notification watch?")) return;
      remove.disabled = true;
      try { await api(`api/notifications/watches/${encodeURIComponent(remove.dataset.watchDelete)}`, {method:"DELETE"}); await load(); }
      catch (error) { $("notification-settings-status").textContent = `Watch delete failed: ${error.message || error}`; remove.disabled = false; }
    }
  });
'''
    frontend = replace_once(
        frontend,
        '  tab.addEventListener("click", load);\n',
        watch_events + '  tab.addEventListener("click", load);\n',
        "watchlist controls",
    )

    backend = backend.replace('version="0.12.43"', 'version="0.12.44"')
    backend = backend.replace('"version": "0.12.43"', '"version": "0.12.44"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.43"', '"X-ZBRANO-Frontend-Version": "0.12.44"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.43"', '"name": "ZBRANO Developer Mode", "version": "0.12.44"')
    frontend = frontend.replace("HUD 0.12.43", "HUD 0.12.44")

    required_backend = (
        'version="0.12.44"', "class NotificationWatchRequest", '"name": "create_notification_watch"',
        'entry.get("platform")', '"telegram_bot"', "async def notification_watch_worker()",
        '@app.post("/api/notifications/watches")', 'source="chat"', '"watches": notification_watches()',
        'name="zbrano-notification-watchlist"',
    )
    required_frontend = (
        "HUD 0.12.44", "Notification Watchlist", 'id="notification-watchlist"',
        "renderWatchlist", "dataset.watchToggle", "dataset.watchDelete", 'data-auto-watch=',
    )
    for marker in required_backend:
        require(backend, marker, marker)
    for marker in required_frontend:
        require(frontend, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
