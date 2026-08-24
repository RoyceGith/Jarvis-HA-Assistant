from __future__ import annotations

import asyncio
import contextlib
import json
from pathlib import Path
import time
from typing import Any

import httpx

from ..services.mcp_protocol import MCPError
from ..services.release_notes import (
    insert_release_history,
    reconcile_explicit_current_versions,
    reconcile_release_history_backfill,
    release_marker,
    release_sync_content_matches,
    release_sync_write_status,
    render_release_entry,
    upsert_current_release_truth,
)


RUNTIME_VERSION = ""
load_preferences = None
call_workshop_memory_tool = None
call_workshop_memory_tool_uncached = None
workshop_result_error = None


def configure_release_sync_domain(
    *, runtime_version: str, load_preferences_fn, call_tool_fn,
    call_uncached_fn, workshop_result_error_fn,
) -> None:
    global RUNTIME_VERSION, load_preferences, call_workshop_memory_tool
    global call_workshop_memory_tool_uncached, workshop_result_error
    RUNTIME_VERSION = runtime_version
    load_preferences = load_preferences_fn
    call_workshop_memory_tool = call_tool_fn
    call_workshop_memory_tool_uncached = call_uncached_fn
    workshop_result_error = workshop_result_error_fn

RELEASE_MANIFEST_PATH = Path(__file__).resolve().parents[2] / "release_manifest.json"

RELEASE_SYNC_STATE_PATH = Path("/data/zbrano_release_sync.json")

RELEASE_SYNC_TASK: asyncio.Task | None = None

RELEASE_SYNC_WORKER_TIMEOUT_SECONDS = 300

RELEASE_SYNC_STATUS: dict[str, Any] = {
    "state": "pending",
    "version": None,
    "target": "ZBRANO Workshop Assistant/Release and Change Log.md",
    "attempts": 0,
    "last_error": None,
    "last_success_at": None,
    "already_present": False,
    "updated_notes": [],
    "already_current_notes": [],
    "missing_notes": [],
    "failed_notes": [],
    "current_note": None,
    "note_progress": None,
}

