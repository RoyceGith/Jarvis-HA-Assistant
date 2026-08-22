import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_customizable_entity_columns_v01255.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01255_supports_column_reordering():
    assert 'table.addEventListener("dragstart"' in PATCH
    assert 'table.addEventListener("dragover"' in PATCH
    assert 'table.addEventListener("drop"' in PATCH
    assert 'layout.order = nextOrder' in PATCH


def test_v01255_supports_pointer_resizing():
    assert 'className = "entity-column-resizer"' in PATCH
    assert 'table.addEventListener("pointerdown"' in PATCH
    assert 'window.addEventListener("pointermove"' in PATCH
    assert 'Math.min(700' in PATCH


def test_v01255_persists_and_resets_layout():
    assert 'zbrano_entity_column_layout_v1' in PATCH
    assert 'localStorage.setItem(STORAGE_KEY' in PATCH
    assert 'localStorage.removeItem(STORAGE_KEY)' in PATCH
    assert 'reset.id = "reset-entity-columns"' in PATCH


def test_v01255_reapplies_layout_after_entity_render():
    assert 'window.zbranoApplyEntityColumnLayout?.();' in PATCH
    assert 'window.zbranoApplyEntityColumnLayout = applyLayout' in PATCH
    assert 'for (const row of rows.rows) reorderRow(row)' in PATCH


def test_v01255_runs_after_v01254_and_aligns_release():
    name = "apply_customizable_entity_columns_v01255.py"
    assert f"COPY {name}" in DOCKER
    assert DOCKER.index("python3 ./apply_gmail_pre_registered_oauth_v01254.py") < DOCKER.index(f"python3 ./{name}")
    assert DOCKER.index(f"python3 ./{name}") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.55"' in CONFIG
    assert MANIFEST["version"] == "0.12.55"
    assert "ZBRANO v0.12.55" in README
    assert 'version="0.12.55"' in PATCH
    assert "HUD 0.12.55" in PATCH
