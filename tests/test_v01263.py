import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OAUTH_PATCH = (ROOT / "jarvis/apply_gmail_oauth_least_privilege_v01256.py").read_text(encoding="utf-8")
RELEASE_PATCH = (ROOT / "jarvis/apply_oauth_details_sibling_v01263.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_v01263_places_oauth_details_outside_plugin_head():
    assert '<div class="plugin-actions">${pluginActions}</div></div>${p.oauth_connected?' in OAUTH_PATCH
    assert '<div class="plugin-oauth-details">' in OAUTH_PATCH


def test_v01263_release_version_and_build_order():
    name = "apply_oauth_details_sibling_v01263.py"
    assert f"COPY {name} ./{name}" in DOCKER
    assert DOCKER.index("python3 ./apply_oauth_details_compact_v01262.py") < DOCKER.index(f"python3 ./{name}")
    assert DOCKER.index(f"python3 ./{name}") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.63"' in CONFIG
    assert MANIFEST["version"] == "0.12.63"
    assert "ZBRANO v0.12.63" in README
    assert 'version="0.12.63"' in RELEASE_PATCH
    assert "HUD 0.12.63" in RELEASE_PATCH
