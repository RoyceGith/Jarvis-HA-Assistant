import json
import re
from pathlib import Path


ROOT = Path("/opt/jarvis")
CONFIG = ROOT / "config.yaml"
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"
MANIFEST = ROOT / "release_manifest.json"


def require_version(text: str, pattern: str, label: str) -> str:
    match = re.search(pattern, text)
    if not match:
        raise RuntimeError(f"Release manifest validation could not find {label}")
    return match.group(1)


def main() -> None:
    config = CONFIG.read_text(encoding="utf-8")
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    versions = {
        "config": require_version(config, r'(?m)^version:\s*"([^"]+)"', "config version"),
        "backend": require_version(backend, r'version="([^"]+)"', "backend version"),
        "frontend": require_version(frontend, r'HUD\s+([0-9]+\.[0-9]+\.[0-9]+)', "HUD version"),
        "manifest": str(manifest.get("version") or ""),
    }
    if len(set(versions.values())) != 1:
        raise RuntimeError(f"Release versions are not aligned: {versions}")

    if manifest.get("project") != "ZBRANO Workshop Assistant":
        raise RuntimeError("Release manifest project must be ZBRANO Workshop Assistant")
    if manifest.get("note") != "Release and Change Log.md":
        raise RuntimeError("Release manifest note must be Release and Change Log.md")
    for field in ("summary", "features", "fixes", "validation"):
        if not manifest.get(field):
            raise RuntimeError(f"Release manifest field is required: {field}")

    print(f"Release manifest validated for ZBRANO v{versions['manifest']}")


if __name__ == "__main__":
    main()
