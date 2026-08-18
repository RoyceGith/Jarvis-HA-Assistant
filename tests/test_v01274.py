import ast
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PATCH_PATH = ROOT / "jarvis" / "apply_fast_memory_v01274.py"
PATCH = PATCH_PATH.read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis" / "Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis" / "config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis" / "release_manifest.json").read_text(encoding="utf-8"))


def _memory_namespace(tmp_path: Path) -> dict[str, Any]:
    tree = ast.parse(PATCH)
    value = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "memory_backend" for target in node.targets):
            value = ast.literal_eval(node.value)
            break
    assert value
    namespace: dict[str, Any] = {
        "asyncio": asyncio, "hashlib": hashlib, "json": json, "os": os, "Path": Path,
        "re": re, "sqlite3": sqlite3, "time": time, "Any": Any,
        "load_preferences": lambda: {"fast_memory_enabled": True, "fast_memory_auto_capture": True, "fast_memory_context_items": 10},
        "is_internal_chat_session": lambda session_id: False,
    }
    exec(value, namespace)
    namespace["FAST_MEMORY_PATH"] = tmp_path / "fast-memory.sqlite3"
    return namespace


def test_fast_memory_deduplicates_and_revises(tmp_path):
    memory = _memory_namespace(tmp_path)
    first = memory["upsert_fast_memory"]({
        "kind": "preference", "subject": "Royce", "key": "preferred units",
        "value": "Use Celsius for temperatures", "summary": "Royce prefers Celsius",
        "keywords": ["temperature", "units"], "importance": 4, "confidence": 1,
        "pinned": False, "expires_at": 0,
    })
    confirmed = memory["upsert_fast_memory"]({
        "kind": "preference", "subject": "Royce", "key": "preferred_units",
        "value": "Use Celsius for temperatures", "summary": "Royce prefers Celsius",
        "keywords": ["temperature"], "importance": 4, "confidence": 1,
        "pinned": False, "expires_at": 0,
    })
    updated = memory["upsert_fast_memory"]({
        "kind": "preference", "subject": "Royce", "key": "preferred_units",
        "value": "Use Celsius and metric units", "summary": "Royce prefers metric units",
        "keywords": ["temperature", "metric"], "importance": 4, "confidence": 1,
        "pinned": False, "expires_at": 0,
    })
    assert first["action"] == "created"
    assert confirmed["action"] == "confirmed"
    assert updated["action"] == "updated"
    assert memory["fast_memory_status"]()["total"] == 1
    assert updated["memory"]["revision"] == 2


def test_fast_memory_retrieval_quality_expiry_and_secret_filter(tmp_path):
    memory = _memory_namespace(tmp_path)
    memory["upsert_fast_memory"]({
        "kind": "project", "subject": "Grinder", "key": "current_goal",
        "value": "Find pulse dosing freezes", "summary": "Diagnose pulse dosing freezes",
        "keywords": ["grinder", "freeze", "pulse"], "importance": 5, "confidence": .95,
        "pinned": True, "expires_at": 0,
    })
    memory["upsert_fast_memory"]({
        "kind": "temporary", "subject": "Workshop", "key": "visitor",
        "value": "Visitor is here", "summary": "Temporary visitor context", "keywords": ["visitor"],
        "importance": 3, "confidence": 1, "pinned": False, "expires_at": time.time() - 1,
    })
    blocked = memory["upsert_fast_memory"]({
        "kind": "fact", "subject": "Account", "key": "api_key",
        "value": "api_key=secret-value", "summary": "credential", "keywords": [],
        "importance": 5, "confidence": 1, "pinned": False, "expires_at": 0,
    })
    result = memory["fast_memory_search"]("grinder pulse problem", limit=10, session_id="new")
    assert result["count"] == 1
    assert result["memories"][0]["key"] == "current_goal"
    assert blocked == {"saved": False, "reason": "credential_like_content_blocked"}
    assert memory["fast_memory_status"]()["total"] == 1


def test_fast_memory_chat_ui_backup_and_diagnostics_are_wired():
    for marker in (
        "FAST_MEMORY_PATH", "CREATE TABLE IF NOT EXISTS memory_records", "def fast_memory_context(",
        "async def extract_fast_memory_from_exchange(", '"name": "remember_fast_memory"',
        '@app.get("/api/fast-memory")', '"fast_memory": export_fast_memory()',
        '"Fast Memory operational"', 'id="fast-memory-list"', 'id="zbrano-v01274-fast-memory"',
    ):
        assert marker in PATCH


def test_v01274_release_alignment():
    assert 'version: "0.12.74"' in CONFIG
    assert MANIFEST["version"] == "0.12.74"
    assert "COPY apply_fast_memory_v01274.py" in DOCKER
    assert "python3 ./apply_fast_memory_v01274.py" in DOCKER
    assert DOCKER.index("apply_navigation_icons_v01273.py") < DOCKER.index("apply_fast_memory_v01274.py")
