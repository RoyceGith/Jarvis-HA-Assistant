import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_mcp_approval_payload_fix_v01235.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01235_approved_payload_omits_reason():
    assert "OpenAI rejects `reason` when approve is true" in PATCH
    assert '"approve": True,' in PATCH
    assert "approved MCP response still contains reason" in PATCH
    replacement = PATCH.split("Cancellation returned above", 1)[1]
    replacement = replacement.split('"approved MCP response payload"', 1)[0]
    assert '"reason":' not in replacement


def test_v01235_preserves_terminal_local_cancellation():
    assert "Cancellation returned above, so this continuation is approval-only" in PATCH
    assert '"approve": approval_decision' in PATCH
    assert "Denied by user in ZBRANO chat" in PATCH


def test_v01235_runs_last_and_aligns_release_markers():
    assert "COPY apply_mcp_approval_payload_fix_v01235.py" in DOCKER
    assert DOCKER.index("python3 ./apply_native_approval_and_activity_order_v01234.py") < DOCKER.index("python3 ./apply_mcp_approval_payload_fix_v01235.py")
    assert DOCKER.index("python3 ./apply_mcp_approval_payload_fix_v01235.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.35"' in CONFIG
    assert MANIFEST["version"] == "0.12.35"
    assert "ZBRANO v0.12.35" in README
    assert 'version="0.12.35"' in PATCH
    assert "HUD 0.12.35" in PATCH
