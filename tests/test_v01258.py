import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_plugin_settings_visibility_v01258.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_v01258_release_version_and_build_order():
    assert "COPY apply_plugin_settings_visibility_v01258.py ./apply_plugin_settings_visibility_v01258.py" in DOCKER
    assert DOCKER.index("python3 ./apply_gmail_direct_v01257.py") < DOCKER.index("python3 ./apply_plugin_settings_visibility_v01258.py")
    assert DOCKER.index("python3 ./apply_plugin_settings_visibility_v01258.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.58"' in CONFIG
    assert MANIFEST["version"] == "0.12.58"
    assert "ZBRANO v0.12.58" in README
    assert 'version="0.12.58"' in PATCH
    assert "HUD 0.12.58" in PATCH


def test_v01258_installed_plugin_settings_stay_compact():
    assert 'class="plugin-settings-toggle" data-a="settings"' in PATCH
    assert '<div class="plugin-settings">${tools||' in PATCH
    assert 'row.querySelector(":scope > .plugin-settings")' in PATCH
