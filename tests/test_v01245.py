import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_notifications_scrolling_v01245.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01245_restores_automations_panel_scrolling():
    assert "#automations-panel {" in PATCH
    assert "min-height:0" in PATCH
    assert "overflow-x:hidden" in PATCH
    assert "overflow-y:auto" in PATCH
    assert "overscroll-behavior:contain" in PATCH


def test_v01245_supports_mobile_touch_scrolling():
    assert "-webkit-overflow-scrolling:touch" in PATCH
    assert "touch-action:pan-y" in PATCH
    assert "@media(max-width:700px)" in PATCH


def test_v01245_preserves_notification_watchlist():
    assert 'data-auto-panel="notifications"' in PATCH
    assert 'id="notification-watchlist"' in PATCH
    assert "#automations-panel .autonomy-view" in PATCH


def test_v01245_gives_watchlist_a_separate_notifications_tab():
    assert 'data-notification-view="center"' in PATCH
    assert 'data-notification-view="watchlist"' in PATCH
    assert 'data-notification-panel="watchlist"' in PATCH
    assert "function showNotificationView(name)" in PATCH
    assert 'showView("watchlist")' in PATCH


def test_v01245_runs_after_watchlist_and_aligns_release():
    assert "COPY apply_notifications_scrolling_v01245.py" in DOCKER
    assert DOCKER.index("python3 ./apply_notification_watchlist_v01244.py") < DOCKER.index("python3 ./apply_notifications_scrolling_v01245.py")
    assert DOCKER.index("python3 ./apply_notifications_scrolling_v01245.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.45"' in CONFIG
    assert MANIFEST["version"] == "0.12.45"
    assert "ZBRANO v0.12.45" in README
    assert 'version="0.12.45"' in PATCH
    assert "HUD 0.12.45" in PATCH
