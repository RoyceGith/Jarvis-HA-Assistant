import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_measured_chat_editor_v01240.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01240_measures_both_conversation_actions():
    assert "beginChatRename(row, openButton, chat, renameButton, deleteButton)" in PATCH
    assert "renameButton?.getBoundingClientRect().height" in PATCH
    assert "deleteButton?.getBoundingClientRect().height" in PATCH
    assert "Math.max" in PATCH


def test_v01240_applies_exact_measured_height_with_priority():
    assert 'editor.style.setProperty("height", measuredHeight, "important")' in PATCH
    assert 'editor.style.setProperty("min-height", measuredHeight, "important")' in PATCH
    assert 'editor.style.setProperty("max-height", measuredHeight, "important")' in PATCH


def test_v01240_runs_last_and_aligns_release_markers():
    assert "COPY apply_measured_chat_editor_v01240.py" in DOCKER
    assert DOCKER.index("python3 ./apply_conversation_authority_alignment_v01239.py") < DOCKER.index("python3 ./apply_measured_chat_editor_v01240.py")
    assert DOCKER.index("python3 ./apply_measured_chat_editor_v01240.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.40"' in CONFIG
    assert MANIFEST["version"] == "0.12.40"
    assert "ZBRANO v0.12.40" in README
    assert 'version="0.12.40"' in PATCH
    assert "HUD 0.12.40" in PATCH
