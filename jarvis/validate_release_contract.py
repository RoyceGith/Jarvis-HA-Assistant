from __future__ import annotations

import json
import re
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPOSITORY_ROOT / "jarvis"
CONFIG = APP_ROOT / "config.yaml"
DOCKERFILE = APP_ROOT / "Dockerfile"
MANIFEST = APP_ROOT / "release_manifest.json"
RUN_SCRIPT = APP_ROOT / "run.sh"
WORKFLOW = REPOSITORY_ROOT / ".github/workflows/build.yaml"


def require(text: str, pattern: str, label: str) -> re.Match[str]:
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        raise RuntimeError(f"Release contract is missing {label}")
    return match


def yaml_scalar(text: str, key: str) -> str:
    match = require(text, rf'^\s*{re.escape(key)}:\s*["\']?([^"\'\n]+)', key)
    return match.group(1).strip()


def yaml_section_keys(text: str, section: str) -> set[str]:
    lines = text.splitlines()
    start = next(
        (index for index, line in enumerate(lines) if line.strip() == f"{section}:"),
        None,
    )
    if start is None:
        raise RuntimeError(f"Release contract is missing {section}")
    keys: set[str] = set()
    for line in lines[start + 1:]:
        if line and not line.startswith(" "):
            break
        match = re.match(r"^  ([a-z0-9_]+):", line)
        if match:
            keys.add(match.group(1))
    return keys


def main() -> None:
    required_files = (CONFIG, DOCKERFILE, MANIFEST, RUN_SCRIPT, WORKFLOW)
    missing = [str(path.relative_to(REPOSITORY_ROOT)) for path in required_files if not path.is_file()]
    if missing:
        raise RuntimeError(f"Release contract files are missing: {', '.join(missing)}")

    config = CONFIG.read_text(encoding="utf-8")
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    run_script = RUN_SCRIPT.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    version = yaml_scalar(config, "version")
    if version != str(manifest.get("version") or ""):
        raise RuntimeError("App metadata and release manifest versions are not aligned")
    if not re.fullmatch(r"0\.13\.\d+", version):
        raise RuntimeError(f"Unexpected release version format: {version}")
    if yaml_scalar(config, "name") != "ZBRANO":
        raise RuntimeError("Home Assistant app name must remain ZBRANO")
    if yaml_scalar(config, "slug") != "jarvis_workshop_assistant":
        raise RuntimeError("Home Assistant app slug changed unexpectedly")
    image = yaml_scalar(config, "image")
    if image != "ghcr.io/roycegith/jarvis-ha-assistant" or image != image.lower():
        raise RuntimeError("Home Assistant image target changed or is not lowercase")

    arch_block = require(config, r"^arch:\s*\n((?:  - .+\n?)+)", "architecture list").group(1)
    architectures = re.findall(r"^  -\s+([a-z0-9_]+)\s*$", arch_block, re.MULTILINE)
    if architectures != ["aarch64"]:
        raise RuntimeError(f"Unsupported release architectures: {architectures}")
    if yaml_scalar(config, "ingress_port") != "8099":
        raise RuntimeError("Ingress port must remain 8099")
    if "exec uvicorn app.main:app --host 0.0.0.0 --port 8099" not in run_script:
        raise RuntimeError("Runtime command does not match the declared ingress port")

    option_keys = yaml_section_keys(config, "options")
    schema_keys = yaml_section_keys(config, "schema")
    if option_keys != schema_keys:
        raise RuntimeError(
            "Home Assistant options/schema mismatch: "
            f"missing schema={sorted(option_keys - schema_keys)}; "
            f"missing defaults={sorted(schema_keys - option_keys)}"
        )
    for secret in (
        "openai_api_key",
        "google_oauth_client_secret",
        "elevenlabs_api_key",
        "grinder_mqtt_password",
    ):
        require(config, rf'^  {secret}:\s*"password"\s*$', f"password schema for {secret}")

    for marker in (
        "ARG BUILD_VERSION",
        "ARG BUILD_ARCH",
        'io.hass.version="${BUILD_VERSION}"',
        'io.hass.arch="${BUILD_ARCH}"',
        "org.opencontainers.image.source=\"https://github.com/RoyceGith/ZBRANO_HA_Assistant\"",
        'CMD ["/run.sh"]',
    ):
        if marker not in dockerfile:
            raise RuntimeError(f"Docker release metadata is missing: {marker}")

    for marker in (
        'path: ./jarvis',
        'context: ./jarvis',
        'arch: ${{ matrix.arch }}',
        'version: ${{ needs.prepare.outputs.version }}',
        "home-assistant/builder/actions/build-image@2026.06.0",
        "home-assistant/builder/actions/publish-multi-arch-manifest@2026.06.0",
        "push: ${{ github.event_name != 'pull_request' }}",
        "if: github.event_name != 'pull_request'",
    ):
        if marker not in workflow:
            raise RuntimeError(f"GitHub release workflow is missing: {marker}")
    if workflow.count("${{ needs.prepare.outputs.version }}") < 3:
        raise RuntimeError("Versioned image and manifest tags are not both configured")
    if workflow.count("latest") < 2:
        raise RuntimeError("Image and manifest latest tags are not both configured")

    print(f"Release contract validated for ZBRANO v{version} ({architectures[0]})")


if __name__ == "__main__":
    main()
