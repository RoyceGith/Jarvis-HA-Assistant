from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_new_chat_shared_files_fix_v01122.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v01122_repairs_new_chat_entities_duplicate_and_shared_files_state():
    assert 'staleSocket?.close();' in PATCH
    assert 'activeRequest = null;' in PATCH
    assert 'stopAudioPlayback("VOICE READY")' in PATCH
    assert 'legacy Entities New Chat remains' in PATCH
    assert 'No shared files. Upload using Add to Shared Files.' in PATCH
    assert 'Shared Files failed to load:' in PATCH
    assert 'New Chat still silently returns' in PATCH
    assert 'apply_new_chat_shared_files_fix_v01122.py' in DOCKER
    assert 'validate_inline_js.py ./app/static/index.html' in DOCKER
    assert 'version: "0.11.22"' in CONFIG
