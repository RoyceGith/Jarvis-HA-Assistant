from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_persistent_chat_attachment_labels_v0127.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v0127_persists_public_attachment_metadata_separately_from_model_context():
    for marker in (
        "ATTACHMENT_CONTEXT_MARKER",
        "def _attachment_message_parts(",
        "def public_chat_message(",
        "def model_chat_history(",
        'record["model_content"] = content',
        'record["attachments"] = attachments',
        '"messages": [public_chat_message(message) for message in history]',
    ):
        assert marker in PATCH


def test_v0127_renders_file_names_on_live_and_restored_user_messages():
    for marker in (
        "function appendMessageAttachments(",
        'className = "message-attachment"',
        "window.zbranoAttachmentItems",
        'addMessage(message, "user", messageAttachments)',
        "message.attachments || []",
        "formatAttachmentSize",
    ):
        assert marker in PATCH


def test_v0127_names_files_in_attachment_status():
    assert "Attached to this chat: ${names}" in PATCH
    assert "Attached and added to Shared Files: ${names}" in PATCH


def test_v0127_build_order_and_version():
    assert DOCKER.index("python3 ./apply_developer_indicator_and_policy_v0126.py") < DOCKER.index("python3 ./apply_persistent_chat_attachment_labels_v0127.py")
    assert DOCKER.index("python3 ./apply_persistent_chat_attachment_labels_v0127.py") < DOCKER.index("validate_inline_js.py ./app/static/index.html")
    assert "COPY apply_persistent_chat_attachment_labels_v0127.py ./apply_persistent_chat_attachment_labels_v0127.py" in DOCKER
    assert "./apply_persistent_chat_attachment_labels_v0127.py ./validate_inline_js.py" in DOCKER
    assert 'version: "0.12.7"' in CONFIG
