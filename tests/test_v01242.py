import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_conversation_row_inset_v01242.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01242_insets_controls_inside_selector_frame():
    assert ".chat-list-item" in PATCH
    assert "min-height: 2rem" in PATCH
    assert "padding: 2px" in PATCH
    assert "overflow: hidden" in PATCH
    assert "height: 1.7rem !important" in PATCH


def test_v01242_reduces_conversation_name_font():
    assert ".chat-list-item .chat-open" in PATCH
    assert ".chat-list-item .chat-title-editor" in PATCH
    assert "font-size: .78rem" in PATCH
    assert "font-size: .72rem" in PATCH


def test_v01242_runs_last_and_aligns_release_markers():
    assert "COPY apply_conversation_row_inset_v01242.py" in DOCKER
    assert DOCKER.index("python3 ./apply_compact_conversation_rows_v01241.py") < DOCKER.index("python3 ./apply_conversation_row_inset_v01242.py")
    assert DOCKER.index("python3 ./apply_conversation_row_inset_v01242.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.42"' in CONFIG
    assert MANIFEST["version"] == "0.12.42"
    assert "ZBRANO v0.12.42" in README
    assert 'version="0.12.42"' in PATCH
    assert "HUD 0.12.42" in PATCH
