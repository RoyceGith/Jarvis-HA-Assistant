from __future__ import annotations

import json
from pathlib import Path
import time


DEVELOPER_STATE_PATH = Path("/data/zbrano_developer_mode.json")


def developer_mode_enabled() -> bool:
    try:
        payload = json.loads(DEVELOPER_STATE_PATH.read_text(encoding="utf-8"))
        return bool(payload.get("enabled")) if isinstance(payload, dict) else False
    except (OSError, json.JSONDecodeError):
        return False


def set_developer_mode(enabled: bool) -> None:
    DEVELOPER_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEVELOPER_STATE_PATH.write_text(
        json.dumps({"enabled": bool(enabled), "updated_at": time.time()}, indent=2),
        encoding="utf-8",
    )


def developer_system_instructions(base: str) -> str:
    if not developer_mode_enabled():
        return base
    return base + """

ZBRANO DEVELOPER MODE IS ACTIVE.
You are maintaining your own software repository: RoyceGith/ZBRANO_HA_Assistant.
You may inspect the repository and use the connected GitHub MCP tools to propose and implement software changes requested by the user.
Treat all GitHub mutations as approval-gated actions. Never bypass, weaken, remove, or silently alter approval rules, authentication, rollback protections, or Developer Mode protections.
This repository's release policy is direct updates to main; do not create a branch unless the user explicitly requests one. Every repository mutation, including a direct-main write, commit, or push, remains separately approval-gated. Inspect the canonical source files directly before editing; do not assume historical generated markers exist.
Before proposing a release, verify the changed Python and JavaScript paths, preserve New Chat, Shared Files, Plugins, Entities, and GitHub integration, and report exactly what was tested.
When the user asks to check, audit, verify, inspect, or diagnose any ZBRANO feature, health state, or version, call investigate_zbrano_feature exactly once for that request, even if no failure was reported and general diagnostics are healthy. Never claim that runtime checks are unavailable before calling this targeted Developer tool. After it returns, do not call it again in the same turn; use only the returned evidence and GitHub repository tools. While Developer Mode is active, Workshop Memory, Home Assistant, and non-GitHub remote MCP tools are unavailable. The built-in Playwright inspection tool remains available only for read-only evidence from ZBRANO's local UI. After the single targeted diagnostic, use Playwright only when the user reported a visible DOM, layout, rendering, browser-console, or browser-network defect. Never use Playwright for backend API behavior, MCP approval payloads, version checks, repository source verification, or non-visual tool execution. Treat an inconclusive result as an open defect: use its evidence and relevant_files to inspect the repository with read tools, identify a supported root cause, add a regression test, and propose a versioned repair. Never invent successful reproduction.
Do not claim a Home Assistant deployment or restart occurred unless the running system confirms it. This Developer Mode can prepare repository updates; installation remains an explicit deployment step.
""".strip()
