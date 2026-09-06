from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping


OWNER_EXTENSIONS_PATH = Path("/data/zbrano_owner_extensions.json")
OWNER_EXTENSIONS_VERSION = 1

_GRINDER_DEFAULTS: dict[str, Any] = {
    "enabled": False,
    "mqtt_host": "core-mosquitto",
    "mqtt_port": 1883,
    "mqtt_username": "",
    "mqtt_password": "",
    "mqtt_topic_prefix": "zbrano/grinder",
}


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _bounded_text(value: Any, default: str, maximum: int) -> str:
    normalized = str(value if value is not None else default).strip()
    return (normalized or default)[:maximum]


def _mqtt_port(value: Any) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError):
        return int(_GRINDER_DEFAULTS["mqtt_port"])
    return port if 1 <= port <= 65535 else int(_GRINDER_DEFAULTS["mqtt_port"])


def _normalize_grinder(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    source = payload if isinstance(payload, Mapping) else {}
    return {
        "enabled": _as_bool(source.get("enabled", _GRINDER_DEFAULTS["enabled"])),
        "mqtt_host": _bounded_text(source.get("mqtt_host"), str(_GRINDER_DEFAULTS["mqtt_host"]), 253),
        "mqtt_port": _mqtt_port(source.get("mqtt_port", _GRINDER_DEFAULTS["mqtt_port"])),
        "mqtt_username": _bounded_text(source.get("mqtt_username"), "", 256),
        "mqtt_password": str(source.get("mqtt_password") or "")[:1024],
        "mqtt_topic_prefix": _bounded_text(
            source.get("mqtt_topic_prefix"), str(_GRINDER_DEFAULTS["mqtt_topic_prefix"]), 256
        ).strip("/"),
    }


def _read_document(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _legacy_grinder_environment(environ: Mapping[str, str]) -> dict[str, Any]:
    return _normalize_grinder({
        "enabled": environ.get("GRINDER_MONITOR_ENABLED", "false"),
        "mqtt_host": environ.get("GRINDER_MQTT_HOST", _GRINDER_DEFAULTS["mqtt_host"]),
        "mqtt_port": environ.get("GRINDER_MQTT_PORT", _GRINDER_DEFAULTS["mqtt_port"]),
        "mqtt_username": environ.get("GRINDER_MQTT_USERNAME", ""),
        "mqtt_password": environ.get("GRINDER_MQTT_PASSWORD", ""),
        "mqtt_topic_prefix": environ.get("GRINDER_MQTT_TOPIC_PREFIX", _GRINDER_DEFAULTS["mqtt_topic_prefix"]),
    })


def grinder_extension_config(
    *, path: Path = OWNER_EXTENSIONS_PATH, environ: Mapping[str, str] | None = None
) -> dict[str, Any]:
    document = _read_document(path)
    extensions = document.get("extensions")
    if isinstance(extensions, dict) and isinstance(extensions.get("grinder_monitor"), dict):
        return _normalize_grinder(extensions["grinder_monitor"])
    return _legacy_grinder_environment(environ if environ is not None else os.environ)


def migrate_legacy_grinder_environment(
    *, path: Path = OWNER_EXTENSIONS_PATH, environ: Mapping[str, str] | None = None
) -> bool:
    source = environ if environ is not None else os.environ
    if "GRINDER_MONITOR_ENABLED" not in source:
        return False
    grinder = _legacy_grinder_environment(source)
    customized = grinder["enabled"] or any(
        grinder[key] != _GRINDER_DEFAULTS[key]
        for key in ("mqtt_host", "mqtt_port", "mqtt_username", "mqtt_password", "mqtt_topic_prefix")
    )
    if not customized and not path.exists():
        return False

    document = _read_document(path)
    extensions = document.get("extensions")
    if not isinstance(extensions, dict):
        extensions = {}
    extensions["grinder_monitor"] = grinder
    document = {**document, "version": OWNER_EXTENSIONS_VERSION, "extensions": extensions}

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    try:
        temporary.chmod(0o600)
    except OSError:
        pass
    temporary.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return True


def main() -> None:
    if len(os.sys.argv) != 2 or os.sys.argv[1] != "migrate":
        raise SystemExit("Usage: python -m app.services.owner_extensions migrate")
    migrated = migrate_legacy_grinder_environment()
    print("Owner extension configuration migrated" if migrated else "No owner extension migration needed")


if __name__ == "__main__":
    main()
