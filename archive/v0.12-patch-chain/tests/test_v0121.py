from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_attach_and_operational_diagnostics_v0121.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v0121_attach_recovery_is_independent_and_late():
    for marker in (
        'id="zbrano-v0121-attach-recovery"',
        'document.getElementById("attach-file")',
        'document.getElementById("attachment-input")',
        'window.zbranoAttachRecovery',
        'event.stopImmediatePropagation()',
        'picker.click()',
    ):
        assert marker in PATCH
    assert DOCKER.index('python3 ./apply_developer_mode_self_diagnostics_v0120.py') < DOCKER.index('python3 ./apply_attach_and_operational_diagnostics_v0121.py')
    assert DOCKER.index('python3 ./apply_attach_and_operational_diagnostics_v0121.py') < DOCKER.index('validate_inline_js.py ./app/static/index.html')


def test_v0121_diagnostics_probe_real_endpoints():
    for marker in (
        'http://127.0.0.1:8099',
        '"Plugin Catalog operational"',
        '"/api/plugin-catalog"',
        '"Plugins API operational"',
        '"/api/plugins"',
        '"Shared Files operational"',
        '"/api/files/shared"',
        '"Chats API operational"',
        '"/api/chats"',
        '"Entities API operational"',
        '"/api/ha/entities"',
        '"Developer status operational"',
        '"/api/developer/status"',
    ):
        assert marker in PATCH


def test_v0121_diagnostics_check_runtime_wiring_not_just_dom_presence():
    for marker in (
        '"Attach recovery present"',
        'zbrano-v0121-attach-recovery',
        '"New Chat wiring present"',
        'newChatButton.addEventListener("click", createNewChat)',
        '"Shared Files recovery present"',
        'window.zbranoLoadSharedFiles',
        '"Plugins compact settings present"',
        'plugin-settings-toggle',
        '"Chat attachment send path present"',
        'attachment_ids: attachmentIds',
        '"Attach click wiring active"',
        '"New Chat runtime available"',
        '"Shared Files runtime available"',
        '"Plugin settings runtime available"',
    ):
        assert marker in PATCH


def test_v0121_async_diagnostics_route_and_version():
    assert 'async def developer_diagnostics()' in PATCH
    assert 'return await developer_diagnostics()' in PATCH
    assert 'version="0.12.1"' in PATCH
    assert 'HUD 0.12.1' in PATCH
    assert 'version: "0.12.1"' in CONFIG


def test_v0121_docker_copies_runs_and_removes_patch():
    assert 'COPY apply_attach_and_operational_diagnostics_v0121.py ./apply_attach_and_operational_diagnostics_v0121.py' in DOCKER
    assert '&& python3 ./apply_attach_and_operational_diagnostics_v0121.py \\' in DOCKER
    assert './apply_attach_and_operational_diagnostics_v0121.py ./validate_inline_js.py' in DOCKER
