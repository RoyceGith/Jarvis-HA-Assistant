import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_release_truth_reconciliation_v01267.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")
HELPER_START = PATCH.index("    helpers = r'''\n") + len("    helpers = r'''\n")
HELPER_END = PATCH.index("\n'''\n    sync_start", HELPER_START)
HELPERS: dict[str, Any] = {"re": re, "Any": Any}
exec(PATCH[HELPER_START:HELPER_END], HELPERS)


def test_release_sync_reconciles_primary_and_specialist_notes():
    for note in (
        "Project Overview.md", "Requirements.md", "Deployment and Operations.md",
        "Release and Change Log.md", "Session Handoff.md", "Architecture.md",
        "API and Integrations.md", "Data and Storage.md", "Security and Permissions.md",
        "Test Log.md",
    ):
        assert note in PATCH
    assert "canonical release truth" in PATCH


def test_release_sync_preserves_history_and_removes_early_exit():
    assert "insert_release_history(updated, render_release_entry(manifest))" in PATCH
    assert "Historical entries are preserved" in PATCH
    assert PATCH.count("if marker in content:") == 1  # verifier rejects this marker in generated code
    assert "retained the stale release-marker early exit" in PATCH
    assert "historical|previous|superseded|legacy|old version" in PATCH


def test_current_truth_is_deterministic_and_idempotent():
    assert "CURRENT_RELEASE_BLOCK_START" in PATCH
    assert "CURRENT_RELEASE_BLOCK_END" in PATCH
    assert "managed.sub(block, content, count=1)" in PATCH
    assert "updated == content" in PATCH
    assert "installed_at" not in PATCH.split("def render_current_release_truth", 1)[1].split("def _insert_after_title", 1)[0]


def test_current_truth_behavior_preserves_historical_versions():
    manifest = {
        "version": "0.12.67",
        "summary": "Current release reconciliation",
        "source": "RoyceGith/Jarvis-HA-Assistant main",
    }
    source = """# ZBRANO\n\n## Current Source Truth\n\n- **Version:** v0.12.18\n- **Source and runtime version:** 0.12.35\n\n## Historical Checkpoints\n\n- v0.12.18 was a historical release.\n"""
    reconciled = HELPERS["reconcile_explicit_current_versions"](source, "0.12.67")
    updated = HELPERS["upsert_current_release_truth"](reconciled, manifest, release_log=False)
    assert "- **Version:** v0.12.67" in updated
    assert "- **Source and runtime version:** 0.12.67" in updated
    assert "v0.12.18 was a historical release" in updated
    repeated = HELPERS["upsert_current_release_truth"](
        HELPERS["reconcile_explicit_current_versions"](updated, "0.12.67"),
        manifest,
        release_log=False,
    )
    assert repeated == updated


def test_release_log_current_section_replaced_without_touching_history():
    manifest = {"version": "0.12.67", "summary": "Fix", "source": "main"}
    source = """# Release Log\n\n## Current Release\n\n- **Source and runtime version:** 0.12.35\n\n## Release History\n\n### v0.12.35\n\n- Historical release evidence.\n"""
    updated = HELPERS["upsert_current_release_truth"](source, manifest, release_log=True)
    assert "- **Source and runtime version:** 0.12.67" in updated
    assert updated.count("## Current Release") == 1
    assert "### v0.12.35" in updated
    assert "Historical release evidence" in updated


def test_release_sync_reports_multi_note_results():
    for field in ("updated_notes", "already_current_notes", "missing_notes", "failed_notes"):
        assert field in PATCH
    assert "Canonical release reconciliation failed" in PATCH


def test_v01267_release_chain_and_markers():
    assert "COPY apply_release_truth_reconciliation_v01267.py" in DOCKER
    assert DOCKER.index("python3 ./apply_grinder_hud_indicator_v01266.py") < DOCKER.index("python3 ./apply_release_truth_reconciliation_v01267.py")
    assert DOCKER.index("python3 ./apply_release_truth_reconciliation_v01267.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.67"' in CONFIG
    assert MANIFEST["version"] == "0.12.67"
    assert "ZBRANO v0.12.67" in README
    assert 'version="0.12.67"' in PATCH
    assert "HUD 0.12.67" in PATCH
