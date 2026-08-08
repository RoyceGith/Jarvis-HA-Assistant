from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_playwright_developer_tools_v01216.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
RUN = (ROOT / "jarvis/run.sh").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_v01216_installs_and_starts_pinned_local_playwright_mcp():
    assert "@playwright/mcp@0.0.78" in DOCKER
    assert "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1" in DOCKER
    assert "chromium" in DOCKER
    for marker in (
        "playwright-mcp",
        "--headless",
        "--no-sandbox",
        "--isolated",
        "--block-service-workers",
        '--allowed-origins "http://127.0.0.1:8099"',
        "--codegen none",
        "--host 127.0.0.1",
        "--port 8931",
        "--image-responses omit",
    ):
        assert marker in RUN


def test_v01216_browser_tool_is_read_only_and_local_only():
    for marker in (
        'PLAYWRIGHT_LOCAL_ORIGIN = "http://127.0.0.1:8099"',
        "not path.startswith",
        "parsed.scheme",
        "parsed.netloc",
        "parsed.query",
        "parsed.fragment",
        '"browser_navigate"',
        '"browser_click"',
        '"browser_snapshot"',
        '"browser_console_messages"',
        '"browser_network_requests"',
        '"static": False',
        '"interaction_scope": "navigation_tab_only"',
        "PLAYWRIGHT_SURFACE_SELECTORS",
    ):
        assert marker in PATCH
    for forbidden in ('"browser_type"', '"browser_file_upload"', '"browser_evaluate"', '"browser_run_code_unsafe"'):
        assert forbidden not in PATCH


def test_v01216_is_developer_only_and_visible_as_builtin():
    assert "if not developer_mode_enabled()" in PATCH
    assert '"name": "inspect_zbrano_ui_with_playwright"' in PATCH
    assert '"builtin": True' in PATCH
    assert "Built-in · Developer Mode" in PATCH
    assert "Playwright MCP readiness" in PATCH
    assert "Developer Playwright tools" in PATCH


def test_v01216_versions_and_build_order():
    assert 'version: "0.12.16"' in CONFIG
    assert "ZBRANO v0.12.16" in README
    assert "COPY apply_playwright_developer_tools_v01216.py" in DOCKER
    assert DOCKER.index("python3 ./apply_ingress_oauth_callback_retry_v01215.py") < DOCKER.index("python3 ./apply_playwright_developer_tools_v01216.py")
    assert DOCKER.index("python3 ./apply_playwright_developer_tools_v01216.py") < DOCKER.index("validate_inline_js.py ./app/static/index.html")