def restore_release_sync_status() -> None:
    try:
        stored = json.loads(RELEASE_SYNC_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(stored, dict):
        return
    for key in (
        "version", "state", "last_error", "last_success_at", "already_present",
        "updated_notes", "already_current_notes", "missing_notes", "failed_notes",
        "current_note", "note_progress",
    ):
        if key in stored:
            RELEASE_SYNC_STATUS[key] = stored[key]

restore_release_sync_status()

def load_release_manifest() -> dict[str, Any]:
    try:
        manifest = json.loads(RELEASE_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Release manifest unavailable: {exc}") from exc
    if not isinstance(manifest, dict):
        raise RuntimeError("Release manifest must contain a JSON object")
    version = str(manifest.get("version") or "").strip()
    if version != RUNTIME_VERSION:
        raise RuntimeError(f"Release manifest version {version or 'missing'} does not match runtime {RUNTIME_VERSION}")
    return manifest

def release_sync_enabled() -> bool:
    return bool(load_preferences().get("auto_sync_releases_to_workshop_memory", True))

def release_sync_status() -> dict[str, Any]:
    status = dict(RELEASE_SYNC_STATUS)
    status["enabled"] = release_sync_enabled()
    status["task_active"] = bool(RELEASE_SYNC_TASK and not RELEASE_SYNC_TASK.done())
    if status.get("state") in {"pending", "synchronizing", "retrying"} and not status["task_active"]:
        RELEASE_SYNC_STATUS.update({
            "state": "failed",
            "last_error": status.get("last_error") or "Release synchronization worker stopped before reaching a terminal state",
        })
        status.update(RELEASE_SYNC_STATUS)
        persist_release_sync_status()
    return status

def persist_release_sync_status() -> None:
    payload = {
        "version": RELEASE_SYNC_STATUS.get("version"),
        "state": RELEASE_SYNC_STATUS.get("state"),
        "last_error": RELEASE_SYNC_STATUS.get("last_error"),
        "last_success_at": RELEASE_SYNC_STATUS.get("last_success_at"),
        "already_present": RELEASE_SYNC_STATUS.get("already_present", False),
        "updated_notes": RELEASE_SYNC_STATUS.get("updated_notes", []),
        "already_current_notes": RELEASE_SYNC_STATUS.get("already_current_notes", []),
        "missing_notes": RELEASE_SYNC_STATUS.get("missing_notes", []),
        "failed_notes": RELEASE_SYNC_STATUS.get("failed_notes", []),
        "current_note": RELEASE_SYNC_STATUS.get("current_note"),
        "note_progress": RELEASE_SYNC_STATUS.get("note_progress"),
    }
    try:
        RELEASE_SYNC_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary = RELEASE_SYNC_STATE_PATH.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(RELEASE_SYNC_STATE_PATH)
    except OSError:
        pass

RELEASE_SYNC_PRIMARY_NOTES = (
    "Project Overview.md",
    "Requirements.md",
    "Deployment and Operations.md",
    "Release and Change Log.md",
    "Session Handoff.md",
)

RELEASE_SYNC_AUDIT_NOTES = (
    "Architecture.md",
    "Design Decisions.md",
    "API and Integrations.md",
    "Data and Storage.md",
    "Security and Permissions.md",
    "Test Log.md",
)

async def confirm_release_note_write(
    result: dict[str, Any],
    relative_path: str,
    expected_content: str,
) -> str:
    error = workshop_result_error(result)
    if error:
        raise RuntimeError(error)
    status = release_sync_write_status(result)
    if status in {"created", "replaced", "updated", "ok", "success", "written"}:
        return status

    try:
        verified = await call_workshop_memory_tool_uncached(
            "read_project_note",
            {"relative_path": relative_path},
        )
    except (MCPError, httpx.HTTPError, OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError(
            f"ambiguous write status: {status or 'missing'}; read-back failed: {str(exc)[:180]}"
        ) from exc
    if release_sync_content_matches(verified.get("content"), expected_content):
        return "verified"
    raise RuntimeError(
        f"ambiguous write status: {status or 'missing'}; read-back did not match the intended note"
    )

async def synchronize_release_to_workshop_memory_once() -> dict[str, Any]:
    if not release_sync_enabled():
        RELEASE_SYNC_STATUS.update({"state": "disabled", "last_error": None})
        persist_release_sync_status()
        return release_sync_status()

    manifest = load_release_manifest()
    version = str(manifest["version"])
    project = str(manifest.get("project") or "ZBRANO Workshop Assistant")
    release_note = str(manifest.get("note") or "Release and Change Log.md")
    note_names = tuple(dict.fromkeys(RELEASE_SYNC_PRIMARY_NOTES + RELEASE_SYNC_AUDIT_NOTES))
    updated_notes: list[str] = []
    already_current_notes: list[str] = []
    missing_notes: list[str] = []
    failed_notes: list[str] = []
    release_history_present = False
    RELEASE_SYNC_STATUS.update({
        "state": "synchronizing",
        "version": version,
        "target": f"{project}/canonical release truth",
        "last_error": None,
        "already_present": False,
        "updated_notes": [],
        "already_current_notes": [],
        "missing_notes": [],
        "failed_notes": [],
        "current_note": None,
        "note_progress": f"0/{len(note_names)}",
    })

    for note_index, note_name in enumerate(note_names, start=1):
        RELEASE_SYNC_STATUS.update({
            "current_note": note_name,
            "note_progress": f"{note_index}/{len(note_names)}",
        })
        relative_path = f"{project}/{note_name}"
        try:
            current = await call_workshop_memory_tool("read_project_note", {"relative_path": relative_path})
            content = str(current.get("content") or "")
        except (MCPError, httpx.HTTPError, OSError, RuntimeError, ValueError) as exc:
            if note_name not in RELEASE_SYNC_PRIMARY_NOTES and "not found" in str(exc).casefold():
                missing_notes.append(note_name)
                continue
            failed_notes.append(f"{note_name}: read failed: {str(exc)[:240]}")
            continue

        updated = reconcile_explicit_current_versions(content, version)
        if note_name == release_note:
            release_history_present = release_marker(version) in content
            updated = upsert_current_release_truth(updated, manifest, release_log=True)
            updated = reconcile_release_history_backfill(updated, manifest)
            updated = insert_release_history(updated, render_release_entry(manifest))
        elif note_name in RELEASE_SYNC_PRIMARY_NOTES:
            updated = upsert_current_release_truth(updated, manifest, release_log=False)

        if updated == content:
            already_current_notes.append(note_name)
            continue
        try:
            result = await call_workshop_memory_tool(
                "write_project_note",
                {
                    "relative_path": relative_path,
                    "content": updated,
                    "mode": "replace",
                    "create_folders": False,
                },
            )
            await confirm_release_note_write(result, relative_path, updated)
            updated_notes.append(note_name)
        except (MCPError, httpx.HTTPError, OSError, RuntimeError, ValueError) as exc:
            failed_notes.append(f"{note_name}: write failed: {str(exc)[:240]}")

    RELEASE_SYNC_STATUS.update({
        "updated_notes": updated_notes,
        "already_current_notes": already_current_notes,
        "missing_notes": missing_notes,
        "failed_notes": failed_notes,
        "already_present": release_history_present,
    })
    if failed_notes:
        raise RuntimeError("Canonical release reconciliation failed: " + " | ".join(failed_notes))
    RELEASE_SYNC_STATUS.update({
        "state": "synchronized",
        "last_success_at": time.time(),
        "last_error": None,
        "current_note": None,
        "note_progress": f"{len(note_names)}/{len(note_names)}",
    })
    persist_release_sync_status()
    return release_sync_status()

async def _release_sync_worker_attempts() -> None:
    delays = (0, 10, 30, 120)
    for attempt, delay in enumerate(delays, start=1):
        if delay:
            await asyncio.sleep(delay)
        RELEASE_SYNC_STATUS["attempts"] = attempt
        try:
            await synchronize_release_to_workshop_memory_once()
            return
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            RELEASE_SYNC_STATUS.update({
                "state": "retrying" if attempt < len(delays) else "failed",
                "last_error": str(exc)[:1000],
            })
            persist_release_sync_status()

async def release_sync_worker() -> None:
    try:
        await asyncio.wait_for(
            _release_sync_worker_attempts(),
            timeout=RELEASE_SYNC_WORKER_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        RELEASE_SYNC_STATUS.update({
            "state": "failed",
            "last_error": f"Release synchronization exceeded {RELEASE_SYNC_WORKER_TIMEOUT_SECONDS} seconds",
        })
        persist_release_sync_status()

def schedule_release_sync() -> asyncio.Task | None:
    global RELEASE_SYNC_TASK
    if not release_sync_enabled():
        RELEASE_SYNC_STATUS.update({"state": "disabled", "last_error": None})
        persist_release_sync_status()
        return None
    if RELEASE_SYNC_TASK is None or RELEASE_SYNC_TASK.done():
        RELEASE_SYNC_TASK = asyncio.create_task(release_sync_worker(), name="zbrano-release-memory-sync")
    return RELEASE_SYNC_TASK


async def stop_release_sync() -> None:
    global RELEASE_SYNC_TASK
    if RELEASE_SYNC_TASK is not None:
        RELEASE_SYNC_TASK.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await RELEASE_SYNC_TASK
        RELEASE_SYNC_TASK = None


def cancel_release_sync() -> None:
    if RELEASE_SYNC_TASK is not None and not RELEASE_SYNC_TASK.done():
        RELEASE_SYNC_TASK.cancel()

