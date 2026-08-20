import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_reliable_wake_primary_v012100.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_reliable_listener_opens_before_native_recognition() -> None:
    assert "async function startWake()" in PATCH
    assert "await startWakeFallback()" in PATCH
    assert "if(wakeFallbackStream||wakeFallbackStarting)" in PATCH
    assert PATCH.index("await startWakeFallback()") < PATCH.rindex("new Recognition()")


def test_listener_stages_are_visible() -> None:
    assert "Reliable wake listening active" in PATCH
    assert "Speech detected - recording wake utterance" in PATCH
    assert "Trying Chrome speech recognition" in PATCH


def test_wake_transcription_is_unbiased_and_noise_gated() -> None:
    assert '@app.post("/api/voice/wake-transcribe")' in PATCH
    assert 'fetch("api/voice/wake-transcribe"' in PATCH
    assert 'if not wake:' in PATCH
    assert 'silence_hallucinations = {' in PATCH
    assert '"zbrano workshop intelligence core assistant"' in PATCH
    assert "const threshold=Math.max(.03,wakeNoiseFloor*3.5)" in PATCH
    assert "wakeFallbackVoiceFrames>=3" in PATCH
    assert "ended-started>=550" in PATCH
    assert "fallbackRateAllowed(mode)" in PATCH
    assert "fallbackRateAllowed.lastWakeAt" in PATCH
    assert "<6000" in PATCH


def test_release_and_build_order_are_aligned() -> None:
    assert 'version: "0.12.100"' in CONFIG
    assert MANIFEST["version"] == "0.12.100"
    copy = "COPY apply_reliable_wake_primary_v012100.py ./apply_reliable_wake_primary_v012100.py"
    run = "python3 ./apply_reliable_wake_primary_v012100.py"
    assert copy in DOCKER
    assert run in DOCKER
    assert DOCKER.index("python3 ./apply_valid_wake_audio_capture_v01299.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
