from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_entity_inventory_draft_and_scroll_v01295.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")


def test_entity_inventory_draft_is_approval_safe() -> None:
    assert 'async def prepare_entity_catalog_draft(' in PATCH
    assert '"saved": False' in PATCH
    assert '"permanent_project_notes_changed": False' in PATCH
    assert '"save_session_draft"' in PATCH  # only the removal guard may mention it
    assert "still contains the obsolete save_session_draft call" in PATCH


def test_frontend_handles_non_json_errors_and_downloads_markdown() -> None:
    assert "Prepare Entity Inventory Update" in PATCH
    assert "const responseText = await response.text()" in PATCH
    assert "JSON.parse(responseText)" in PATCH
    assert 'new Blob([data.catalog_markdown], {type: "text/markdown;charset=utf-8"})' in PATCH


def test_entities_table_has_real_scroll_container() -> None:
    assert "#entities-panel { display:flex; flex-direction:column; min-height:0; overflow:hidden; }" in PATCH
    assert "#entities-panel .table-wrap { flex:1 1 auto; min-height:0; height:auto" in PATCH
    assert "-webkit-overflow-scrolling:touch" in PATCH


def test_brave_wake_loop_is_disabled_with_clear_fallback() -> None:
    assert "const braveBrowser=Boolean(navigator.brave)" in PATCH
    assert "&&Recognition&&!braveBrowser" in PATCH
    assert "Browser wake phrase is unavailable in Brave" in PATCH
    assert "Push-to-talk still works" in PATCH
    assert "if(showWakeCompatibility())startWake()" in PATCH


def test_release_and_build_order_are_aligned() -> None:
    copy = "COPY apply_entity_inventory_draft_and_scroll_v01295.py ./apply_entity_inventory_draft_and_scroll_v01295.py"
    run = "python3 ./apply_entity_inventory_draft_and_scroll_v01295.py"
    assert copy in DOCKER
    assert run in DOCKER
    assert DOCKER.index("python3 ./apply_proactive_voice_and_wake_word_v01294.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
