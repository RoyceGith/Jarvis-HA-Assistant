from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_new_chat_draft_fix_v01121.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")


def test_v01121_new_chat_is_unsaved_draft_until_first_message():
    assert 'showPanel("chat");' in PATCH
    assert 'jarvisChatSessionId = createSessionId();' in PATCH
    assert 'localStorage.setItem("jarvis_chat_session_id", jarvisChatSessionId);' in PATCH
    assert 'window.zbranoClearPendingAttachments();' in PATCH
    assert 'fetch("api/chats"' in PATCH  # present only in the old block being replaced
    assert 'New Chat still persists before first message' in PATCH
    assert 'apply_new_chat_draft_fix_v01121.py' in DOCKER
    assert 'validate_inline_js.py ./app/static/index.html' in DOCKER
