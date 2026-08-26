#!/usr/bin/env python3
"""Validate the public-core boundary before ZBRANO image publication."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
FORBIDDEN_PREFIXES = (
    ".local-",
    "private-services/",
    "commercial-services/",
    "Workshop-Memory-HA-App/",
)
FORBIDDEN_NAMES = {
    ".env",
    "secrets.yaml",
    "credentials.json",
}
FORBIDDEN_SUFFIXES = (".pem", ".key", ".p12", ".pfx")
REQUIRED_IGNORES = (
    ".local-*/",
    ".env",
    "secrets.yaml",
    "*.pem",
    "/private-services/",
    "/commercial-services/",
    "/Workshop-Memory-HA-App/",
    "/*HANDOFF*.txt",
)
PERSONAL_DEFAULTS = (
    "person.royce",
    "device_tracker.royce",
    "factory workshop",
)
PRODUCT_DEFAULT_FILES = (
    "jarvis/config.yaml",
    "jarvis/app/static/index.html",
    "jarvis/app/static/js/automations/workspace.js",
)


def tracked_paths() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def validate(paths: list[str] | None = None) -> list[str]:
    errors: list[str] = []
    paths = tracked_paths() if paths is None else paths
    for path in paths:
        normalized = path.replace("\\", "/")
        name = Path(normalized).name.lower()
        if normalized.startswith(FORBIDDEN_PREFIXES):
            errors.append(f"private path is tracked: {normalized}")
        if name in FORBIDDEN_NAMES or name.endswith(FORBIDDEN_SUFFIXES):
            errors.append(f"secret-bearing filename is tracked: {normalized}")

    ignore_text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for marker in REQUIRED_IGNORES:
        if marker not in ignore_text:
            errors.append(f"missing public-boundary ignore rule: {marker}")

    repository = (ROOT / "repository.yaml").read_text(encoding="utf-8")
    if "name: ZBRANO" not in repository:
        errors.append("repository.yaml must use the ZBRANO product name")
    if "https://github.com/RoyceGith/Jarvis-HA-Assistant" not in repository:
        errors.append("repository.yaml must point to the canonical public repository")

    for relative in PRODUCT_DEFAULT_FILES:
        content = (ROOT / relative).read_text(encoding="utf-8").lower()
        for personal in PERSONAL_DEFAULTS:
            if personal in content:
                errors.append(f"personal default {personal!r} found in {relative}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Public repository boundary validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
