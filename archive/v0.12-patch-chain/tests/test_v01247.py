import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_telegram_exact_payload_v01247.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01247_telegram_matches_verified_home_assistant_action():
    assert '"entity_id": request.target' in PATCH
    assert '"message": message' in PATCH
    assert "unmodified message" in PATCH
    replacement = PATCH.split("new = '''", 1)[1].split("'''", 1)[0]
    assert '"title":' not in replacement
    assert 'f"{title}' not in replacement


def test_v01247_keeps_title_only_in_delivery_history():
    assert "title remains in" in PATCH
    assert "ZBRANO Delivery History" in PATCH
    assert "verified exact-message compatibility" in PATCH


def test_v01247_adds_separate_delivery_logs_tab():
    assert 'data-notification-view="logs"' in PATCH
    assert 'data-notification-panel="logs"' in PATCH
    assert "Delivery Logs" in PATCH
    assert 'id="notification-deliveries"' in PATCH
    assert "notification-delivery-log-card" in PATCH


def test_v01247_delivery_logs_support_single_and_bulk_deletion():
    assert '@app.delete("/api/notifications/deliveries")' in PATCH
    assert "NotificationDeliveryDeleteRequest" in PATCH
    assert 'id="notification-log-select-all"' in PATCH
    assert 'id="notification-log-delete"' in PATCH
    assert 'className = "notification-delivery-select"' in PATCH
    assert "selectedDeliveries" in PATCH
    assert 'method:"DELETE"' in PATCH


def test_v01247_runs_after_v01246_and_aligns_release():
    assert "COPY apply_telegram_exact_payload_v01247.py" in DOCKER
    assert DOCKER.index("python3 ./apply_telegram_notify_compat_v01246.py") < DOCKER.index("python3 ./apply_telegram_exact_payload_v01247.py")
    assert DOCKER.index("python3 ./apply_telegram_exact_payload_v01247.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.47"' in CONFIG
    assert MANIFEST["version"] == "0.12.47"
    assert "ZBRANO v0.12.47" in README
    assert 'version="0.12.47"' in PATCH
    assert "HUD 0.12.47" in PATCH
