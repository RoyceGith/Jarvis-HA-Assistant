import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_telegram_plain_text_v01249.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01249_forces_plain_text_only_for_telegram():
    assert '"parse_mode": "plain_text"' in PATCH
    assert "Can't parse entities" in PATCH
    assert "telegram_branch.count" in PATCH
    assert "non_telegram_branch" in PATCH


def test_v01249_preserves_websocket_notification_transport():
    assert 'await ha_ws.call_service("notify", "send_message", body)' in PATCH
    assert "HA_API_BASE" not in PATCH
    assert "httpx.AsyncClient" not in PATCH


def test_v01249_runs_after_v01248_and_aligns_release():
    name = "apply_telegram_plain_text_v01249.py"
    assert f"COPY {name}" in DOCKER
    assert DOCKER.index("python3 ./apply_notification_websocket_and_tab_activity_v01248.py") < DOCKER.index(f"python3 ./{name}")
    assert DOCKER.index(f"python3 ./{name}") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.49"' in CONFIG
    assert MANIFEST["version"] == "0.12.49"
    assert "ZBRANO v0.12.49" in README
    assert 'version="0.12.49"' in PATCH
    assert "HUD 0.12.49" in PATCH
