import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_telegram_service_routing_v01250.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01250_routes_telegram_to_its_supported_action():
    assert 'service_domain = "telegram_bot" if channel["platform"] == "telegram" else "notify"' in PATCH
    assert 'await ha_ws.call_service(service_domain, "send_message", body)' in PATCH
    assert '"parse_mode": "plain_text"' in PATCH


def test_v01250_preserves_generic_notify_for_other_channels_and_websocket_transport():
    assert 'else "notify"' in PATCH
    assert "still hard-codes the generic notify action" in PATCH
    assert "regressed to REST notification delivery" in PATCH
    assert "httpx.AsyncClient" not in PATCH


def test_v01250_runs_after_v01249_and_aligns_release():
    name = "apply_telegram_service_routing_v01250.py"
    assert f"COPY {name}" in DOCKER
    assert DOCKER.index("python3 ./apply_telegram_plain_text_v01249.py") < DOCKER.index(f"python3 ./{name}")
    assert DOCKER.index(f"python3 ./{name}") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.50"' in CONFIG
    assert MANIFEST["version"] == "0.12.50"
    assert "ZBRANO v0.12.50" in README
    assert 'version="0.12.50"' in PATCH
    assert "HUD 0.12.50" in PATCH
