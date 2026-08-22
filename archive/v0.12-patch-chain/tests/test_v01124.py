from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_remove_legacy_new_chat_interceptor_v01124.py").read_text(encoding="utf-8")
VALIDATOR = (ROOT / "jarvis/validate_new_chat_wiring.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v01124_removes_capture_interceptor_and_validates_final_html():
    assert 'legacy capture-phase New Chat interceptor' in PATCH
    assert 'newChatButton.addEventListener("click", createNewChat);' in PATCH
    assert 'event.target.closest?.("#new-chat-button, #clear-chat")' in PATCH
    assert 'capture-phase handler intercepts New Chat' in VALIDATOR
    assert 'id="clear-chat"' in VALIDATOR
    assert 'apply_remove_legacy_new_chat_interceptor_v01124.py' in DOCKER
    assert 'validate_new_chat_wiring.py ./app/static/index.html' in DOCKER
    assert 'validate_inline_js.py ./app/static/index.html' in DOCKER
    assert 'version: "0.11.24"' in CONFIG
