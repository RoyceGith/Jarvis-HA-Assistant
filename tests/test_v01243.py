import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_notification_center_v01243.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01243_discovers_home_assistant_notification_channels():
    assert "async def notification_channels()" in PATCH
    assert 'entity_id.startswith("notify.")' in PATCH
    assert '"telegram" if "telegram" in identity' in PATCH
    assert "Bot tokens remain in Home Assistant" in PATCH


def test_v01243_delivers_tests_through_home_assistant():
    assert '@app.post("/api/notifications/test")' in PATCH
    assert 'f"{HA_API_BASE}/services/notify/send_message"' in PATCH
    assert '"Authorization": f"Bearer {SUPERVISOR_TOKEN}"' in PATCH
    assert 'status="delivered"' in PATCH
    assert 'status="failed"' in PATCH


def test_v01243_adds_notification_policy_and_delivery_log():
    assert "NotificationCenterSettingsRequest" in PATCH
    assert "quiet_hours_enabled" in PATCH
    assert "critical_override" in PATCH
    assert "repeat_critical_minutes" in PATCH
    assert 'id="notification-deliveries"' in PATCH
    assert "message bodies or credentials" in PATCH


def test_v01243_adds_automation_notification_workspace():
    assert 'data-auto-view="notifications"' in PATCH
    assert 'id="notification-settings-form"' in PATCH
    assert 'id="notification-test-form"' in PATCH
    assert 'id="zbrano-v01243-notification-center"' in PATCH
    assert "Notification Center API operational" in PATCH
    assert "Notification Center frontend wired" in PATCH


def test_v01243_includes_notification_state_in_backup():
    assert '"notifications": notification_store()' in PATCH
    assert 'notifications = backup.get("notifications")' in PATCH
    assert "Backup notification data is malformed" in PATCH
    assert "_notification_save(notifications)" in PATCH


def test_v01243_runs_last_and_aligns_release_markers():
    assert "COPY apply_notification_center_v01243.py" in DOCKER
    assert DOCKER.index("python3 ./apply_conversation_row_inset_v01242.py") < DOCKER.index("python3 ./apply_notification_center_v01243.py")
    assert DOCKER.index("python3 ./apply_notification_center_v01243.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.43"' in CONFIG
    assert MANIFEST["version"] == "0.12.43"
    assert "ZBRANO v0.12.43" in README
    assert 'version="0.12.43"' in PATCH
    assert "HUD 0.12.43" in PATCH
