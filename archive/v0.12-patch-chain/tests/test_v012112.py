import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_local_wake_command_capture_v012112.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_local_shadow_suppresses_only_wake_mode_vad() -> None:
    assert 'wakeShadowEnabled.checked&&wakeFallbackMode==="wake"' in PATCH
    assert "local command voice-activity gate" in PATCH
    assert "wakeShadowEnabled.checked)return" in PATCH


def test_wake_controls_are_grouped_without_duplicate_ids() -> None:
    assert "Enable always listening mode" in PATCH
    assert "hands-free wake controls" in PATCH
    assert "duplicate diagnostic activation control" in PATCH
    assert "local wake activation control must appear once" in PATCH


def test_release_and_build_order_are_aligned() -> None:
    assert 'version: "0.12.112"' in CONFIG
    assert MANIFEST["version"] == "0.12.112"
    copy = "COPY apply_local_wake_command_capture_v012112.py ./apply_local_wake_command_capture_v012112.py"
    run = "python3 ./apply_local_wake_command_capture_v012112.py"
    assert copy in DOCKER and run in DOCKER
    assert DOCKER.index("python3 ./apply_local_wake_conversation_v012111.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
