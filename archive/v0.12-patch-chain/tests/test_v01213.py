from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_release_alignment_v01213.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_v01213_preserves_workshop_memory_workflow():
    assert "summarize_workshop_memory_arguments" in PATCH
    assert "WORKSHOP_TASK_APPROVAL_GRANTS" in PATCH
    assert "write_project_note" in PATCH


def test_v01213_aligns_companion_release_and_versions():
    assert "Workshop Memory v0.1.28" in README
    assert 'version: "0.12.13"' in CONFIG
    assert "HUD 0.12.13" in PATCH


def test_v01213_build_order():
    assert DOCKER.index("python3 ./apply_workshop_task_approval_v01212.py") < DOCKER.index("python3 ./apply_release_alignment_v01213.py")
    assert DOCKER.index("python3 ./apply_release_alignment_v01213.py") < DOCKER.index("validate_inline_js.py ./app/static/index.html")
    assert "COPY apply_release_alignment_v01213.py ./apply_release_alignment_v01213.py" in DOCKER
