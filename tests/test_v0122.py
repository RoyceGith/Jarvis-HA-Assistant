from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_attachment_upload_fix_v0122.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v0122_owns_complete_attachment_upload_lifecycle():
    for marker in (
        'id="zbrano-v0122-attachment-controller"',
        "window.zbranoPendingAttachments",
        'picker.addEventListener("change", uploadSelectedFiles, true)',
        'fetch(endpoint, {method: "POST", body})',
        "if (!payload.file_id || !payload.name)",
        "renderPendingAttachments();",
        "window.zbranoAttachmentIds",
        "pending.splice(0, pending.length)",
        "event.stopImmediatePropagation()",
    ):
        assert marker in PATCH


def test_v0122_diagnostic_performs_and_cleans_up_real_upload():
    for marker in (
        '"Attachment upload operational"',
        '"__zbrano_attachment_diagnostic__"',
        '"zbrano-diagnostic.txt"',
        'client.post(',
        "response.status_code == 200",
        "stored.is_dir()",
        "shutil.rmtree(diagnostic_dir, ignore_errors=True)",
    ):
        assert marker in PATCH


def test_v0122_replaces_false_positive_browser_check():
    assert 'name: "Attachment controller wired"' in PATCH
    assert "window.zbranoAttachmentController?.ready" in PATCH
    assert "text.replace(old_browser_check, new_browser_check, 1)" in PATCH


def test_v0122_build_order_and_version():
    assert DOCKER.index("python3 ./apply_attach_and_operational_diagnostics_v0121.py") < DOCKER.index("python3 ./apply_attachment_upload_fix_v0122.py")
    assert DOCKER.index("python3 ./apply_attachment_upload_fix_v0122.py") < DOCKER.index("validate_inline_js.py ./app/static/index.html")
    assert "COPY apply_attachment_upload_fix_v0122.py ./apply_attachment_upload_fix_v0122.py" in DOCKER
    assert "./apply_attachment_upload_fix_v0122.py ./validate_inline_js.py" in DOCKER
    assert 'version: "0.12.2"' in CONFIG
