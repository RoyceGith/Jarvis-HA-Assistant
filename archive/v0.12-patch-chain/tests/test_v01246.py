import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_telegram_notify_compat_v01246.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01246_uses_message_only_payload_for_telegram():
    assert 'if channel["platform"] == "telegram":' in PATCH
    assert '"message": f"{title}\\\\n{message}" if title else message' in PATCH
    telegram_branch = PATCH.split('if channel["platform"] == "telegram":', 1)[1].split("else:", 1)[0]
    assert '"title": title' not in telegram_branch


def test_v01246_preserves_native_titles_for_other_channels():
    assert 'else:\n        body = {' in PATCH
    assert '"title": title' in PATCH
    assert '"message": message' in PATCH


def test_v01246_records_compatibility_delivery_evidence():
    assert "message-only compatibility" in PATCH
    assert 'channel["platform"] == "telegram"' in PATCH


def test_v01246_runs_after_scrolling_release_and_aligns_versions():
    assert "COPY apply_telegram_notify_compat_v01246.py" in DOCKER
    assert DOCKER.index("python3 ./apply_notifications_scrolling_v01245.py") < DOCKER.index("python3 ./apply_telegram_notify_compat_v01246.py")
    assert DOCKER.index("python3 ./apply_telegram_notify_compat_v01246.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.46"' in CONFIG
    assert MANIFEST["version"] == "0.12.46"
    assert "ZBRANO v0.12.46" in README
    assert 'version="0.12.46"' in PATCH
    assert "HUD 0.12.46" in PATCH
