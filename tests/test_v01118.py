from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_shared_files_and_github_state_v01118.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v01118_shared_files_and_github_connected_state():
    assert 'Path("/data/shared_files")' in PATCH
    assert 'Path("/data/uploads")' in PATCH
    assert '@app.delete("/api/files/shared")' in PATCH
    assert 'Delete selected' in PATCH
    assert 'Attach selected to chat' in PATCH
    assert 'GitHub connected · installed' in PATCH
    assert 'attachment_ids: list[str]' in PATCH
    assert 'apply_shared_files_and_github_state_v01118.py' in DOCKER
    assert 'version: "0.11.18"' in CONFIG
