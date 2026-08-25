from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PLUGIN_REGISTRY_PATH = Path("/data/plugins/registry.json")
PLUGIN_SECRETS_PATH = Path("/data/plugins/secrets.json")


def _plugin_load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _plugin_save(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.chmod(0o600)
    temporary.replace(path)
    path.chmod(0o600)


def plugin_registry() -> dict[str, Any]:
    return _plugin_load(PLUGIN_REGISTRY_PATH)


def plugin_secrets() -> dict[str, Any]:
    return _plugin_load(PLUGIN_SECRETS_PATH)
