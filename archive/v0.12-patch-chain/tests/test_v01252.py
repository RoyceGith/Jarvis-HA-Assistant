import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_notification_watch_dedup_v01252.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01252_defines_semantic_watch_identity():
    assert "def _notification_watch_key(" in PATCH
    for field in ("trigger_entity", "trigger_state", "destination", "active_start", "active_end", "one_shot"):
        assert f'watch.get("{field}")' in PATCH


def test_v01252_refreshes_one_watch_and_removes_older_duplicates():
    assert "if matches:" in PATCH
    assert "watch = matches[0]" in PATCH
    assert "watch.update(payload)" in PATCH
    assert 'data["automations"].insert(0, watch)' in PATCH
    assert '"deduplicated": len(matches)' in PATCH
    assert "removed {max(0, len(matches) - 1)} older duplicate(s)" in PATCH


def test_v01252_preserves_runtime_history_when_refreshing():
    for field in ("id", "created_at", "last_observed_state", "last_triggered_at", "trigger_count"):
        assert f'"{field}"' in PATCH
    assert "watch.update(runtime)" in PATCH
    assert '"created": False' in PATCH


def test_v01252_runs_after_v01251_and_aligns_release():
    name = "apply_notification_watch_dedup_v01252.py"
    assert f"COPY {name}" in DOCKER
    assert DOCKER.index("python3 ./apply_semantic_tab_activity_v01251.py") < DOCKER.index(f"python3 ./{name}")
    assert DOCKER.index(f"python3 ./{name}") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.52"' in CONFIG
    assert MANIFEST["version"] == "0.12.52"
    assert "ZBRANO v0.12.52" in README
    assert 'version="0.12.52"' in PATCH
    assert "HUD 0.12.52" in PATCH
