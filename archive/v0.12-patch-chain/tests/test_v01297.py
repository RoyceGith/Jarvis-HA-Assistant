from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_chrome_wake_phrase_matching_v01297.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")


def test_chrome_wake_matches_interim_and_safe_name_variants() -> None:
    assert "recognition.interimResults=true" in PATCH
    assert "function matchWakePhrase(value)" in PATCH
    assert '"hey z brano"' in PATCH
    assert '"hey zebrano"' in PATCH
    assert "event.results[index].isFinal" in PATCH


def test_listener_reports_live_transcript_and_handoffs_cleanly() -> None:
    assert "Microphone active - listening for" in PATCH
    assert "waiting for" in PATCH
    assert "setTimeout(startCommandWindow,180)" in PATCH
    assert "Math.max(250,delay)" in PATCH


def test_release_and_build_order_are_aligned() -> None:
    copy = "COPY apply_chrome_wake_phrase_matching_v01297.py ./apply_chrome_wake_phrase_matching_v01297.py"
    run = "python3 ./apply_chrome_wake_phrase_matching_v01297.py"
    assert copy in DOCKER
    assert run in DOCKER
    assert DOCKER.index("python3 ./apply_wake_listening_overlay_v01296.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
