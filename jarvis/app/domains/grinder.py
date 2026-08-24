from __future__ import annotations

import asyncio
from collections import deque
import contextlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any

import aiomqtt


DATA_DIR = Path("/data")

GRINDER_MONITOR_ENABLED = os.getenv("GRINDER_MONITOR_ENABLED", "false").lower() == "true"

GRINDER_MQTT_HOST = os.getenv("GRINDER_MQTT_HOST", "core-mosquitto")

GRINDER_MQTT_PORT = int(os.getenv("GRINDER_MQTT_PORT", "1883"))

GRINDER_MQTT_USERNAME = os.getenv("GRINDER_MQTT_USERNAME", "")

GRINDER_MQTT_PASSWORD = os.getenv("GRINDER_MQTT_PASSWORD", "")

GRINDER_MQTT_TOPIC_PREFIX = os.getenv("GRINDER_MQTT_TOPIC_PREFIX", "zbrano/grinder").strip("/")

GRINDER_INCIDENTS_PATH = DATA_DIR / "grinder_incidents.json"

GRINDER_BUFFER_SECONDS = 60.0

GRINDER_HEARTBEAT_TIMEOUT = 3.5

GRINDER_MAX_PAYLOAD = 8192

GRINDER_MAX_INCIDENTS = 100

GRINDER_MAX_DEVICES = 8

GRINDER_MONITOR_TASK: asyncio.Task[Any] | None = None

GRINDER_DEVICE_BUFFERS: dict[str, deque[dict[str, Any]]] = {}

GRINDER_DEVICE_STATE: dict[str, dict[str, Any]] = {}

GRINDER_MONITOR_STATE: dict[str, Any] = {
    "enabled": GRINDER_MONITOR_ENABLED,
    "connected": False,
    "last_error": "",
    "last_connected_at": 0.0,
    "messages_received": 0,
}

def _grinder_safe_device_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)[:64]

