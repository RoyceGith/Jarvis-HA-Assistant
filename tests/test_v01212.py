from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_workshop_task_approval_v01212.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v01212_supports_single_and_task_approval_choices():
    assert 'return "once"' in PATCH
    assert 'return "task"' in PATCH
    assert 'return "deny"' in PATCH
    assert "**approve task**" in PATCH


def test_v01212_task_grant_is_chat_scoped_and_time_limited():
    assert "WORKSHOP_TASK_APPROVAL_GRANTS" in PATCH
    assert "WORKSHOP_TASK_APPROVAL_SECONDS = 15 * 60" in PATCH
    assert "grant_workshop_memory_task_approval(session_id)" in PATCH
    assert "workshop_memory_task_approval_active(session_id)" in PATCH


def test_v01212_preserves_exact_write_call_binding():
    assert "workshop_write_call_ids" in PATCH
    assert "approved_workshop_call_ids" in PATCH
    assert 'workshop_decision in {"once", "task"}' in PATCH


def test_v01212_summarizes_large_notes_without_echoing_the_body():
    assert "summarize_workshop_memory_arguments" in PATCH
    assert 'label = "note content"' in PATCH
    assert 'f"<list with {len(value)} items>"' in PATCH
    assert 'title: {title}' in PATCH
    assert "call.get(\"arguments\")" in PATCH


def test_v01212_guides_one_call_generic_note_creation():
    assert "Prefer one generic" in PATCH
    assert "write_project_note call" in PATCH
    assert "create missing folders" in PATCH


def test_v01212_build_order_and_version():
    assert DOCKER.index("python3 ./apply_workshop_memory_writes_v01211.py") < DOCKER.index("python3 ./apply_workshop_task_approval_v01212.py")
    assert DOCKER.index("python3 ./apply_workshop_task_approval_v01212.py") < DOCKER.index("validate_inline_js.py ./app/static/index.html")
    assert "COPY apply_workshop_task_approval_v01212.py ./apply_workshop_task_approval_v01212.py" in DOCKER
    assert "./apply_workshop_task_approval_v01212.py ./validate_inline_js.py" in DOCKER
    assert 'version: "0.12.12"' in CONFIG
