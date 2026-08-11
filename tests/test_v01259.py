import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_release_bump_v01259.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_v01259_release_version_and_build_order():
    assert "COPY apply_release_bump_v01259.py ./apply_release_bump_v01259.py" in DOCKER
    assert DOCKER.index("python3 ./apply_plugin_settings_visibility_v01258.py") < DOCKER.index("python3 ./apply_release_bump_v01259.py")
    assert DOCKER.index("python3 ./apply_release_bump_v01259.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.59"' in CONFIG
    assert MANIFEST["version"] == "0.12.59"
    assert "ZBRANO v0.12.59" in README
    assert 'version="0.12.59"' in PATCH
    assert "HUD 0.12.59" in PATCH
