from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_build_cleanup_fix_v01217.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_v01217_cleanup_is_idempotent():
    assert 'RUN rm() { command rm -f "$@"; }' in DOCKER
    assert "./apply_plugin_controls_and_new_chat_v01119.py" in DOCKER


def test_v01217_versions_and_build_order():
    assert 'version: "0.12.17"' in CONFIG
    assert "ZBRANO v0.12.17" in README
    assert 'version="0.12.16"' in PATCH
    assert 'version="0.12.17"' in PATCH
    assert "COPY apply_build_cleanup_fix_v01217.py" in DOCKER
    assert DOCKER.index("python3 ./apply_playwright_developer_tools_v01216.py") < DOCKER.index("python3 ./apply_build_cleanup_fix_v01217.py")
    assert DOCKER.index("python3 ./apply_build_cleanup_fix_v01217.py") < DOCKER.index("validate_inline_js.py ./app/static/index.html")
    assert "&& rm ./apply_build_cleanup_fix_v01217.py" in DOCKER
