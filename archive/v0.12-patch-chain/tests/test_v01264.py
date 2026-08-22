import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_workshop_approval_message_fix_v01264.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_approval_continuation_receives_message_explicitly():
    assert "approval_message: str" in PATCH
    assert "priority_system_instructions(effective_system_instructions(), approval_message)" in PATCH
    assert "runtime_chat_tools(message=approval_message)" in PATCH
    assert "message=message" in PATCH  # regression guard used to detect and reject the broken generated body


def test_streaming_and_non_streaming_callers_pass_the_reply():
    assert 'workshop_decision in {"once", "task"},\n            session_id,\n            message,' in PATCH
    assert "pending_workshop,\n            approved,\n            session_id,\n            message," in PATCH
    assert "non-streaming approval call" in PATCH
    assert "streaming approval call" in PATCH


def test_v01264_release_chain_and_markers():
    assert "COPY apply_workshop_approval_message_fix_v01264.py" in DOCKER
    assert DOCKER.index("python3 ./apply_oauth_details_sibling_v01263.py") < DOCKER.index("python3 ./apply_workshop_approval_message_fix_v01264.py")
    assert DOCKER.index("python3 ./apply_workshop_approval_message_fix_v01264.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.64"' in CONFIG
    assert MANIFEST["version"] == "0.12.64"
    assert "ZBRANO v0.12.64" in README
    assert 'version="0.12.64"' in PATCH
    assert "HUD 0.12.64" in PATCH
