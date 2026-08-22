import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_workshop_write_reconciliation_v01268.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_ambiguous_note_writes_are_verified_before_retry():
    assert 'tool_name == "write_project_note"' in PATCH
    assert '"read_project_note"' in PATCH
    assert "actual == expected" in PATCH
    assert 'mode == "append"' in PATCH
    assert "Automatic retry stopped to prevent" in PATCH
    assert 'mode == "create" and existing' in PATCH


def test_template_pack_recovery_is_bounded_and_idempotent():
    assert 'tool_name == "apply_project_template_pack"' in PATCH
    assert "server-defined create-missing operations" in PATCH
    assert PATCH.count("retry_result = await call_workshop_memory_tool_uncached(") == 2
    assert "only missing notes were created" in PATCH


def test_unknown_write_types_are_not_retried():
    assert '"reconciliation_supported": False' in PATCH
    assert "inspect current" in PATCH
    assert "Workshop Memory state before retrying" in PATCH
    assert "guessing could duplicate or" in PATCH


def test_post_write_response_failure_gets_truthful_completion():
    assert "async def create_workshop_continuation_response(" in PATCH
    assert "workshop_execution_fallback_reply" in PATCH
    assert "Confirmed operations" in PATCH
    assert "could not be generated" in PATCH
    assert "await create_workshop_continuation_response({" in PATCH


def test_reconciliation_runs_only_for_approved_writes():
    assert 'permission == "write"' in PATCH
    assert "call_id in approved_workshop_call_ids" in PATCH
    assert "and workshop_result_error(result)" in PATCH
    assert 'if permission == "write"' in PATCH
    assert "call_workshop_memory_tool_uncached(name, arguments)" in PATCH


def test_v01268_release_chain_and_markers():
    assert "COPY apply_workshop_write_reconciliation_v01268.py" in DOCKER
    assert DOCKER.index("python3 ./apply_release_truth_reconciliation_v01267.py") < DOCKER.index(
        "python3 ./apply_workshop_write_reconciliation_v01268.py"
    )
    assert DOCKER.index("python3 ./apply_workshop_write_reconciliation_v01268.py") < DOCKER.index(
        "python3 ./validate_release_manifest.py"
    )
    assert 'version: "0.12.68"' in CONFIG
    assert MANIFEST["version"] == "0.12.68"
    assert "ZBRANO v0.12.68" in README
    assert 'version="0.12.68"' in PATCH
    assert "HUD 0.12.68" in PATCH
