from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_wake_listening_overlay_v01296.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")


def test_overlay_appears_only_after_wake_trigger() -> None:
    assert 'id="wake-listening-overlay"' in PATCH
    assert 'showWakeOverlay("WAKE PHRASE HEARD"' in PATCH
    assert "function startCommandWindow()" in PATCH
    assert "stopRecognition(commandRecognition);showWakeOverlay()" in PATCH


def test_overlay_has_feedback_timeout_and_cancel() -> None:
    assert "updateWakeOverlay(transcript" in PATCH
    assert "No command heard" in PATCH
    assert "wakeOverlayCancel.addEventListener" in PATCH
    assert "wake-listening-progress" in PATCH
    assert "wake-listening-timeout 9s" in PATCH


def test_overlay_is_responsive_and_reduced_motion_safe() -> None:
    assert "width:min(420px,92vw)" in PATCH
    assert ':root[data-theme="light"] .wake-listening-overlay' in PATCH
    assert ':root[data-reduced-motion="true"] .wake-ring' in PATCH


def test_release_and_build_order_are_aligned() -> None:
    copy = "COPY apply_wake_listening_overlay_v01296.py ./apply_wake_listening_overlay_v01296.py"
    run = "python3 ./apply_wake_listening_overlay_v01296.py"
    assert copy in DOCKER
    assert run in DOCKER
    assert DOCKER.index("python3 ./apply_entity_inventory_draft_and_scroll_v01295.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
