import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_notification_watchlist_v01244.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01244_uses_home_assistant_metadata_for_telegram():
    assert 'config/entity_registry/list' in PATCH
    assert 'entry.get("platform")' in PATCH
    assert 'integration in {"telegram", "telegram_bot"}' in PATCH
    assert '"integration": integration or "unknown"' in PATCH


def test_v01244_keeps_notification_rules_in_automation_library():
    assert 'data = automation_store()' in PATCH
    assert '"kind": "notification_watch"' in PATCH
    assert 'data["automations"].insert(0, watch)' in PATCH
    assert 'item.get("kind") == "notification_watch"' in PATCH


def test_v01244_exposes_explicit_chat_creation_tool():
    assert '"name": "create_notification_watch"' in PATCH
    assert 'when the user explicitly asks' in PATCH
    assert 'source="chat"' in PATCH
    assert 'find_home_assistant_entities' in PATCH


def test_v01244_runs_bounded_persistent_watch_worker():
    assert 'async def notification_watch_worker()' in PATCH
    assert 'await asyncio.sleep(2.0)' in PATCH
    assert 'previous is None or previous == current' in PATCH
    assert '_notification_quiet_now' in PATCH
    assert 'cooldown_minutes' in PATCH
    assert 'one_shot' in PATCH
    assert 'name="zbrano-notification-watchlist"' in PATCH


def test_v01244_adds_watchlist_workspace_and_controls():
    assert 'Notification Watchlist' in PATCH
    assert 'id="notification-watchlist"' in PATCH
    assert 'function renderWatchlist()' in PATCH
    assert 'dataset.watchToggle' in PATCH
    assert 'dataset.watchDelete' in PATCH
    assert 'data-auto-watch=' in PATCH
    assert 'event-driven watches' in PATCH


def test_v01244_aligns_release_and_build_markers():
    assert "COPY apply_notification_watchlist_v01244.py" in DOCKER
    assert DOCKER.index("python3 ./apply_notification_center_v01243.py") < DOCKER.index("python3 ./apply_notification_watchlist_v01244.py")
    assert DOCKER.index("python3 ./apply_notification_watchlist_v01244.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.44"' in CONFIG
    assert MANIFEST["version"] == "0.12.44"
    assert "ZBRANO v0.12.44" in README
    assert 'version="0.12.44"' in PATCH
    assert "HUD 0.12.44" in PATCH
