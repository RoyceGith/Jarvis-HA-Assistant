import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_release_memory_sync_v01221.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))
VALIDATOR = (ROOT / "jarvis/validate_release_manifest.py").read_text(encoding="utf-8")


def test_v01221_manifest_matches_release_and_contains_useful_information():
    assert MANIFEST["version"] == "0.12.21"
    assert MANIFEST["project"] == "ZBRANO Workshop Assistant"
    assert MANIFEST["note"] == "Release and Change Log.md"
    assert MANIFEST["features"]
    assert MANIFEST["fixes"]
    assert MANIFEST["validation"]
    assert "Release versions are not aligned" in VALIDATOR
    assert 'for field in ("summary", "features", "fixes", "validation")' in VALIDATOR


def test_v01221_sync_is_narrow_idempotent_and_backup_backed():
    assert 'relative_path = f"{project}/{note}"' in PATCH
    assert 'release_marker(version)' in PATCH
    assert 'if marker in content:' in PATCH
    assert '"read_project_note"' in PATCH
    assert '"write_project_note"' in PATCH
    assert '"mode": "replace"' in PATCH
    assert '"create_folders": False' in PATCH
    assert "insert_release_history" in PATCH
    assert "## Release History" in PATCH


def test_v01221_sync_is_nonblocking_retryable_and_observable():
    assert "asyncio.create_task(release_sync_worker()" in PATCH
    assert "delays = (0, 10, 30, 120)" in PATCH
    assert '@app.get("/api/release-memory-sync")' in PATCH
    assert '@app.post("/api/release-memory-sync/retry")' in PATCH
    assert "Release memory synchronization" in PATCH
    assert '"release_sync": release_sync_status()' in PATCH
    assert "RELEASE_SYNC_STATE_PATH" in PATCH
    assert "def restore_release_sync_status" in PATCH
    assert 'else "degraded" if payload.get("state")' in PATCH


def test_v01221_standing_authorization_is_user_controllable():
    assert '"auto_sync_releases_to_workshop_memory": True' in PATCH
    assert "auto_sync_releases_to_workshop_memory: bool = True" in PATCH
    assert 'id="release-memory-auto-sync"' in PATCH
    assert 'data-settings-target="updates"' in PATCH
    assert "standing authorization only" in PATCH
    assert "Automatic release synchronization is disabled" in PATCH


def test_v01221_versions_and_build_order():
    assert 'version: "0.12.21"' in CONFIG
    assert "ZBRANO v0.12.21" in README
    assert "COPY release_manifest.json ./release_manifest.json" in DOCKER
    assert "COPY apply_release_memory_sync_v01221.py" in DOCKER
    assert "COPY validate_release_manifest.py" in DOCKER
    assert DOCKER.index("python3 ./apply_navigation_settings_and_chat_wrap_v01220.py") < DOCKER.index("python3 ./apply_release_memory_sync_v01221.py")
    assert DOCKER.index("python3 ./apply_release_memory_sync_v01221.py") < DOCKER.index("validate_inline_js.py ./app/static/index.html")
    assert DOCKER.index("python3 ./apply_release_memory_sync_v01221.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert DOCKER.index("python3 ./validate_release_manifest.py") < DOCKER.index("validate_inline_js.py ./app/static/index.html")
    assert "&& rm ./apply_release_memory_sync_v01221.py" in DOCKER
    assert "&& rm ./validate_release_manifest.py" in DOCKER
