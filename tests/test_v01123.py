from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_new_chat_sidebar_draft_v01123.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v01123_renders_visible_temporary_new_chat_sidebar_state():
    assert 'function renderDraftChatRow()' in PATCH
    assert "row.className = 'chat-list-item active';" in PATCH
    assert "row.dataset.draft = 'true';" in PATCH
    assert "open.textContent = 'New chat';" in PATCH
    assert 'renderDraftChatRow();' in PATCH
    assert 'apply_new_chat_sidebar_draft_v01123.py' in DOCKER
    assert 'validate_inline_js.py ./app/static/index.html' in DOCKER
    assert 'version: "0.11.23"' in CONFIG
