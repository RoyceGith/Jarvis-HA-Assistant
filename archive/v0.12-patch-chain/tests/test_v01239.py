import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_conversation_authority_alignment_v01239.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01239_enforces_conversation_editor_height():
    assert ".chat-list-item .chat-title-editor" in PATCH
    assert "box-sizing: border-box !important" in PATCH
    assert "height: 1.8rem !important" in PATCH
    assert "max-height: 1.8rem !important" in PATCH
    assert "height: 1.65rem !important" in PATCH
    assert "max-height: 1.65rem !important" in PATCH


def test_v01239_stacks_authority_checkboxes_as_rows():
    assert "#autonomy-settings-form .autonomy-form-grid .check" in PATCH
    assert "grid-column: 1 / -1" in PATCH
    assert "width: 100%" in PATCH
    assert 'input[type="checkbox"]' in PATCH
    assert "flex: 0 0 auto" in PATCH


def test_v01239_runs_last_and_aligns_release_markers():
    assert "COPY apply_conversation_authority_alignment_v01239.py" in DOCKER
    assert DOCKER.index("python3 ./apply_mobile_chat_layout_v01238.py") < DOCKER.index("python3 ./apply_conversation_authority_alignment_v01239.py")
    assert DOCKER.index("python3 ./apply_conversation_authority_alignment_v01239.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.39"' in CONFIG
    assert MANIFEST["version"] == "0.12.39"
    assert "ZBRANO v0.12.39" in README
    assert 'version="0.12.39"' in PATCH
    assert "HUD 0.12.39" in PATCH
