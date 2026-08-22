import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_playwright_routing_timeout_v01236.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01236_routes_playwright_only_to_browser_faults():
    assert "visible ZBRANO browser symptom" in PATCH
    assert "DOM layout" in PATCH
    assert "browser console errors" in PATCH
    assert "Never call this tool for" in PATCH
    for boundary in ("backend APIs", "MCP approval payloads", "versions", "repository source"):
        assert boundary in PATCH


def test_v01236_bounds_inspection_and_reports_the_step():
    assert "step = {\"name\": \"session initialization\"}" in PATCH
    assert "return await asyncio.wait_for(collect(), timeout=30.0)" in PATCH
    assert "Playwright inspection timed out during" in PATCH
    assert "playwright_preflight_summary(include_log=True)" in PATCH
    assert "else 35.0 if" in PATCH


def test_v01236_preserves_bounded_browser_evidence():
    for step in (
        "tool inventory", "browser navigation", "accessibility snapshot",
        "console error collection", "network request collection",
    ):
        assert step in PATCH
    assert '"snapshot": _playwright_text' in PATCH
    assert '"console_errors": _playwright_text' in PATCH
    assert '"network_requests": _playwright_text' in PATCH


def test_v01236_runs_last_and_aligns_release_markers():
    assert "COPY apply_playwright_routing_timeout_v01236.py" in DOCKER
    assert DOCKER.index("python3 ./apply_mcp_approval_payload_fix_v01235.py") < DOCKER.index("python3 ./apply_playwright_routing_timeout_v01236.py")
    assert DOCKER.index("python3 ./apply_playwright_routing_timeout_v01236.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.36"' in CONFIG
    assert MANIFEST["version"] == "0.12.36"
    assert "ZBRANO v0.12.36" in README
    assert 'version="0.12.36"' in PATCH
    assert "HUD 0.12.36" in PATCH
