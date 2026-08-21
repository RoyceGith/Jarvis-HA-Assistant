import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_local_wake_conversation_v012111.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_local_wake_activation_is_explicit_and_bounded() -> None:
    assert 'id="wake-local-activate"' in PATCH
    assert "wakeShadowAbove>=2" in PATCH
    assert "wakeFallbackMode===\"wake\"" in PATCH
    assert "Date.now()-wakeLocalActivationAt>=8000" in PATCH
    assert "LOCAL WAKE PHRASE HEARD" in PATCH


def test_conversation_mode_only_chains_voice_turns() -> None:
    assert 'id="wake-conversation-enabled"' in PATCH
    assert "wakeConversationArmed=true" in PATCH
    assert 'label === "Completed"' in PATCH
    assert "zbrano-response-finished" in PATCH
    assert "wakeConversationListening?15000:9000" in PATCH
    assert "stop|end|exit|cancel" in PATCH
    assert 'id="wake-conversation-stop"' in PATCH
    assert 'value="ok thank you"' in PATCH
    assert "normalized===preferredStop" in PATCH


def test_conversation_mode_has_stop_boundaries() -> None:
    assert "document.hidden" in PATCH
    assert "wakeConversationEnabled.checked" in PATCH
    assert "wakeOverlayCancel.addEventListener" in PATCH
    assert "Conversation follow-up expired" in PATCH
    assert "if(wakeConversationWaitTimer)clearTimeout" in PATCH


def test_release_and_build_order_are_aligned() -> None:
    assert 'version: "0.12.111"' in CONFIG
    assert MANIFEST["version"] == "0.12.111"
    copy = "COPY apply_local_wake_conversation_v012111.py ./apply_local_wake_conversation_v012111.py"
    run = "python3 ./apply_local_wake_conversation_v012111.py"
    assert copy in DOCKER and run in DOCKER
    assert DOCKER.index("python3 ./apply_clean_interface_v012110.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
