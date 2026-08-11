import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OAUTH_PATCH = (ROOT / "jarvis/apply_gmail_oauth_least_privilege_v01256.py").read_text(encoding="utf-8")
RELEASE_PATCH = (ROOT / "jarvis/apply_oauth_details_compact_v01262.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_v01262_places_oauth_details_behind_settings():
    assert '<div class="plugin-actions">${pluginActions}</div>${p.oauth_connected?' in OAUTH_PATCH
    assert '<div class="plugin-oauth-details">' in OAUTH_PATCH
    assert 'OAuth account: ${esc(p.oauth_account' in OAUTH_PATCH
    assert 'Granted scopes: ${esc((p.oauth_scopes' in OAUTH_PATCH


def test_v01262_release_version_and_build_order():
    name = "apply_oauth_details_compact_v01262.py"
    assert f"COPY {name} ./{name}" in DOCKER
    assert DOCKER.index("python3 ./apply_plugin_compact_repair_v01261.py") < DOCKER.index(f"python3 ./{name}")
    assert DOCKER.index(f"python3 ./{name}") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.62"' in CONFIG
    assert MANIFEST["version"] == "0.12.62"
    assert "ZBRANO v0.12.62" in README
    assert 'version="0.12.62"' in RELEASE_PATCH
    assert "HUD 0.12.62" in RELEASE_PATCH
