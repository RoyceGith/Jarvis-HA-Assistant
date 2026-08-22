import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_notification_websocket_and_tab_activity_v01248.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01248_uses_home_assistant_websocket_for_notifications():
    assert 'await ha_ws.call_service("notify", "send_message", body)' in PATCH
    replacement = PATCH.split("new_delivery = '''", 1)[1].split("'''", 1)[0]
    assert "HA_API_BASE" not in replacement
    assert "httpx.AsyncClient" not in replacement
    assert "Home Assistant WebSocket" in replacement


def test_v01248_supports_unseen_change_indicators_across_tabs():
    assert "MutationObserver" in PATCH
    assert "zbrano-tab-unseen" in PATCH
    assert "zbranoMarkTabChanged" in PATCH
    assert '[data-auto-view]' in PATCH
    assert '[data-notification-view]' in PATCH
    assert ".settings-category-tab[data-settings-target]" in PATCH
    assert "#plugins-installed-tab, #plugins-browse-tab" in PATCH


def test_v01248_detects_autonomous_notification_activity_while_other_tabs_are_open():
    assert '@app.get("/api/notifications/activity")' in PATCH
    assert "checkNotificationActivity" in PATCH
    assert 'setInterval(checkNotificationActivity, 15000)' in PATCH
    assert 'document.getElementById("automations-tab")' in PATCH
    assert 'data-auto-view="notifications"' in PATCH
    assert 'data-notification-view="logs"' in PATCH


def test_v01248_indicator_clears_when_viewed_and_ignores_startup_rendering():
    assert 'button.addEventListener("click"' in PATCH
    assert "requestAnimationFrame(() => clear(button))" in PATCH
    assert "if (!armed || isViewed(button, panel)) return" in PATCH
    assert "setTimeout(() => { armed = true; }, 2500)" in PATCH
    assert 'background:#f39a32' in PATCH


def test_v01248_runs_after_v01247_and_aligns_release():
    name = "apply_notification_websocket_and_tab_activity_v01248.py"
    assert f"COPY {name}" in DOCKER
    assert DOCKER.index("python3 ./apply_telegram_exact_payload_v01247.py") < DOCKER.index(f"python3 ./{name}")
    assert DOCKER.index(f"python3 ./{name}") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.48"' in CONFIG
    assert MANIFEST["version"] == "0.12.48"
    assert "ZBRANO v0.12.48" in README
    assert 'version="0.12.48"' in PATCH
    assert "HUD 0.12.48" in PATCH
