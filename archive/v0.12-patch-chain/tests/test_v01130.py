from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_shared_files_runtime_recovery_v01130.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v01130_shared_files_has_independent_late_controller():
    assert 'zbrano-v01130-shared-files-recovery' in PATCH
    assert 'function activateFilesPanel()' in PATCH
    assert 'api/files/shared?' in PATCH
    assert 'window.zbranoLoadSharedFiles' in PATCH
    assert 'event.stopPropagation()' in PATCH
    assert '["chat-panel", "entities-panel", "settings-panel", "plugins-panel", "files-panel"]' in PATCH


def test_v01130_plugin_token_is_in_form():
    assert 'id="plugin-install-form"' in PATCH
    assert 'form?.addEventListener("submit"' in PATCH
    assert 'button?.click()' in PATCH
    assert 'id="plugin-token" type="password"' in PATCH


def test_v01130_preserves_github_approval_release_before_recovery():
    assert 'apply_github_tool_approval_policy_v01129.py' in DOCKER
    assert 'apply_shared_files_runtime_recovery_v01130.py' in DOCKER
    assert DOCKER.index('python3 ./apply_github_tool_approval_policy_v01129.py') < DOCKER.index('python3 ./apply_shared_files_runtime_recovery_v01130.py')
    assert DOCKER.index('python3 ./apply_shared_files_runtime_recovery_v01130.py') < DOCKER.index('validate_inline_js.py ./app/static/index.html')


def test_v01130_release_version():
    assert 'version: "0.11.30"' in CONFIG
