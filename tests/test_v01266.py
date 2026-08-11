import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_grinder_hud_indicator_v01266.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_grinder_indicator_has_all_connection_states():
    for marker in (
        '"Grinder Online"', '"Grinder Offline"', '"Grinder Broker Offline"',
        '"Grinder Waiting"', '"Grinder Monitor Off"', '"Grinder Status Unavailable"',
    ):
        assert marker in PATCH


def test_grinder_indicator_is_read_only_and_bounded():
    assert 'fetch("api/grinder-monitor/status"' in PATCH
    assert 'method:' not in PATCH
    assert "setTimeout(() => controller.abort(), 4000)" in PATCH
    assert "if (!document.hidden) refreshGrinderIndicator()" in PATCH
    assert "setInterval" in PATCH and "5000" in PATCH


def test_grinder_indicator_placement_and_accessibility():
    grinder_index = PATCH.index('id="grinder-connection-indicator"')
    developer_index = PATCH.rfind('id="developer-mode-indicator"', 0, grinder_index)
    health_index = PATCH.index('id="health"', grinder_index)
    assert developer_index < grinder_index < health_index
    assert 'role="status" aria-live="polite"' in PATCH
    assert ".grinder-connection-indicator" in PATCH
    assert "@media(max-width:620px)" in PATCH


def test_v01266_release_chain_and_markers():
    assert "COPY apply_grinder_hud_indicator_v01266.py" in DOCKER
    assert DOCKER.index("python3 ./apply_grinder_deep_monitoring_v01265.py") < DOCKER.index("python3 ./apply_grinder_hud_indicator_v01266.py")
    assert DOCKER.index("python3 ./apply_grinder_hud_indicator_v01266.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.66"' in CONFIG
    assert MANIFEST["version"] == "0.12.66"
    assert "ZBRANO v0.12.66" in README
    assert 'version="0.12.66"' in PATCH
    assert "HUD 0.12.66" in PATCH
