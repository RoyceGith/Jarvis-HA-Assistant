from __future__ import annotations

import asyncio
import contextlib
import json
from pathlib import Path
import time
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed

from ..schemas import NotificationTestRequest


TELEGRAM_INBOUND_PATH = Path("/data/telegram_inbound.json")
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

plugin_load = None
plugin_save = None
ha_ws = None
notification_store = None
test_notification_channel = None
run_jarvis = None
SUPERVISOR_TOKEN = ""
HA_WS_URL = ""


def configure_telegram_inbound_domain(
    *, plugin_load_fn, plugin_save_fn, ha_client, notification_store_fn,
    notification_test_fn, run_jarvis_fn, supervisor_token: str, ha_ws_url: str,
) -> None:
    global plugin_load, plugin_save, ha_ws, notification_store
    global test_notification_channel, run_jarvis, SUPERVISOR_TOKEN, HA_WS_URL
    plugin_load = plugin_load_fn
    plugin_save = plugin_save_fn
    ha_ws = ha_client
    notification_store = notification_store_fn
    test_notification_channel = notification_test_fn
    run_jarvis = run_jarvis_fn
    SUPERVISOR_TOKEN = supervisor_token
    HA_WS_URL = ha_ws_url


def telegram_inbound_store() -> dict[str, Any]:
    data = plugin_load(TELEGRAM_INBOUND_PATH) or {}
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


def save_telegram_inbound(data: dict[str, Any]) -> None:
    data["linked_chats"] = list(data.get("linked_chats") or [])[:20]
    plugin_save(TELEGRAM_INBOUND_PATH, data)


def telegram_public_status() -> dict[str, Any]:
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
                {"chat_id": int(chat_id), "message": part},
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


def telegram_event_fields(event_type: str, data: dict[str, Any]) -> tuple[str, str, str, str]:
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
        text = (
            " ".join([command, *[str(value) for value in args]]).strip()
            if isinstance(args, list)
            else " ".join([command, str(args or "")]).strip()
        )
    else:
        text = str(data.get("text") or "").strip()
    return chat_id, text, username, display_name


def telegram_event_duplicate(event_type: str, data: dict[str, Any], chat_id: str, text: str) -> bool:
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
            save_telegram_inbound(data)
            await _telegram_send(chat_id, "Started a new ZBRANO conversation. Your earlier Telegram chat remains in Conversations.")
            return
        if normalized == "/unlink":
            data["linked_chats"] = [item for item in data["linked_chats"] if str(item.get("chat_id")) != chat_id]
            save_telegram_inbound(data)
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
        save_telegram_inbound(data)
        try:
            result = await asyncio.wait_for(run_jarvis(text, session_id), timeout=120.0)
            reply = str(result.get("reply") or "ZBRANO completed the request without a text response.")
            await _telegram_send(chat_id, reply)
        except asyncio.TimeoutError:
            await _telegram_send(chat_id, "The request exceeded two minutes and was stopped. No automatic retry was started.")
        except Exception as exc:
            await _telegram_send(chat_id, f"I could not complete that request: {str(exc)[:500]}")


async def _telegram_handle_event(event_type: str, data: dict[str, Any]) -> None:
    chat_id, text, username, display_name = telegram_event_fields(event_type, data)
    if not chat_id or not text or telegram_event_duplicate(event_type, data, chat_id, text):
        return
    TELEGRAM_INBOUND_STATUS["last_event_at"] = time.time()
    store = telegram_inbound_store()
    linked = next((item for item in store["linked_chats"] if str(item.get("chat_id")) == chat_id), None)
    normalized = " ".join(text.strip().split())
    pairing = store.get("pairing") or {}
    expected = str(pairing.get("code") or "")
    supplied = normalized[6:].strip().upper() if normalized.lower().startswith("/link ") else ""
    if not linked and expected and time.time() < float(pairing.get("expires_at") or 0.0) and supplied == expected:
        store["linked_chats"].append({
            "chat_id": chat_id,
            "display_name": display_name,
            "username": username,
            "linked_at": time.time(),
            "last_message_at": time.time(),
            "session_id": f"telegram-{chat_id}",
        })
        store["pairing"] = {}
        save_telegram_inbound(store)
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


async def start_telegram_inbound() -> None:
    global TELEGRAM_INBOUND_TASK
    if TELEGRAM_INBOUND_TASK is None or TELEGRAM_INBOUND_TASK.done():
        TELEGRAM_INBOUND_TASK = asyncio.create_task(telegram_inbound_worker(), name="zbrano-telegram-inbound")


async def stop_telegram_inbound() -> None:
    global TELEGRAM_INBOUND_TASK
    if TELEGRAM_INBOUND_TASK is not None:
        TELEGRAM_INBOUND_TASK.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await TELEGRAM_INBOUND_TASK
        TELEGRAM_INBOUND_TASK = None
