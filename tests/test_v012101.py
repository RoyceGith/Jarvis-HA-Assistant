from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_wake_capture_watchdog_v012101.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")


def test_capture_has_independent_hard_stop_and_cleanup() -> None:
    assert "wakeFallbackCaptureTimer=setTimeout" in PATCH
    assert "8500" in PATCH
    assert "clearTimeout(wakeFallbackCaptureTimer)" in PATCH


def test_finalization_requests_data_and_recovers_empty_audio() -> None:
    assert "Finalizing wake audio..." in PATCH
    assert "recorder.requestData();recorder.stop()" in PATCH
    assert "!validDuration||!chunks.length" in PATCH
    assert "Reliable wake audio finalization failed" in PATCH


def test_voice_detection_calibrates_and_rejects_noise_hallucinations() -> None:
    assert "Calibrating reliable wake microphone" in PATCH
    assert "wakeFallbackCalibratingUntil=performance.now()+2500" in PATCH
    assert "const strongVoice=rms>threshold&&peak>" in PATCH
    assert "wakeNoiseFloor*2.8" in PATCH
    assert 'wake_characters = re.sub(' in PATCH
    assert "not wake_characters" in PATCH


def test_release_and_build_order_are_aligned() -> None:
    copy = "COPY apply_wake_capture_watchdog_v012101.py ./apply_wake_capture_watchdog_v012101.py"
    run = "python3 ./apply_wake_capture_watchdog_v012101.py"
    assert copy in DOCKER
    assert run in DOCKER
    assert DOCKER.index("python3 ./apply_reliable_wake_primary_v012100.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
