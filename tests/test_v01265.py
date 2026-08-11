import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_grinder_deep_monitoring_v01265.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
RUN = (ROOT / "jarvis/run.sh").read_text(encoding="utf-8")
REQUIREMENTS = (ROOT / "jarvis/requirements.txt").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_grinder_monitor_is_strictly_read_only():
    assert '"telemetry", "event", "availability"' in PATCH
    assert '/+/telemetry' in PATCH
    assert '/+/event' in PATCH
    assert '/+/availability' in PATCH
    assert "client.publish" not in PATCH
    assert "/command" not in PATCH
    assert "ZBRANO subscribes" in PATCH


def test_grinder_monitor_bounds_and_incident_evidence():
    assert "GRINDER_BUFFER_SECONDS = 60.0" in PATCH
    assert "GRINDER_HEARTBEAT_TIMEOUT = 3.5" in PATCH
    assert "GRINDER_MAX_PAYLOAD = 8192" in PATCH
    assert "GRINDER_MAX_INCIDENTS = 100" in PATCH
    assert '"pre_failure_window": window' in PATCH
    assert '"heartbeat_lost_at": previous.get("heartbeat_lost_at")' in PATCH
    assert 'state["frozen_window"] = list(' in PATCH
    assert '"last_connectivity_gap"' in PATCH
    assert "previous_boot_id" in PATCH
    assert "abrupt_reset_while_grinding" in PATCH


def test_grinder_monitor_chat_tools_and_api_are_wired():
    for marker in (
        "get_grinder_diagnostic_status",
        "list_grinder_incidents",
        "get_grinder_incident",
        "/api/grinder-monitor/status",
        "/api/grinder-monitor/incidents",
        "GRINDER_MONITOR_TOOLS + workshop_memory_function_tools()",
    ):
        assert marker in PATCH


def test_mqtt_settings_are_option_backed_and_secret_is_not_committed():
    assert "aiomqtt>=2.4.0,<3.0" in REQUIREMENTS
    assert 'grinder_mqtt_password: ""' in CONFIG
    assert 'grinder_mqtt_password: "password"' in CONFIG
    assert "GRINDER_MQTT_PASSWORD" in RUN
    assert "change-me" not in CONFIG


def test_v01265_release_chain_and_markers():
    assert "COPY apply_grinder_deep_monitoring_v01265.py" in DOCKER
    assert DOCKER.index("python3 ./apply_workshop_approval_message_fix_v01264.py") < DOCKER.index("python3 ./apply_grinder_deep_monitoring_v01265.py")
    assert DOCKER.index("python3 ./apply_grinder_deep_monitoring_v01265.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.65"' in CONFIG
    assert MANIFEST["version"] == "0.12.65"
    assert "ZBRANO v0.12.65" in README
    assert 'version="0.12.65"' in PATCH
    assert "HUD 0.12.65" in PATCH
