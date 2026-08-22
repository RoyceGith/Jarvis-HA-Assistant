from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_history_recent_entity_refresh_v01292.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")


def test_history_prioritizes_recent_live_entities() -> None:
    assert "const recent=[...new Set((live.events||[])" in PATCH
    assert "[...recent,...selected]" in PATCH
    assert ".slice(0,8)" in PATCH
    assert "stale History selection early return" in PATCH


def test_history_exposes_capture_evidence() -> None:
    assert "live capture ${live.connected?'connected':'disconnected'}" in PATCH
    assert "journal ${Number(live.count||0)}" in PATCH
    assert "await window.zbranoHaHistory?.load()" in PATCH


def test_release_and_build_order_are_aligned() -> None:
    copy = "COPY apply_history_recent_entity_refresh_v01292.py ./apply_history_recent_entity_refresh_v01292.py"
    run = "python3 ./apply_history_recent_entity_refresh_v01292.py"
    assert copy in DOCKER
    assert run in DOCKER
    assert DOCKER.index("python3 ./apply_telegram_chat_id_and_entity_search_v01291.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
