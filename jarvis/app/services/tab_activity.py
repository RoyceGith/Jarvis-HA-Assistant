from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any


_automation_store: Callable[[], dict[str, Any]] = lambda: {}
_list_files: Callable[[Path], list[dict[str, Any]]] = lambda path: []
_shared_file_root = Path("/data/shared_files")
_revision_paths: dict[str, Path] = {}


def configure_tab_activity_service(
    *,
    automation_store_fn: Callable[[], dict[str, Any]],
    list_files_fn: Callable[[Path], list[dict[str, Any]]],
    shared_file_root: Path,
    revision_paths: dict[str, Path],
) -> None:
    global _automation_store, _list_files, _shared_file_root, _revision_paths
    _automation_store = automation_store_fn
    _list_files = list_files_fn
    _shared_file_root = shared_file_root
    _revision_paths = revision_paths


def _tab_activity_revision(path: Path) -> str:
    try:
        stat = path.stat()
        return f"{stat.st_mtime_ns}:{stat.st_size}"
    except OSError:
        return "missing"


def _tab_activity_value_revision(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def tab_activity_revisions() -> dict[str, str]:
    automation_data = _automation_store()
    volatile_watch_fields = {
        "last_observed_state", "last_triggered_at", "trigger_count", "updated_at", "status",
    }
    semantic_automations = [
        {key: value for key, value in item.items() if key not in volatile_watch_fields}
        for item in automation_data.get("automations", [])
    ]
    return {
        "chat": _tab_activity_revision(_revision_paths["chat"]),
        "files": _tab_activity_value_revision([
            {
                key: item.get(key)
                for key in ("file_id", "name", "mime_type", "size", "sha256", "created_at")
            }
            for item in sorted(_list_files(_shared_file_root), key=lambda item: str(item.get("file_id") or ""))
        ]),
        "plugins": ":".join((
            _tab_activity_revision(_revision_paths["plugins"]),
            _tab_activity_revision(_revision_paths["oauth"]),
        )),
        "automations": _tab_activity_value_revision({
            "settings": automation_data.get("settings", {}),
            "automations": semantic_automations,
            "suggestions": automation_data.get("suggestions", []),
            "timeline": automation_data.get("timeline", []),
        }),
        "notifications": _tab_activity_revision(_revision_paths["notifications"]),
        "calendar": _tab_activity_revision(_revision_paths["calendar"]),
        "settings": _tab_activity_revision(_revision_paths["settings"]),
        "developer": _tab_activity_revision(_revision_paths["developer"]),
    }
