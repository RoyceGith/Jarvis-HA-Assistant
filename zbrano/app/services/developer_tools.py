from __future__ import annotations

from collections.abc import Callable
from typing import Any


_developer_mode_enabled: Callable[[], bool] = lambda: False


def configure_developer_tools(*, developer_mode_enabled_fn: Callable[[], bool]) -> None:
    global _developer_mode_enabled
    _developer_mode_enabled = developer_mode_enabled_fn


def developer_runtime_tools() -> list[dict[str, Any]]:
    if not _developer_mode_enabled():
        return []
    return [{
        "type": "function",
        "name": "investigate_zbrano_feature",
        "description": (
            "Run one targeted, read-only ZBRANO feature check. "
            "Use this for check, audit, verify, health, version, or broken-feature requests, even when "
            "general diagnostics are healthy. Return evidence and fault boundaries before proposing code changes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "feature": {
                    "type": "string",
                    "description": "Feature name such as shared_files, attachments, new_chat, plugin_catalog, plugins, entities, settings, voice, workshop_memory, or developer.",
                },
                "symptom": {
                    "type": "string",
                    "description": "Exact observed behavior, reproduction steps, and expected behavior supplied by the user.",
                },
            },
            "required": ["feature", "symptom"],
            "additionalProperties": False,
        },
        "strict": True,
    }]
