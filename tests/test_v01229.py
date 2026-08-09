import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_frontend_cache_refresh_v01229.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01229_prevents_stale_ingress_html():
    assert '"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"' in PATCH
    assert '"Pragma": "no-cache"' in PATCH
    assert '"Expires": "0"' in PATCH
    assert 'http-equiv="Cache-Control"' in PATCH


def test_v01229_exposes_served_frontend_version():
    assert '"X-ZBRANO-Frontend-Version": "0.12.29"' in PATCH
    assert 'id="composer-plugin-icons"' in PATCH


def test_v01229_runs_after_composer_patch():
    assert "COPY apply_frontend_cache_refresh_v01229.py" in DOCKER
    assert DOCKER.index("python3 ./apply_composer_web_plugins_v01228.py") < DOCKER.index("python3 ./apply_frontend_cache_refresh_v01229.py")
    assert DOCKER.index("python3 ./apply_frontend_cache_refresh_v01229.py") < DOCKER.index("python3 ./validate_release_manifest.py")


def test_v01229_aligns_release_markers():
    assert 'version: "0.12.29"' in CONFIG
    assert MANIFEST["version"] == "0.12.29"
    assert "ZBRANO v0.12.29" in README
    assert 'version="0.12.29"' in PATCH
    assert "HUD 0.12.29" in PATCH
