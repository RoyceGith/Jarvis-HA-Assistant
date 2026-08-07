from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_frontend_repair_and_device_picker_v01119.py").read_text(encoding="utf-8")
CHECKER = (ROOT / "jarvis/validate_inline_js.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")


def test_v01119_repairs_frontend_and_uses_native_chat_transport():
    assert 'malformed shared-files script start' in PATCH
    assert 'window.zbranoAttachmentIds' in PATCH
    assert 'attachment_ids: attachmentIds' in PATCH
    assert 'window.WebSocket=function' in PATCH
    assert 'Choose files from this device' in PATCH
    assert 'node", "--check"' in CHECKER
    assert 'nodejs' in DOCKER
    assert 'validate_inline_js.py ./app/static/index.html' in DOCKER
    assert 'apply_frontend_repair_and_device_picker_v01119.py' in DOCKER
