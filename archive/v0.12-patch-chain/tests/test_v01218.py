from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_workshop_bulk_edit_capacity_v01218.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_v01218_expands_both_bounded_chat_tool_loops():
    assert "def runtime_tool_round_limit(session_id: str) -> int:" in PATCH
    assert "if developer_mode_enabled():" in PATCH
    assert "if workshop_memory_task_approval_active(session_id):" in PATCH
    assert "return 24" in PATCH
    assert "return 12" in PATCH
    assert "backend.count(old_limit) != 2" in PATCH
    assert "max_tool_rounds = runtime_tool_round_limit(session_id)" in PATCH


def test_v01218_preserves_approval_and_guides_efficient_bulk_edits():
    assert "under task approval" in PATCH
    assert "batch independent write calls" in PATCH
    assert "read each relevant note only once" in PATCH
    assert "Do\nnot repeatedly reread" in PATCH
    assert "no bulk replacement tool" in PATCH
    assert "WORKSHOP_TASK_APPROVAL_SECONDS" not in PATCH


def test_v01218_versions_and_build_order():
    assert 'version: "0.12.18"' in CONFIG
    assert "ZBRANO v0.12.18" in README
    assert "COPY apply_workshop_bulk_edit_capacity_v01218.py" in DOCKER
    assert DOCKER.index("python3 ./apply_build_cleanup_fix_v01217.py") < DOCKER.index("python3 ./apply_workshop_bulk_edit_capacity_v01218.py")
    assert DOCKER.index("python3 ./apply_workshop_bulk_edit_capacity_v01218.py") < DOCKER.index("validate_inline_js.py ./app/static/index.html")
    assert "&& rm ./apply_workshop_bulk_edit_capacity_v01218.py" in DOCKER
