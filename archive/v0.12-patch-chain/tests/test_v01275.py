import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_compact_header_v01275.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_compact_header_layout_is_wired():
    for marker in (
        'class="brand-line"', 'class="status hud-version-label"',
        ".runtime-status-stack {", "display:flex; flex-direction:row; flex-wrap:wrap; align-items:center;",
        "nav button { min-height:2rem;", "@media(max-width:520px)",
        'id="voice-state" role="status" aria-live="polite" hidden',
        ".voice-bar .composer-context-row", "grid-template-columns:minmax(0,1fr) auto auto auto",
    ):
        assert marker in PATCH


def test_v01275_release_alignment():
    assert 'version: "0.12.75"' in CONFIG
    assert MANIFEST["version"] == "0.12.75"
    assert "COPY apply_compact_header_v01275.py" in DOCKER
    assert "python3 ./apply_compact_header_v01275.py" in DOCKER
    assert DOCKER.index("apply_fast_memory_v01274.py") < DOCKER.index("apply_compact_header_v01275.py")
