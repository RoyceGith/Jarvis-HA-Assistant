#!/usr/bin/env python3
"""Validate the public-core boundary before ZBRANO image publication."""

from __future__ import annotations

from pathlib import Path
import struct
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
    "jarvis/translations/en.yaml",
    "jarvis/translations/el.yaml",
    "jarvis/translations/it.yaml",
    "jarvis/translations/fr.yaml",
    "jarvis/app/static/index.html",
    "jarvis/app/static/js/automations/workspace.js",
)
PUBLIC_DISTRIBUTION_FILES = {
    "README.md",
    "repository.yaml",
    "jarvis/README.md",
    "jarvis/CHANGELOG.md",
    "jarvis/config.yaml",
    "jarvis/translations/en.yaml",
    "jarvis/translations/el.yaml",
    "jarvis/translations/it.yaml",
    "jarvis/translations/fr.yaml",
    "jarvis/icon.png",
    "jarvis/logo.png",
    "hacs.json",
    "custom_components/zbrano/__init__.py",
    "custom_components/zbrano/api.py",
    "custom_components/zbrano/config_flow.py",
    "custom_components/zbrano/const.py",
    "custom_components/zbrano/conversation.py",
    "custom_components/zbrano/manifest.json",
    "custom_components/zbrano/strings.json",
    "custom_components/zbrano/translations/en.json",
    "custom_components/zbrano/translations/el.json",
    "custom_components/zbrano/translations/it.json",
    "custom_components/zbrano/translations/fr.json",
}
PUBLIC_PRESENTATION_ASSETS = {
    "jarvis/icon.png": (128, 128),
    "jarvis/logo.png": (511, 120),
}


def tracked_paths(root: Path = ROOT) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def validate(paths: list[str] | None = None, *, root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    root = Path(root).resolve()
    paths = tracked_paths(root) if paths is None else paths
    normalized_paths = {path.replace("\\", "/") for path in paths}
    for path in paths:
        normalized = path.replace("\\", "/")
        name = Path(normalized).name.lower()
        if normalized.startswith(FORBIDDEN_PREFIXES):
            errors.append(f"private path is tracked: {normalized}")
        if name in FORBIDDEN_NAMES or name.endswith(FORBIDDEN_SUFFIXES):
            errors.append(f"secret-bearing filename is tracked: {normalized}")

    thin_distribution = "jarvis/config.yaml" in normalized_paths and ".github/workflows/build.yaml" not in normalized_paths
    if thin_distribution:
        for path in sorted(PUBLIC_DISTRIBUTION_FILES - normalized_paths):
            errors.append(f"required public distribution file is missing: {path}")
        for path in sorted(normalized_paths - PUBLIC_DISTRIBUTION_FILES):
            errors.append(f"unexpected file in thin public distribution: {path}")
    else:
        ignore_text = (root / ".gitignore").read_text(encoding="utf-8")
        for marker in REQUIRED_IGNORES:
            if marker not in ignore_text:
                errors.append(f"missing public-boundary ignore rule: {marker}")

    repository = (root / "repository.yaml").read_text(encoding="utf-8")
    if "name: ZBRANO" not in repository:
        errors.append("repository.yaml must use the ZBRANO product name")
    if "https://github.com/ZBRANO-HOME/ZBRANO_HA_Assistant" not in repository:
        errors.append("repository.yaml must point to the canonical public repository")

    for relative, expected_size in PUBLIC_PRESENTATION_ASSETS.items():
        candidate = root / relative
        if not candidate.is_file():
            errors.append(f"required public presentation asset is missing: {relative}")
            continue
        payload = candidate.read_bytes()
        if len(payload) > 100_000:
            errors.append(f"public presentation asset is too large: {relative}")
            continue
        if len(payload) < 26 or payload[:8] != b"\x89PNG\r\n\x1a\n" or payload[12:16] != b"IHDR":
            errors.append(f"public presentation asset is not a valid PNG: {relative}")
            continue
        dimensions = struct.unpack(">II", payload[16:24])
        if dimensions != expected_size:
            errors.append(
                f"public presentation asset has size {dimensions[0]}x{dimensions[1]}, "
                f"expected {expected_size[0]}x{expected_size[1]}: {relative}"
            )
        if payload[25] not in {4, 6}:
            errors.append(f"public presentation asset must preserve transparency: {relative}")

    for relative in PRODUCT_DEFAULT_FILES:
        candidate = root / relative
        if not candidate.is_file():
            if thin_distribution and relative in PUBLIC_DISTRIBUTION_FILES:
                errors.append(f"required product metadata is missing: {relative}")
            continue
        content = candidate.read_text(encoding="utf-8").lower()
        for personal in PERSONAL_DEFAULTS:
            if personal in content:
                errors.append(f"personal default {personal!r} found in {relative}")
    return errors


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT
    errors = validate(root=root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Public repository boundary validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