def _load_grinder_incidents() -> list[dict[str, Any]]:
    if not GRINDER_INCIDENTS_PATH.exists():
        return []
    try:
        payload = json.loads(GRINDER_INCIDENTS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return payload if isinstance(payload, list) else []

def _save_grinder_incidents(incidents: list[dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary = GRINDER_INCIDENTS_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(incidents[-GRINDER_MAX_INCIDENTS:], indent=2), encoding="utf-8")
    temporary.replace(GRINDER_INCIDENTS_PATH)

def _grinder_classification(boot: dict[str, Any], window: list[dict[str, Any]]) -> tuple[str, str]:
    reason = str(boot.get("reset_reason") or boot.get("reason") or "unknown").lower()
    if "brownout" in reason or "power" in reason:
        return "power_or_brownout", "Reset reason indicates power loss or brownout."
    if "watchdog" in reason or "wdt" in reason:
        return "watchdog", "Reset reason indicates a watchdog timeout."
    if "panic" in reason or "exception" in reason:
        return "firmware_panic", "Reset reason indicates a panic or exception."
    recent = [item.get("payload", {}) for item in window[-10:]]
    relay_active = any(bool(item.get("relay_on") or item.get("grinder_running")) for item in recent)
    if relay_active:
        return "abrupt_reset_while_grinding", "The previous heartbeat ended while the grinder relay was active."
    return "unclassified_reboot", "A new boot was observed, but telemetry does not identify a definitive cause."

def _record_grinder_incident(device_id: str, boot: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    window = list(previous.get("frozen_window") or GRINDER_DEVICE_BUFFERS.get(device_id, ()))
    classification, summary = _grinder_classification(boot, window)
    incident = {
        "id": f"{device_id}-{int(time.time() * 1000)}",
        "device_id": device_id,
        "detected_at": time.time(),
        "heartbeat_lost_at": previous.get("heartbeat_lost_at"),
        "reconnected_at": time.time(),
        "classification": classification,
        "summary": summary,
        "previous_boot_id": previous.get("boot_id"),
        "boot": boot,
        "pre_failure_window": window,
    }
    incidents = _load_grinder_incidents()
    incidents.append(incident)
    _save_grinder_incidents(incidents)
    previous["last_incident_id"] = incident["id"]
    previous.pop("frozen_window", None)
    previous["heartbeat_lost_at"] = None
    return incident

def _ingest_grinder_message(topic: str, raw_payload: bytes) -> None:
    if len(raw_payload) > GRINDER_MAX_PAYLOAD:
        GRINDER_MONITOR_STATE["last_error"] = "Dropped oversized grinder telemetry payload"
        return
    parts = topic.split("/")
    prefix_parts = GRINDER_MQTT_TOPIC_PREFIX.split("/")
    if len(parts) != len(prefix_parts) + 2 or parts[:len(prefix_parts)] != prefix_parts:
        return
    device_id = _grinder_safe_device_id(parts[-2])
    kind = parts[-1]
    if not device_id or kind not in {"telemetry", "event", "availability"}:
        return
    now = time.time()
    state = GRINDER_DEVICE_STATE.setdefault(device_id, {
        "device_id": device_id, "online": False, "heartbeat_lost": False,
        "last_seen": 0.0, "boot_id": None, "last_incident_id": None,
        "heartbeat_lost_at": None,
    })
    GRINDER_MONITOR_STATE["messages_received"] += 1
    if kind == "availability":
        value = raw_payload.decode("utf-8", errors="replace").strip().lower()
        state["online"] = value == "online"
        return
    try:
        payload = json.loads(raw_payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        GRINDER_MONITOR_STATE["last_error"] = f"Invalid JSON from {device_id}/{kind}"
        return
    if not isinstance(payload, dict):
        return
    was_lost = bool(state.get("heartbeat_lost"))
    state["last_seen"] = now
    state["heartbeat_lost"] = False
    state["online"] = True
    boot_id = payload.get("boot_id")
    previous_boot_id = state.get("boot_id")
    is_boot = kind == "event" and str(payload.get("event") or "").lower() == "boot"
    if boot_id is not None and previous_boot_id is not None and str(boot_id) != str(previous_boot_id):
        _record_grinder_incident(device_id, payload if is_boot else {"boot_id": boot_id}, state)
        GRINDER_DEVICE_BUFFERS[device_id] = deque()
    elif was_lost:
        state["last_connectivity_gap"] = {
            "lost_at": state.get("heartbeat_lost_at"), "restored_at": now,
        }
        state.pop("frozen_window", None)
        state["heartbeat_lost_at"] = None
    if boot_id is not None:
        state["boot_id"] = boot_id
    state["latest"] = payload
    buffer = GRINDER_DEVICE_BUFFERS.setdefault(device_id, deque())
    buffer.append({"received_at": now, "kind": kind, "payload": payload})
    cutoff = now - GRINDER_BUFFER_SECONDS
    while buffer and float(buffer[0].get("received_at", 0)) < cutoff:
        buffer.popleft()
    if len(GRINDER_DEVICE_BUFFERS) > GRINDER_MAX_DEVICES:
        oldest = min(GRINDER_DEVICE_STATE, key=lambda key: GRINDER_DEVICE_STATE[key].get("last_seen", 0))
        GRINDER_DEVICE_BUFFERS.pop(oldest, None)
        GRINDER_DEVICE_STATE.pop(oldest, None)

async def grinder_monitor_worker() -> None:
    subscriptions = [f"{GRINDER_MQTT_TOPIC_PREFIX}/+/telemetry", f"{GRINDER_MQTT_TOPIC_PREFIX}/+/event", f"{GRINDER_MQTT_TOPIC_PREFIX}/+/availability"]
    while GRINDER_MONITOR_ENABLED:
        try:
            async with aiomqtt.Client(
                hostname=GRINDER_MQTT_HOST,
                port=GRINDER_MQTT_PORT,
                username=GRINDER_MQTT_USERNAME or None,
                password=GRINDER_MQTT_PASSWORD or None,
                identifier="zbrano-grinder-monitor",
                keepalive=30,
                timeout=10,
            ) as client:
                for topic in subscriptions:
                    await client.subscribe(topic, qos=0)
                GRINDER_MONITOR_STATE.update(connected=True, last_error="", last_connected_at=time.time())
                async for message in client.messages:
                    _ingest_grinder_message(str(message.topic), bytes(message.payload))
        except asyncio.CancelledError:
            raise
        except (aiomqtt.MqttError, OSError, ValueError) as exc:
            GRINDER_MONITOR_STATE.update(connected=False, last_error=str(exc)[:300])
            await asyncio.sleep(5)
        finally:
            GRINDER_MONITOR_STATE["connected"] = False

async def grinder_heartbeat_worker() -> None:
    while GRINDER_MONITOR_ENABLED:
        now = time.time()
        for state in GRINDER_DEVICE_STATE.values():
            age = now - float(state.get("last_seen") or 0)
            if state.get("last_seen") and age > GRINDER_HEARTBEAT_TIMEOUT and not state.get("heartbeat_lost"):
                state["online"] = False
                state["heartbeat_lost"] = True
                state["heartbeat_lost_at"] = now
                state["frozen_window"] = list(GRINDER_DEVICE_BUFFERS.get(state["device_id"], ()))
        await asyncio.sleep(1)

async def grinder_monitor_supervisor() -> None:
    await asyncio.gather(grinder_monitor_worker(), grinder_heartbeat_worker())

def grinder_monitor_status() -> dict[str, Any]:
    now = time.time()
    devices = []
    for device_id, state in sorted(GRINDER_DEVICE_STATE.items()):
        devices.append({
            **{key: value for key, value in state.items() if key not in {"latest", "frozen_window"}},
            "heartbeat_age_seconds": round(max(0.0, now - float(state.get("last_seen") or now)), 2),
            "latest": state.get("latest", {}),
            "buffer_samples": len(GRINDER_DEVICE_BUFFERS.get(device_id, ())),
        })
    return {**GRINDER_MONITOR_STATE, "topic_prefix": GRINDER_MQTT_TOPIC_PREFIX, "read_only": True, "devices": devices}

def list_grinder_incidents(limit: int = 20) -> dict[str, Any]:
    incidents = list(reversed(_load_grinder_incidents()))[:max(1, min(int(limit), 100))]
    return {"count": len(incidents), "incidents": [{key: value for key, value in item.items() if key != "pre_failure_window"} for item in incidents]}

def get_grinder_incident(incident_id: str) -> dict[str, Any]:
    for incident in _load_grinder_incidents():
        if incident.get("id") == incident_id:
            return incident
    return {"error": "Grinder incident not found"}

GRINDER_MONITOR_TOOLS: list[dict[str, Any]] = [
    {"type": "function", "name": "get_grinder_diagnostic_status", "description": "Read the grinder diagnostic monitor status and latest telemetry. This never controls the grinder.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}, "strict": True},
    {"type": "function", "name": "list_grinder_incidents", "description": "List recent grinder reboot incidents without the full telemetry windows.", "parameters": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100}}, "required": ["limit"], "additionalProperties": False}, "strict": True},
    {"type": "function", "name": "get_grinder_incident", "description": "Read one grinder incident and its bounded pre-failure telemetry window.", "parameters": {"type": "object", "properties": {"incident_id": {"type": "string"}}, "required": ["incident_id"], "additionalProperties": False}, "strict": True},
]


def start_grinder_monitor() -> bool:
    global GRINDER_MONITOR_TASK
    if not GRINDER_MONITOR_ENABLED:
        return False
    if GRINDER_MONITOR_TASK is None or GRINDER_MONITOR_TASK.done():
        GRINDER_MONITOR_TASK = asyncio.create_task(
            grinder_monitor_supervisor(), name="zbrano-grinder-deep-monitor"
        )
    return True


async def stop_grinder_monitor() -> None:
    global GRINDER_MONITOR_TASK
    if GRINDER_MONITOR_TASK is not None:
        GRINDER_MONITOR_TASK.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await GRINDER_MONITOR_TASK
        GRINDER_MONITOR_TASK = None

