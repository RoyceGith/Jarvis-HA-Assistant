import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.43 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.43 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    models = r'''class NotificationCenterSettingsRequest(BaseModel):
    default_channel: str = Field(default="", max_length=255)
    suggestion_notifications: bool = True
    autonomous_action_notifications: bool = True
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = Field(default="22:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    quiet_hours_end: str = Field(default="07:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    critical_override: bool = True
    repeat_critical_minutes: int = Field(default=15, ge=0, le=1440)


class NotificationTestRequest(BaseModel):
    target: str = Field(min_length=3, max_length=255, pattern=r"^notify\.[a-z0-9_]+$")
    severity: str = Field(default="information", pattern="^(information|suggestion|warning|critical)$")
    title: str = Field(default="ZBRANO notification test", max_length=120)
    message: str = Field(min_length=1, max_length=2000)


'''
    backend = replace_once(
        backend,
        "class SettingsRestoreRequest(BaseModel):\n",
        models + "class SettingsRestoreRequest(BaseModel):\n",
        "notification request models",
    )

    notification_backend = r'''NOTIFICATION_STORAGE_PATH = Path("/data/notification_center.json")
NOTIFICATION_DEFAULT_SETTINGS = {
    "default_channel": "",
    "suggestion_notifications": True,
    "autonomous_action_notifications": True,
    "quiet_hours_enabled": False,
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "07:00",
    "critical_override": True,
    "repeat_critical_minutes": 15,
}


def notification_store() -> dict[str, Any]:
    data = _plugin_load(NOTIFICATION_STORAGE_PATH) or {}
    settings = dict(NOTIFICATION_DEFAULT_SETTINGS)
    if isinstance(data.get("settings"), dict):
        settings.update(data["settings"])
    deliveries = data.get("deliveries") if isinstance(data.get("deliveries"), list) else []
    return {"settings": settings, "deliveries": deliveries[:100]}


def _notification_save(data: dict[str, Any]) -> None:
    data["deliveries"] = list(data.get("deliveries") or [])[:100]
    _plugin_save(NOTIFICATION_STORAGE_PATH, data)


def _notification_delivery(
    data: dict[str, Any], *, target: str, severity: str, title: str,
    status: str, detail: str = "",
) -> dict[str, Any]:
    import secrets

    delivery = {
        "id": secrets.token_hex(8),
        "target": str(target)[:255],
        "severity": str(severity)[:24],
        "title": str(title)[:120],
        "status": str(status)[:24],
        "detail": str(detail)[:500],
        "created_at": time.time(),
    }
    data.setdefault("deliveries", []).insert(0, delivery)
    return delivery


async def notification_channels() -> list[dict[str, Any]]:
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


@app.get("/api/notifications")
async def read_notification_center() -> dict[str, Any]:
    data = notification_store()
    channels = await notification_channels()
    configured = data["settings"].get("default_channel")
    if configured and not any(item["entity_id"] == configured for item in channels):
        data["settings"]["default_channel_available"] = False
    else:
        data["settings"]["default_channel_available"] = bool(configured)
    return {
        **data,
        "channels": channels,
        "telegram_channels": sum(item["platform"] == "telegram" for item in channels),
        "credential_boundary": "Bot tokens remain in Home Assistant and are never returned to ZBRANO.",
    }


@app.put("/api/notifications/settings")
async def update_notification_settings(request: NotificationCenterSettingsRequest) -> dict[str, Any]:
    data = notification_store()
    settings = request.model_dump()
    settings["default_channel"] = settings["default_channel"].strip().lower()
    if settings["default_channel"]:
        channels = await notification_channels()
        if not any(item["entity_id"] == settings["default_channel"] for item in channels):
            raise HTTPException(status_code=400, detail="Selected notification channel is unavailable")
    data["settings"] = settings
    _notification_save(data)
    return {"saved": True, "settings": settings}


@app.post("/api/notifications/test")
async def test_notification_channel(request: NotificationTestRequest) -> dict[str, Any]:
    channels = await notification_channels()
    channel = next((item for item in channels if item["entity_id"] == request.target), None)
    if not channel:
        raise HTTPException(status_code=400, detail="Notification target is not an available Home Assistant notify entity")
    if not SUPERVISOR_TOKEN:
        raise HTTPException(status_code=503, detail="Home Assistant API token unavailable")

    title = request.title.strip() or "ZBRANO notification test"
    data = notification_store()
    headers = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}", "Content-Type": "application/json"}
    body = {
        "entity_id": request.target,
        "title": title,
        "message": request.message.strip(),
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(f"{HA_API_BASE}/services/notify/send_message", headers=headers, json=body)
        if response.is_error:
            raise RuntimeError(f"Home Assistant returned HTTP {response.status_code}: {response.text[:300]}")
        delivery = _notification_delivery(
            data, target=request.target, severity=request.severity,
            title=title, status="delivered", detail=f"Sent through {channel['platform']} via Home Assistant",
        )
        _notification_save(data)
        return {"delivered": True, "delivery": delivery}
    except (httpx.HTTPError, RuntimeError) as exc:
        delivery = _notification_delivery(
            data, target=request.target, severity=request.severity,
            title=title, status="failed", detail=str(exc),
        )
        _notification_save(data)
        raise HTTPException(status_code=502, detail=f"Notification delivery failed: {exc}") from exc


'''
    backend = replace_once(
        backend,
        '@app.get("/api/settings")\n',
        notification_backend + '@app.get("/api/settings")\n',
        "notification API insertion point",
    )

    backend = replace_once(
        backend,
        '        "automations": automation_store(),\n',
        '        "automations": automation_store(),\n        "notifications": notification_store(),\n',
        "notification backup export",
    )
    backend = replace_once(
        backend,
        '    automations = backup.get("automations")\n',
        '    automations = backup.get("automations")\n    notifications = backup.get("notifications")\n',
        "notification backup restore input",
    )
    backend = replace_once(
        backend,
        '''    if automations is not None and (
        not isinstance(automations, dict)
        or not isinstance(automations.get("settings"), dict)
        or not isinstance(automations.get("automations"), list)
        or not isinstance(automations.get("suggestions", []), list)
        or not isinstance(automations.get("timeline", []), list)
    ):
        raise HTTPException(status_code=400, detail="Automation backup data is malformed")''',
        '''    if automations is not None and (
        not isinstance(automations, dict)
        or not isinstance(automations.get("settings"), dict)
        or not isinstance(automations.get("automations"), list)
        or not isinstance(automations.get("suggestions", []), list)
        or not isinstance(automations.get("timeline", []), list)
    ):
        raise HTTPException(status_code=400, detail="Automation backup data is malformed")
    if notifications is not None and (
        not isinstance(notifications, dict)
        or not isinstance(notifications.get("settings"), dict)
        or not isinstance(notifications.get("deliveries", []), list)
    ):
        raise HTTPException(status_code=400, detail="Backup notification data is malformed")''',
        "notification backup validation",
    )
    backend = replace_once(
        backend,
        '''    if automations is not None:
        _automation_save(automations)
    load_chat_sessions()''',
        '''    if automations is not None:
        _automation_save(automations)
    if notifications is not None:
        _notification_save(notifications)
    load_chat_sessions()''',
        "notification backup persistence",
    )

    diagnostic_marker = '''        await probe(
            "Autonomous Automations API operational",
            "/api/automations",
            lambda payload: (
                "operational" if isinstance(payload, dict) and isinstance(payload.get("automations"), list) else "failed",
                f"{len(payload.get('automations', [])) if isinstance(payload, dict) else 0} automation drafts; evaluator intentionally inactive",
            ),
            "automations",
        )
'''
    require(backend, diagnostic_marker, "notification diagnostics insertion")
    backend = backend.replace(
        diagnostic_marker,
        diagnostic_marker + '''
        await probe(
            "Notification Center API operational",
            "/api/notifications",
            lambda payload: (
                "operational" if isinstance(payload, dict) and isinstance(payload.get("channels"), list) else "failed",
                f"{len(payload.get('channels', [])) if isinstance(payload, dict) else 0} Home Assistant notify channels; {payload.get('telegram_channels', 0) if isinstance(payload, dict) else 0} Telegram",
            ),
            "automations",
        )
''',
        1,
    )
    backend = replace_once(
        backend,
        '''            "Automations frontend wired": ('id="automations-tab"', 'id="automations-panel"', 'zbrano-v01210-autonomous-automations'),''',
        '''            "Automations frontend wired": ('id="automations-tab"', 'id="automations-panel"', 'zbrano-v01210-autonomous-automations'),
            "Notification Center frontend wired": ('data-auto-view="notifications"', 'id="notification-settings-form"', 'zbrano-v01243-notification-center'),''',
        "notification frontend diagnostics",
    )

    frontend = replace_once(
        frontend,
        '''        <button type="button" data-auto-view="safety" role="tab" aria-selected="false">Safety &amp; Authority</button>
        <button type="button" data-auto-view="activity" role="tab" aria-selected="false">Activity</button>''',
        '''        <button type="button" data-auto-view="safety" role="tab" aria-selected="false">Safety &amp; Authority</button>
        <button type="button" data-auto-view="notifications" role="tab" aria-selected="false">Notifications</button>
        <button type="button" data-auto-view="activity" role="tab" aria-selected="false">Activity</button>''',
        "Notifications automation tab",
    )

    notification_panel = r'''      <section class="autonomy-view hidden" data-auto-panel="notifications">
        <div class="notification-center-grid">
          <article class="autonomy-card notification-channel-card">
            <div class="autonomy-card-head"><div><h3>Notification Channels</h3><p>ZBRANO discovers Home Assistant notify entities. Telegram credentials remain inside Home Assistant.</p></div><button id="notification-refresh" type="button">Refresh</button></div>
            <div id="notification-channels" class="notification-channel-list"><div class="autonomy-empty">Open Notifications to discover channels.</div></div>
            <p id="notification-credential-boundary" class="muted"></p>
          </article>
          <article class="autonomy-card">
            <h3>Delivery Policy</h3><p>Saved notification rules inherit these defaults. An approved rule may deliver without asking again.</p>
            <form id="notification-settings-form">
              <div class="notification-form-grid">
                <label class="wide">Default channel<select id="notification-default-channel"><option value="">Choose a Home Assistant notify entity</option></select></label>
                <label class="check wide"><input id="notification-suggestions" type="checkbox" checked> Send autonomous suggestions through the default channel</label>
                <label class="check wide"><input id="notification-actions" type="checkbox" checked> Notify after autonomous actions</label>
                <label class="check wide"><input id="notification-quiet-enabled" type="checkbox"> Enable notification quiet hours</label>
                <label>Quiet hours start<input id="notification-quiet-start" type="time" value="22:00"></label>
                <label>Quiet hours end<input id="notification-quiet-end" type="time" value="07:00"></label>
                <label class="check wide"><input id="notification-critical-override" type="checkbox" checked> Critical alerts override quiet hours</label>
                <label>Repeat critical alerts (minutes)<input id="notification-critical-repeat" type="number" min="0" max="1440" value="15"></label>
              </div>
              <div class="autonomy-form-actions"><button type="submit">Save notification policy</button><span id="notification-settings-status" role="status"></span></div>
            </form>
          </article>
        </div>
        <div class="notification-center-grid notification-center-lower">
          <article class="autonomy-card">
            <h3>Test Delivery</h3><p>This sends one real notification through the selected Home Assistant channel.</p>
            <form id="notification-test-form">
              <div class="notification-form-grid">
                <label>Target<select id="notification-test-target" required><option value="">Choose channel</option></select></label>
                <label>Severity<select id="notification-test-severity"><option value="information">Information</option><option value="suggestion">Suggestion</option><option value="warning">Warning</option><option value="critical">Critical</option></select></label>
                <label class="wide">Title<input id="notification-test-title" maxlength="120" value="ZBRANO notification test"></label>
                <label class="wide">Message<textarea id="notification-test-message" rows="3" maxlength="2000" required>ZBRANO Notification Center is connected.</textarea></label>
              </div>
              <div class="autonomy-form-actions"><button type="submit">Send test notification</button><span id="notification-test-status" role="status"></span></div>
            </form>
          </article>
          <article class="autonomy-card">
            <div class="autonomy-card-head"><div><h3>Delivery Log</h3><p>Recent delivery outcomes without storing message bodies or credentials.</p></div></div>
            <div id="notification-deliveries" class="notification-delivery-list"><div class="autonomy-empty">No deliveries recorded.</div></div>
          </article>
        </div>
      </section>

'''
    frontend = replace_once(
        frontend,
        '      <section class="autonomy-view hidden" data-auto-panel="activity">\n',
        notification_panel + '      <section class="autonomy-view hidden" data-auto-panel="activity">\n',
        "Notification Center panel",
    )

    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.43 patch could not locate the final stylesheet")
    notification_css = r'''
    .notification-center-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.75rem; margin-top:.75rem; }
    .notification-center-lower { margin-top:.75rem; }
    #notification-settings-form, #notification-test-form { display:block; min-width:0; margin-top:.65rem; }
    .notification-form-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.6rem; }
    .notification-form-grid label { display:grid; gap:.3rem; min-width:0; }
    .notification-form-grid .wide { grid-column:1/-1; }
    .notification-form-grid .check { display:flex; align-items:center; gap:.5rem; }
    .notification-form-grid input:not([type="checkbox"]), .notification-form-grid select, .notification-form-grid textarea { width:100%; min-width:0; max-width:100%; }
    .notification-form-grid input[type="checkbox"] { width:auto; flex:0 0 auto; }
    .notification-channel-list, .notification-delivery-list { display:grid; gap:.45rem; margin-top:.65rem; }
    .notification-channel, .notification-delivery { display:grid; gap:.2rem; border:1px solid var(--line); border-radius:6px; padding:.65rem; min-width:0; }
    .notification-channel-head, .notification-delivery-head { display:flex; justify-content:space-between; align-items:center; gap:.6rem; }
    .notification-platform { border:1px solid var(--line); border-radius:999px; padding:.15rem .42rem; color:var(--cyan); font-size:.68rem; text-transform:uppercase; }
    .notification-channel code { overflow-wrap:anywhere; }
    .notification-delivery[data-status="failed"] { border-color:rgba(255,100,90,.42); }
    .notification-delivery[data-status="delivered"] { border-color:rgba(92,236,255,.3); }
    @media(max-width:900px) { .notification-center-grid, .notification-form-grid { grid-template-columns:1fr; } .notification-form-grid .wide { grid-column:auto; } }
'''
    frontend = frontend[:style_close] + notification_css + frontend[style_close:]

    body_close = frontend.rfind("</body>")
    if body_close < 0:
        raise RuntimeError("ZBRANO v0.12.43 patch could not locate body close")
    notification_runtime = r'''
<script id="zbrano-v01243-notification-center">
(() => {
  const tab = document.querySelector('[data-auto-view="notifications"]');
  const panel = document.querySelector('[data-auto-panel="notifications"]');
  if (!tab || !panel) return;
  const $ = id => document.getElementById(id);
  let state = {settings:{}, channels:[], deliveries:[]};

  async function api(path, options={}) {
    const response = await fetch(path, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    return data;
  }

  function option(select, channel) {
    const node = document.createElement("option");
    node.value = channel.entity_id;
    node.textContent = `${channel.platform === "telegram" ? "Telegram · " : ""}${channel.friendly_name}`;
    select.appendChild(node);
  }

  function renderChannels() {
    const root = $("notification-channels"); root.replaceChildren();
    const defaultSelect = $("notification-default-channel");
    const testSelect = $("notification-test-target");
    defaultSelect.replaceChildren(new Option("Choose a Home Assistant notify entity", ""));
    testSelect.replaceChildren(new Option("Choose channel", ""));
    for (const channel of state.channels) {
      option(defaultSelect, channel); option(testSelect, channel);
      const row = document.createElement("div"); row.className = "notification-channel";
      const head = document.createElement("div"); head.className = "notification-channel-head";
      const name = document.createElement("strong"); name.textContent = channel.friendly_name;
      const platform = document.createElement("span"); platform.className = "notification-platform"; platform.textContent = channel.platform;
      const id = document.createElement("code"); id.textContent = channel.entity_id;
      const availability = document.createElement("small"); availability.textContent = channel.available ? "Available" : `Unavailable · ${channel.state || "unknown"}`;
      head.append(name, platform); row.append(head, id, availability); root.appendChild(row);
    }
    if (!state.channels.length) root.innerHTML = '<div class="autonomy-empty">No Home Assistant notify entities found. Finish the Telegram bot integration and add an allowed chat ID.</div>';
    defaultSelect.value = state.settings.default_channel || "";
    testSelect.value = state.settings.default_channel || "";
  }

  function renderSettings() {
    $("notification-suggestions").checked = state.settings.suggestion_notifications !== false;
    $("notification-actions").checked = state.settings.autonomous_action_notifications !== false;
    $("notification-quiet-enabled").checked = Boolean(state.settings.quiet_hours_enabled);
    $("notification-quiet-start").value = state.settings.quiet_hours_start || "22:00";
    $("notification-quiet-end").value = state.settings.quiet_hours_end || "07:00";
    $("notification-critical-override").checked = state.settings.critical_override !== false;
    $("notification-critical-repeat").value = String(state.settings.repeat_critical_minutes ?? 15);
  }

  function renderDeliveries() {
    const root = $("notification-deliveries"); root.replaceChildren();
    for (const delivery of state.deliveries || []) {
      const row = document.createElement("div"); row.className = "notification-delivery"; row.dataset.status = delivery.status;
      const head = document.createElement("div"); head.className = "notification-delivery-head";
      const title = document.createElement("strong"); title.textContent = delivery.title || "Notification";
      const status = document.createElement("span"); status.className = "notification-platform"; status.textContent = delivery.status;
      const detail = document.createElement("small"); detail.textContent = `${delivery.target} · ${delivery.severity} · ${new Date(delivery.created_at * 1000).toLocaleString()}`;
      const evidence = document.createElement("small"); evidence.textContent = delivery.detail || "";
      head.append(title, status); row.append(head, detail, evidence); root.appendChild(row);
    }
    if (!state.deliveries?.length) root.innerHTML = '<div class="autonomy-empty">No deliveries recorded.</div>';
  }

  async function load() {
    const status = $("notification-settings-status"); status.textContent = "Discovering channels…";
    try {
      state = await api("api/notifications");
      renderChannels(); renderSettings(); renderDeliveries();
      $("notification-credential-boundary").textContent = state.credential_boundary || "";
      status.textContent = `${state.channels.length} channel(s); ${state.telegram_channels || 0} Telegram`;
    } catch (error) { status.textContent = `Load failed: ${error.message || error}`; }
  }

  $("notification-settings-form").addEventListener("submit", async event => {
    event.preventDefault(); const status = $("notification-settings-status"); status.textContent = "Saving…";
    const body = {
      default_channel: $("notification-default-channel").value,
      suggestion_notifications: $("notification-suggestions").checked,
      autonomous_action_notifications: $("notification-actions").checked,
      quiet_hours_enabled: $("notification-quiet-enabled").checked,
      quiet_hours_start: $("notification-quiet-start").value,
      quiet_hours_end: $("notification-quiet-end").value,
      critical_override: $("notification-critical-override").checked,
      repeat_critical_minutes: Number($("notification-critical-repeat").value || 0),
    };
    try { await api("api/notifications/settings", {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)}); status.textContent = "Notification policy saved."; await load(); }
    catch (error) { status.textContent = `Save failed: ${error.message || error}`; }
  });

  $("notification-test-form").addEventListener("submit", async event => {
    event.preventDefault(); const status = $("notification-test-status"); status.textContent = "Sending…";
    const body = {target:$("notification-test-target").value, severity:$("notification-test-severity").value, title:$("notification-test-title").value, message:$("notification-test-message").value};
    try { await api("api/notifications/test", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)}); status.textContent = "Delivered through Home Assistant."; await load(); }
    catch (error) { status.textContent = `Delivery failed: ${error.message || error}`; await load(); }
  });

  tab.addEventListener("click", load);
  $("notification-refresh").addEventListener("click", load);
  window.zbranoNotificationCenter = {load};
})();
</script>
'''
    frontend = frontend[:body_close] + notification_runtime + frontend[body_close:]

    backend = backend.replace('version="0.12.42"', 'version="0.12.43"')
    backend = backend.replace('"version": "0.12.42"', '"version": "0.12.43"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.42"', '"X-ZBRANO-Frontend-Version": "0.12.43"')
    backend = backend.replace('"name": "ZBRANO Developer Mode", "version": "0.12.42"', '"name": "ZBRANO Developer Mode", "version": "0.12.43"')
    frontend = frontend.replace("HUD 0.12.42", "HUD 0.12.43")

    require(backend, '@app.get("/api/notifications")', "Notification Center read API")
    require(backend, '@app.post("/api/notifications/test")', "notification test API")
    require(backend, '"notifications": notification_store()', "notification backup")
    require(frontend, 'data-auto-view="notifications"', "Notifications tab")
    require(frontend, 'id="zbrano-v01243-notification-center"', "Notification Center controller")
    require(backend, "Bot tokens remain in Home Assistant", "credential boundary")
    require(backend, 'version="0.12.43"', "backend version")
    require(frontend, "HUD 0.12.43", "HUD version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
