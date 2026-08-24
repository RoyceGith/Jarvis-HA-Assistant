from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any, Callable

import websockets
from websockets.exceptions import ConnectionClosed


class HomeAssistantWebSocketClient:
    """Persistent Home Assistant WebSocket client with state cache and REST fallback."""

    def __init__(self, url: str, token: str, state_changed_callback: Callable[[dict[str, Any]], None]) -> None:
        self.url = url
        self.token = token
        self.state_changed_callback = state_changed_callback
        self.websocket: Any | None = None
        self.reader_task: asyncio.Task[None] | None = None
        self.connect_lock = asyncio.Lock()
        self.send_lock = asyncio.Lock()
        self.pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self.next_id = 1
        self.state_cache: dict[str, dict[str, Any]] = {}
        self.connected = False
        self.last_error: str | None = None
        self.subscription_id: int | None = None

    async def connect(self) -> None:
        if self.connected and self.websocket is not None:
            return
        if not self.token:
            raise RuntimeError("Home Assistant API token unavailable")

        async with self.connect_lock:
            if self.connected and self.websocket is not None:
                return
            await self._disconnect()

            try:
                ws = await websockets.connect(
                    self.url,
                    open_timeout=10,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                    max_size=4 * 1024 * 1024,
                )
                hello = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                if hello.get("type") != "auth_required":
                    await ws.close()
                    raise RuntimeError(
                        f"Unexpected Home Assistant WebSocket greeting: {hello.get('type')}"
                    )

                await ws.send(json.dumps({"type": "auth", "access_token": self.token}))
                auth = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                if auth.get("type") != "auth_ok":
                    await ws.close()
                    raise RuntimeError(
                        auth.get("message") or "Home Assistant WebSocket authentication failed"
                    )

                self.websocket = ws
                self.connected = True
                self.last_error = None
                self.reader_task = asyncio.create_task(
                    self._reader_loop(),
                    name="jarvis-ha-websocket-reader",
                )

                states_result = await self.command({"type": "get_states"}, ensure=False)
                states = states_result.get("result") or []
                self.state_cache = {
                    state["entity_id"]: state
                    for state in states
                    if isinstance(state, dict) and state.get("entity_id")
                }

                subscription = await self.command(
                    {"type": "subscribe_events", "event_type": "state_changed"},
                    ensure=False,
                )
                self.subscription_id = subscription.get("id")
            except Exception as exc:
                self.last_error = str(exc)
                await self._disconnect()
                raise RuntimeError(
                    f"Home Assistant WebSocket connection failed: {exc}"
                ) from exc

    async def _reader_loop(self) -> None:
        try:
            assert self.websocket is not None
            async for raw in self.websocket:
                message = json.loads(raw)
                message_type = message.get("type")

                if message_type == "result":
                    future = self.pending.pop(int(message.get("id", -1)), None)
                    if future and not future.done():
                        future.set_result(message)
                    continue

                if message_type == "event":
                    event = message.get("event") or {}
                    if event.get("event_type") != "state_changed":
                        continue
                    data = event.get("data") or {}
                    entity_id = data.get("entity_id")
                    new_state = data.get("new_state")
                    if not entity_id:
                        continue
                    if new_state is None:
                        self.state_cache.pop(entity_id, None)
                    elif isinstance(new_state, dict):
                        self.state_cache[entity_id] = new_state
                    self.state_changed_callback(event)
        except asyncio.CancelledError:
            raise
        except (ConnectionClosed, OSError, json.JSONDecodeError) as exc:
            self.last_error = str(exc)
        finally:
            self.connected = False
            error = RuntimeError(
                f"Home Assistant WebSocket disconnected: {self.last_error or 'connection closed'}"
            )
            for future in self.pending.values():
                if not future.done():
                    future.set_exception(error)
            self.pending.clear()

    async def command(
        self,
        payload: dict[str, Any],
        timeout: float = 15.0,
        ensure: bool = True,
    ) -> dict[str, Any]:
        if ensure:
            await self.connect()
        if not self.connected or self.websocket is None:
            raise RuntimeError("Home Assistant WebSocket is not connected")

        loop = asyncio.get_running_loop()
        async with self.send_lock:
            command_id = self.next_id
            self.next_id += 1
            future: asyncio.Future[dict[str, Any]] = loop.create_future()
            self.pending[command_id] = future
            message = {"id": command_id, **payload}
            try:
                await self.websocket.send(json.dumps(message))
            except Exception:
                self.pending.pop(command_id, None)
                self.connected = False
                raise

        try:
            response = await asyncio.wait_for(future, timeout=timeout)
        except Exception:
            self.pending.pop(command_id, None)
            raise

        if not response.get("success"):
            error = response.get("error") or {}
            raise RuntimeError(
                error.get("message")
                or error.get("code")
                or "Home Assistant WebSocket command failed"
            )
        return response

    async def get_state(self, entity_id: str) -> dict[str, Any] | None:
        await self.connect()
        return self.state_cache.get(entity_id)

    async def call_service(
        self,
        domain: str,
        service: str,
        service_data: dict[str, Any],
    ) -> dict[str, Any]:
        return await self.command(
            {
                "type": "call_service",
                "domain": domain,
                "service": service,
                "service_data": service_data,
                "return_response": False,
            }
        )

    async def wait_for_state(
        self,
        entity_id: str,
        expected: str,
        timeout: float = 5.0,
    ) -> dict[str, Any] | None:
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            state = self.state_cache.get(entity_id)
            if state and state.get("state") == expected:
                return state
            await asyncio.sleep(0.05)
        return self.state_cache.get(entity_id)

    async def _disconnect(self) -> None:
        self.connected = False
        if self.reader_task and self.reader_task is not asyncio.current_task():
            self.reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.reader_task
        self.reader_task = None

        if self.websocket is not None:
            with contextlib.suppress(Exception):
                await self.websocket.close()
        self.websocket = None
        self.subscription_id = None

    async def close(self) -> None:
        await self._disconnect()

    def status(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "cached_entities": len(self.state_cache),
            "subscription_active": self.subscription_id is not None,
            "last_error": self.last_error,
        }
