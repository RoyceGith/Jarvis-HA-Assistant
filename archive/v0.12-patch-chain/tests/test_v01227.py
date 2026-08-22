import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_playwright_host_port_fix_v01227.py").read_text(encoding="utf-8")
RUN = (ROOT / "jarvis/run.sh").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01227_qualifies_local_playwright_hosts_with_transport_port():
    assert '--allowed-hosts "127.0.0.1:8931,localhost:8931"' in RUN
    assert '--host 127.0.0.1' in RUN
    assert '--port 8931' in RUN
    assert '--allowed-hosts "*"' not in RUN


def test_v01227_runs_after_combined_v01226_release():
    assert "COPY apply_playwright_host_port_fix_v01227.py" in DOCKER
    assert DOCKER.index("python3 ./apply_playwright_mcp_readiness_fix_v01226.py") < DOCKER.index("python3 ./apply_playwright_host_port_fix_v01227.py")
    assert DOCKER.index("python3 ./apply_playwright_host_port_fix_v01227.py") < DOCKER.index("python3 ./validate_release_manifest.py")


def test_v01227_aligns_release_markers():
    assert 'version: "0.12.27"' in CONFIG
    assert MANIFEST["version"] == "0.12.27"
    assert "ZBRANO v0.12.27" in README
    assert 'version="0.12.27"' in PATCH
    assert '"version": "0.12.27"' in PATCH
    assert "HUD 0.12.27" in PATCH


def test_v01227_documents_exact_host_header_repair():
    assert "port-qualified" in MANIFEST["summary"]
    assert any("Host header" in fix and ":8931" in fix for fix in MANIFEST["fixes"])
