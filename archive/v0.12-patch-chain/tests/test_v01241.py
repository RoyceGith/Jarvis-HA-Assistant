import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_compact_conversation_rows_v01241.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01241_compacts_every_conversation_row_control():
    for selector in (".chat-open", ".chat-title-editor", ".chat-actions", ".chat-rename", ".chat-delete"):
        assert selector in PATCH
    assert "min-height: 1.8rem" in PATCH
    assert "max-height: 1.8rem" in PATCH
    assert "padding: 0 .55rem !important" in PATCH


def test_v01241_keeps_phone_rows_compact():
    assert "@media (max-width: 760px)" in PATCH
    assert "min-height: 1.65rem" in PATCH
    assert "max-height: 1.65rem !important" in PATCH


def test_v01241_runs_last_and_aligns_release_markers():
    assert "COPY apply_compact_conversation_rows_v01241.py" in DOCKER
    assert DOCKER.index("python3 ./apply_measured_chat_editor_v01240.py") < DOCKER.index("python3 ./apply_compact_conversation_rows_v01241.py")
    assert DOCKER.index("python3 ./apply_compact_conversation_rows_v01241.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.41"' in CONFIG
    assert MANIFEST["version"] == "0.12.41"
    assert "ZBRANO v0.12.41" in README
    assert 'version="0.12.41"' in PATCH
    assert "HUD 0.12.41" in PATCH
