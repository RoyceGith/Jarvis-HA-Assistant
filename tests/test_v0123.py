from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_shared_files_and_diagnostics_v0123.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v0123_shared_files_controller_owns_actions():
    for marker in (
        'id="zbrano-v0123-shared-files-controller"',
        'deleteButton.addEventListener("click", deleteSelected, true)',
        'useButton.addEventListener("click", attachSelected, true)',
        'method: "DELETE"',
        'body: JSON.stringify({file_ids: ids})',
        "pending.splice(index, 1)",
        "renderPendingAttachments",
    ):
        assert marker in PATCH


def test_v0123_diagnostics_are_operational_and_transactional():
    for marker in (
        '"Shared Files create/list/delete operational"',
        '"Conversation lifecycle operational"',
        '"Chat attachment lifecycle operational"',
        '"Persistent storage operational"',
        '"Application health and version"',
        '"Voice pipeline readiness"',
        '"AI chat readiness"',
        '"Workshop Memory operational"',
        '"Entity inventory operational"',
        '"GitHub MCP readiness"',
        '"repair_hint"',
    ):
        assert marker in PATCH


def test_v0123_catalog_distinguishes_cold_start_retry():
    assert "for attempt in (1, 2):" in PATCH
    assert "timeout=18.0" in PATCH
    assert '"operational" if attempt == 1 else "degraded"' in PATCH
    assert "cold start required retry" in PATCH


def test_v0123_reports_diagnostic_levels():
    for status in ("present", "wired", "operational", "degraded", "failed"):
        assert f'"{status}"' in PATCH
    assert '"counts": counts' in PATCH
    assert 'status === "degraded"' in PATCH
    assert "Repair hint:" in PATCH


def test_v0123_build_order_and_version():
    assert DOCKER.index("python3 ./apply_attachment_upload_fix_v0122.py") < DOCKER.index("python3 ./apply_shared_files_and_diagnostics_v0123.py")
    assert DOCKER.index("python3 ./apply_shared_files_and_diagnostics_v0123.py") < DOCKER.index("validate_inline_js.py ./app/static/index.html")
    assert "COPY apply_shared_files_and_diagnostics_v0123.py ./apply_shared_files_and_diagnostics_v0123.py" in DOCKER
    assert "./apply_shared_files_and_diagnostics_v0123.py ./validate_inline_js.py" in DOCKER
    assert 'version: "0.12.3"' in CONFIG
