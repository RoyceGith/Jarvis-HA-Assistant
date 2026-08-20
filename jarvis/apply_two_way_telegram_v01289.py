import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.89 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.89 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    models = r'''class TelegramInboundSettingsRequest(BaseModel):
    enabled: bool = False
    reply_channel: str = Field(default="", max_length=255, pattern=r"^(|notify\.[a-z0-9_]+)$")
    remote_approvals_enabled: bool = False


class TelegramInboundUnlinkRequest(BaseModel):
    chat_id: str = Field(min_length=1, max_length=64, pattern=r"^-?[0-9]+$")


'''
    backend = replace_once(
        backend,
        "class SettingsRestoreRequest(BaseModel):\n",
        models + "class SettingsRestoreRequest(BaseModel):\n",
        "Telegram Inbox request models",
    )

    telegram_backend = r'''TELEGRAM_INBOUND_PATH = Path("/data/telegram_inbound.json")
TELEGRAM_INBOUND_TASK: asyncio.Task[None] | None = None
TELEGRAM_INBOUND_STATUS: dict[str, Any] = {
    "connected": False,
    "last_error": "",
    "last_event_at": 0.0,
    "messages_received": 0,
    "messages_rejected": 0,
}
TELEGRAM_CHAT_LOCKS: dict[str, asyncio.Lock] = {}
TELEGRAM_RECENT_EVENTS: dict[str, float] = {}


def telegram_inbound_store() -> dict[str, Any]:
    data = _plugin_load(TELEGRAM_INBOUND_PATH) or {}
    settings = data.get("settings") if isinstance(data.get("settings"), dict) else {}
    linked = data.get("linked_chats") if isinstance(data.get("linked_chats"), list) else []
    return {
        "settings": {
            "enabled": bool(settings.get("enabled", False)),
            "reply_channel": str(settings.get("reply_channel") or ""),
            "remote_approvals_enabled": bool(settings.get("remote_approvals_enabled", False)),
        },
        "linked_chats": [item for item in linked if isinstance(item, dict)][:20],
        "pairing": data.get("pairing") if isinstance(data.get("pairing"), dict) else {},
    }


def _telegram_inbound_save(data: dict[str, Any]) -> None:
    data["linked_chats"] = list(data.get("linked_chats") or [])[:20]
    _plugin_save(TELEGRAM_INBOUND_PATH, data)


def _telegram_public_status() -> dict[str, Any]:
    data = telegram_inbound_store()
    pairing = data.get("pairing") or {}
    expires_at = float(pairing.get("expires_at") or 0.0)
    return {
        "settings": data["settings"],
        "linked_chats": [
            {
                "chat_id": str(item.get("chat_id") or ""),
                "display_name": str(item.get("display_name") or "Telegram owner")[:120],
                "username": str(item.get("username") or "")[:120],
                "linked_at": float(item.get("linked_at") or 0.0),
                "last_message_at": float(item.get("last_message_at") or 0.0),
                "session_id": str(item.get("session_id") or "")[:160],
            }
            for item in data["linked_chats"]
        ],
        "pairing_active": bool(pairing.get("code") and expires_at > time.time()),
        "pairing_expires_at": expires_at,
        "listener": dict(TELEGRAM_INBOUND_STATUS),
        "credential_boundary": "Home Assistant owns the Telegram bot token; ZBRANO stores only explicitly paired chat IDs.",
    }


async def _telegram_send(chat_id: str, message: str, *, title: str = "ZBRANO") -> None:
    clean = str(message or "").strip()
    if not clean:
        return
    parts = [clean[index:index + 3800] for index in range(0, len(clean), 3800)]
    settings = telegram_inbound_store()["settings"]
    for part in parts:
        try:
            await ha_ws.call_service(
                "telegram_bot",
                "send_message",
                {"target": int(chat_id), "message": part},
            )
        except (RuntimeError, OSError, asyncio.TimeoutError, ConnectionClosed):
            target = str(settings.get("reply_channel") or notification_store()["settings"].get("default_channel") or "")
            if not target:
                raise
            await test_notification_channel(NotificationTestRequest(
                target=target,
                severity="information",
                title=title,
                message=part,
            ))


def _telegram_event_fields(event_type: str, data: dict[str, Any]) -> tuple[str, str, str, str]:
    chat_id = str(data.get("chat_id") or data.get("chat") or "").strip()
    username = str(data.get("from_username") or data.get("username") or "").strip()
    display_name = " ".join(
        value for value in (
            str(data.get("from_first") or data.get("first_name") or "").strip(),
            str(data.get("from_last") or data.get("last_name") or "").strip(),
        ) if value
    ) or username or "Telegram owner"
    if event_type == "telegram_command":
        command = str(data.get("command") or "").strip()
        if command and not command.startswith("/"):
            command = "/" + command
        args = data.get("args")
        if isinstance(args, list):
            text = " ".join([command, *[str(value) for value in args]]).strip()
        else:
            text = " ".join([command, str(args or "")]).strip()
    else:
        text = str(data.get("text") or "").strip()
    return chat_id, text, username, display_name


def _telegram_event_duplicate(event_type: str, data: dict[str, Any], chat_id: str, text: str) -> bool:
    now = time.time()
    event_id = data.get("id") or data.get("message_id") or data.get("update_id")
    key = f"{event_type}:{chat_id}:{event_id if event_id is not None else text}"
    previous = TELEGRAM_RECENT_EVENTS.get(key, 0.0)
    TELEGRAM_RECENT_EVENTS[key] = now
    for old_key, timestamp in list(TELEGRAM_RECENT_EVENTS.items()):
        if now - timestamp > 120:
            TELEGRAM_RECENT_EVENTS.pop(old_key, None)
    return bool(previous and now - previous < 30)


async def _telegram_process_message(chat_id: str, text: str) -> None:
    lock = TELEGRAM_CHAT_LOCKS.setdefault(chat_id, asyncio.Lock())
    if lock.locked():
        await _telegram_send(chat_id, "I am still working on your previous message. Please wait for the reply.")
        return
    async with lock:
        data = telegram_inbound_store()
        linked = next((item for item in data["linked_chats"] if str(item.get("chat_id")) == chat_id), None)
        if not linked:
            return
        normalized = " ".join(text.lower().split())
        if normalized in {"/help", "help"}:
            await _telegram_send(chat_id, "Send me a normal message to talk with ZBRANO. Commands: /new, /status, /unlink, /approve, /cancel.")
            return
        if normalized == "/status":
            await _telegram_send(chat_id, "ZBRANO Telegram Inbox is online and this chat is paired.")
            return
        if normalized == "/new":
            linked["session_id"] = f"telegram-{chat_id}-{int(time.time())}"
            linked["last_message_at"] = time.time()
            _telegram_inbound_save(data)
            await _telegram_send(chat_id, "Started a new ZBRANO conversation. Your earlier Telegram chat remains in Conversations.")
            return
        if normalized == "/unlink":
            data["linked_chats"] = [item for item in data["linked_chats"] if str(item.get("chat_id")) != chat_id]
            _telegram_inbound_save(data)
            await _telegram_send(chat_id, "This Telegram chat is now unlinked from ZBRANO.")
            return
        if normalized in {"/approve", "approve", "/cancel", "cancel"}:
            if not data["settings"].get("remote_approvals_enabled"):
                await _telegram_send(chat_id, "Remote approvals are disabled. Enable them in Notification Center → Telegram Inbox, or approve from the ZBRANO interface.")
                return
            text = "approve" if "approve" in normalized else "cancel"

        linked["last_message_at"] = time.time()
        session_id = str(linked.get("session_id") or f"telegram-{chat_id}")
        linked["session_id"] = session_id
        _telegram_inbound_save(data)
        try:
            result = await asyncio.wait_for(run_jarvis(text, session_id), timeout=120.0)
            reply = str(result.get("reply") or "ZBRANO completed the request without a text response.")
            await _telegram_send(chat_id, reply)
        except asyncio.TimeoutError:
            await _telegram_send(chat_id, "The request exceeded two minutes and was stopped. No automatic retry was started.")
        except Exception as exc:
            await _telegram_send(chat_id, f"I could not complete that request: {str(exc)[:500]}")


async def _telegram_handle_event(event_type: str, data: dict[str, Any]) -> None:
    chat_id, text, username, display_name = _telegram_event_fields(event_type, data)
    if not chat_id or not text or _telegram_event_duplicate(event_type, data, chat_id, text):
        return
    TELEGRAM_INBOUND_STATUS["last_event_at"] = time.time()
    store = telegram_inbound_store()
    linked = next((item for item in store["linked_chats"] if str(item.get("chat_id")) == chat_id), None)
    normalized = " ".join(text.strip().split())
    pairing = store.get("pairing") or {}
    expected = str(pairing.get("code") or "")
    supplied = normalized[6:].strip().upper() if normalized.lower().startswith("/link ") else ""
    if not linked and expected and time.time() < float(pairing.get("expires_at") or 0.0) and supplied == expected:
        record = {
            "chat_id": chat_id,
            "display_name": display_name,
            "username": username,
            "linked_at": time.time(),
            "last_message_at": time.time(),
            "session_id": f"telegram-{chat_id}",
        }
        store["linked_chats"].append(record)
        store["pairing"] = {}
        _telegram_inbound_save(store)
        await _telegram_send(chat_id, "Telegram is now securely linked to ZBRANO. Send /help to see the available commands.")
        return
    if not linked:
        TELEGRAM_INBOUND_STATUS["messages_rejected"] += 1
        return
    TELEGRAM_INBOUND_STATUS["messages_received"] += 1
    asyncio.create_task(_telegram_process_message(chat_id, text), name=f"zbrano-telegram-message-{chat_id}")


async def telegram_inbound_worker() -> None:
    backoff = 2.0
    while True:
        try:
            if not telegram_inbound_store()["settings"].get("enabled") or not SUPERVISOR_TOKEN:
                TELEGRAM_INBOUND_STATUS["connected"] = False
                await asyncio.sleep(2.0)
                continue
            async with websockets.connect(
                HA_WS_URL,
                open_timeout=10,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=5,
                max_size=1024 * 1024,
            ) as ws:
                hello = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                if hello.get("type") != "auth_required":
                    raise RuntimeError("Unexpected Home Assistant WebSocket greeting")
                await ws.send(json.dumps({"type": "auth", "access_token": SUPERVISOR_TOKEN}))
                auth = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                if auth.get("type") != "auth_ok":
                    raise RuntimeError(auth.get("message") or "Home Assistant WebSocket authentication failed")
                subscriptions = {901: "telegram_text", 902: "telegram_command"}
                for command_id, event_type in subscriptions.items():
                    await ws.send(json.dumps({"id": command_id, "type": "subscribe_events", "event_type": event_type}))
                confirmed: set[int] = set()
                while len(confirmed) < len(subscriptions):
                    result = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                    if result.get("type") == "result" and int(result.get("id", -1)) in subscriptions:
                        if not result.get("success"):
                            raise RuntimeError((result.get("error") or {}).get("message") or "Telegram event subscription failed")
                        confirmed.add(int(result["id"]))
                TELEGRAM_INBOUND_STATUS.update({"connected": True, "last_error": ""})
                backoff = 2.0
                async for raw in ws:
                    message = json.loads(raw)
                    if message.get("type") != "event":
                        continue
                    event = message.get("event") or {}
                    event_type = str(event.get("event_type") or "")
                    if event_type in {"telegram_text", "telegram_command"}:
                        await _telegram_handle_event(event_type, event.get("data") or {})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            TELEGRAM_INBOUND_STATUS.update({"connected": False, "last_error": str(exc)[:500]})
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2.0, 30.0)
        finally:
            TELEGRAM_INBOUND_STATUS["connected"] = False


@app.get("/api/telegram-inbound")
async def read_telegram_inbound() -> dict[str, Any]:
    return _telegram_public_status()


@app.put("/api/telegram-inbound/settings")
async def update_telegram_inbound_settings(request: TelegramInboundSettingsRequest) -> dict[str, Any]:
    data = telegram_inbound_store()
    settings = request.model_dump()
    settings["reply_channel"] = settings["reply_channel"].strip().lower()
    if settings["reply_channel"]:
        channels = await notification_channels()
        selected = next((item for item in channels if item["entity_id"] == settings["reply_channel"]), None)
        if not selected or selected.get("platform") != "telegram":
            raise HTTPException(status_code=400, detail="Reply channel must be an available Telegram notify entity")
    data["settings"] = settings
    _telegram_inbound_save(data)
    return _telegram_public_status()


@app.post("/api/telegram-inbound/link-code")
async def create_telegram_link_code() -> dict[str, Any]:
    import secrets

    data = telegram_inbound_store()
    if not data["settings"].get("enabled"):
        raise HTTPException(status_code=400, detail="Enable Telegram Inbox before generating a pairing code")
    code = secrets.token_hex(4).upper()
    expires_at = time.time() + 600
    data["pairing"] = {"code": code, "expires_at": expires_at}
    _telegram_inbound_save(data)
    return {"code": code, "expires_at": expires_at, "command": f"/link {code}"}


@app.post("/api/telegram-inbound/unlink")
async def unlink_telegram_chat(request: TelegramInboundUnlinkRequest) -> dict[str, Any]:
    data = telegram_inbound_store()
    before = len(data["linked_chats"])
    data["linked_chats"] = [item for item in data["linked_chats"] if str(item.get("chat_id")) != request.chat_id]
    _telegram_inbound_save(data)
    return {"removed": len(data["linked_chats"]) < before, **_telegram_public_status()}


@app.on_event("startup")
async def start_telegram_inbound() -> None:
    global TELEGRAM_INBOUND_TASK
    if TELEGRAM_INBOUND_TASK is None or TELEGRAM_INBOUND_TASK.done():
        TELEGRAM_INBOUND_TASK = asyncio.create_task(telegram_inbound_worker(), name="zbrano-telegram-inbound")


@app.on_event("shutdown")
async def stop_telegram_inbound() -> None:
    global TELEGRAM_INBOUND_TASK
    if TELEGRAM_INBOUND_TASK is not None:
        TELEGRAM_INBOUND_TASK.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await TELEGRAM_INBOUND_TASK
        TELEGRAM_INBOUND_TASK = None


'''
    backend = replace_once(
        backend,
        '@app.get("/api/settings")\n',
        telegram_backend + '@app.get("/api/settings")\n',
        "Telegram Inbox backend insertion point",
    )

    telegram_panel = r'''        <article class="autonomy-card telegram-inbox-card">
          <div class="autonomy-card-head"><div><h3>Telegram Inbox</h3><p>Talk with ZBRANO remotely through explicitly paired Telegram chats. Home Assistant keeps the bot token.</p></div><span id="telegram-inbound-state" class="notification-platform">Disabled</span></div>
          <form id="telegram-inbound-form">
            <div class="notification-form-grid">
              <label class="check wide"><input id="telegram-inbound-enabled" type="checkbox"> Enable incoming Telegram messages</label>
              <label class="wide">Reply channel<select id="telegram-inbound-channel"><option value="">Use Notification Center default</option></select></label>
              <label class="check wide"><input id="telegram-remote-approvals" type="checkbox"> Allow paired Telegram chats to approve already-proposed actions</label>
            </div>
            <div class="autonomy-form-actions"><button type="submit">Save Telegram Inbox</button><button id="telegram-generate-code" type="button">Generate pairing code</button><span id="telegram-inbound-status" role="status"></span></div>
          </form>
          <div id="telegram-pairing-command" class="telegram-pairing-command" hidden></div>
          <div id="telegram-linked-chats" class="notification-channel-list"><div class="autonomy-empty">No Telegram chats paired.</div></div>
          <p id="telegram-credential-boundary" class="muted"></p>
        </article>

'''
    frontend = replace_once(
        frontend,
        '        <div class="notification-center-grid notification-center-lower">\n',
        telegram_panel + '        <div class="notification-center-grid notification-center-lower">\n',
        "Telegram Inbox Notification Center card",
    )

    style_close = frontend.rfind("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.89 patch could not locate stylesheet")
    telegram_css = r'''
    .telegram-inbox-card { margin-top:.75rem; }
    #telegram-inbound-form { display:block; margin-top:.65rem; }
    .telegram-pairing-command { margin:.7rem 0; padding:.7rem; border:1px solid color-mix(in srgb,var(--cyan) 55%,var(--line)); border-radius:6px; background:color-mix(in srgb,var(--cyan) 8%,transparent); overflow-wrap:anywhere; }
    .telegram-pairing-command code { display:block; margin-top:.3rem; color:var(--cyan); font-size:1rem; user-select:all; }
    .telegram-linked-chat { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:.35rem .65rem; align-items:center; }
    .telegram-linked-chat small { grid-column:1/-1; }
    .telegram-linked-chat button { min-height:2rem; padding:.25rem .55rem; }
'''
    frontend = frontend[:style_close] + telegram_css + frontend[style_close:]

    body_close = frontend.rfind("</body>")
    if body_close < 0:
        raise RuntimeError("ZBRANO v0.12.89 patch could not locate body close")
    telegram_runtime = r'''
<script id="zbrano-v01289-two-way-telegram">
(() => {
  const tab = document.querySelector('[data-auto-view="notifications"]');
  const $ = id => document.getElementById(id);
  if (!tab || !$('telegram-inbound-form')) return;
  let state = {settings:{}, linked_chats:[], listener:{}};

  async function api(path, options={}) {
    const response = await fetch(path, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    return data;
  }

  async function load() {
    const status = $('telegram-inbound-status');
    try {
      const [inbound, notifications] = await Promise.all([api('api/telegram-inbound'), api('api/notifications')]);
      state = inbound;
      $('telegram-inbound-enabled').checked = Boolean(state.settings?.enabled);
      $('telegram-remote-approvals').checked = Boolean(state.settings?.remote_approvals_enabled);
      const channel = $('telegram-inbound-channel');
      channel.replaceChildren(new Option('Use Notification Center default', ''));
      for (const item of notifications.channels || []) {
        if (item.platform === 'telegram') channel.appendChild(new Option(`Telegram · ${item.friendly_name}`, item.entity_id));
      }
      channel.value = state.settings?.reply_channel || '';
      const badge = $('telegram-inbound-state');
      badge.textContent = !state.settings?.enabled ? 'Disabled' : state.listener?.connected ? 'Online' : 'Waiting';
      badge.dataset.status = state.listener?.connected ? 'online' : 'offline';
      status.textContent = state.listener?.last_error ? `Listener: ${state.listener.last_error}` : `${state.linked_chats?.length || 0} paired chat(s)`;
      $('telegram-credential-boundary').textContent = state.credential_boundary || '';
      const root = $('telegram-linked-chats'); root.replaceChildren();
      for (const item of state.linked_chats || []) {
        const row = document.createElement('div'); row.className = 'notification-channel telegram-linked-chat';
        const identity = document.createElement('strong'); identity.textContent = item.display_name || 'Telegram owner';
        const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = 'Unlink'; remove.dataset.telegramUnlink = item.chat_id;
        const detail = document.createElement('small'); detail.textContent = `${item.username ? '@' + item.username + ' · ' : ''}Chat ${item.chat_id} · ${item.last_message_at ? 'last message ' + new Date(item.last_message_at * 1000).toLocaleString() : 'no messages yet'}`;
        row.append(identity, remove, detail); root.appendChild(row);
      }
      if (!state.linked_chats?.length) root.innerHTML = '<div class="autonomy-empty">No Telegram chats paired.</div>';
    } catch (error) { status.textContent = `Load failed: ${error.message || error}`; }
  }

  $('telegram-inbound-form').addEventListener('submit', async event => {
    event.preventDefault(); const status = $('telegram-inbound-status'); status.textContent = 'Saving…';
    const body = {enabled:$('telegram-inbound-enabled').checked, reply_channel:$('telegram-inbound-channel').value, remote_approvals_enabled:$('telegram-remote-approvals').checked};
    try { await api('api/telegram-inbound/settings', {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)}); status.textContent = 'Telegram Inbox saved.'; await load(); }
    catch (error) { status.textContent = `Save failed: ${error.message || error}`; }
  });

  $('telegram-generate-code').addEventListener('click', async () => {
    const status = $('telegram-inbound-status'); status.textContent = 'Generating secure code…';
    try {
      const result = await api('api/telegram-inbound/link-code', {method:'POST'});
      const output = $('telegram-pairing-command'); output.hidden = false;
      output.innerHTML = `Send this command to your Telegram bot within 10 minutes:<code></code>`;
      output.querySelector('code').textContent = result.command;
      status.textContent = 'Pairing code ready.';
    } catch (error) { status.textContent = `Pairing failed: ${error.message || error}`; }
  });

  $('telegram-linked-chats').addEventListener('click', async event => {
    const button = event.target.closest('[data-telegram-unlink]'); if (!button) return;
    button.disabled = true;
    try { await api('api/telegram-inbound/unlink', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({chat_id:button.dataset.telegramUnlink})}); await load(); }
    catch (error) { $('telegram-inbound-status').textContent = `Unlink failed: ${error.message || error}`; button.disabled = false; }
  });

  tab.addEventListener('click', load);
  document.getElementById('notification-refresh')?.addEventListener('click', load);
  window.zbranoTelegramInbox = {load};
})();
</script>
'''
    frontend = frontend[:body_close] + telegram_runtime + frontend[body_close:]

    backend = backend.replace('version="0.12.88"', 'version="0.12.89"')
    backend = backend.replace('"version": "0.12.88"', '"version": "0.12.89"')
    frontend = frontend.replace("HUD 0.12.88", "HUD 0.12.89")

    for marker, location in [
        ('version="0.12.89"', backend),
        ('@app.get("/api/telegram-inbound")', backend),
        ('event_type in {"telegram_text", "telegram_command"}', backend),
        ('await asyncio.wait_for(run_jarvis(text, session_id), timeout=120.0)', backend),
        ('remote_approvals_enabled', backend),
        ('id="zbrano-v01289-two-way-telegram"', frontend),
        ('id="telegram-generate-code"', frontend),
        ('HUD 0.12.89', frontend),
    ]:
        require(location, marker, marker)

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
