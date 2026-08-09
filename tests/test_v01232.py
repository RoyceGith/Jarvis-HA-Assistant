import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_web_source_curation_v01232.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01232_prefers_sources_cited_by_the_final_answer():
    assert "cited: list[dict[str, str]]" in PATCH
    assert "discovered: list[dict[str, str]]" in PATCH
    assert "return (cited if cited else discovered)[:8]" in PATCH
    assert "only as a bounded fallback" in PATCH


def test_v01232_canonicalizes_and_deduplicates_source_urls():
    assert "def canonical_web_source_url" in PATCH
    assert 'startswith("utm_")' in PATCH
    assert '"fbclid"' in PATCH
    assert "urlunsplit" in PATCH
    assert "cited_seen" in PATCH


def test_v01232_guides_primary_current_and_direct_sources():
    assert "def web_search_quality_instructions" in PATCH
    assert "current primary or official sources" in PATCH
    assert "community sources only for clearly labelled anecdotal evidence" in PATCH
    assert "Prefer direct articles or documentation" in PATCH
    assert "publication and event dates" in PATCH


def test_v01232_caps_backend_and_frontend_sources():
    assert "sources[:8]" in PATCH
    assert ").slice(0, 8);" in PATCH
    assert "normally 3 to 8 sources" in PATCH


def test_v01232_runs_last_and_aligns_release_markers():
    assert "COPY apply_web_source_curation_v01232.py" in DOCKER
    assert DOCKER.index("python3 ./apply_live_tool_timeline_v01231.py") < DOCKER.index("python3 ./apply_web_source_curation_v01232.py")
    assert DOCKER.index("python3 ./apply_web_source_curation_v01232.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.32"' in CONFIG
    assert MANIFEST["version"] == "0.12.32"
    assert "ZBRANO v0.12.32" in README
    assert 'version="0.12.32"' in PATCH
    assert "HUD 0.12.32" in PATCH
