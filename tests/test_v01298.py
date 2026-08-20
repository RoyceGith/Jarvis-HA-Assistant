import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_bounded_wake_transcription_fallback_v01298.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_fallback_records_only_detected_bounded_utterances() -> None:
    assert "function sampleWakeFallback()" in PATCH
    assert "wakeFallbackVoiceFrames>=2" in PATCH
    assert "now-wakeFallbackSpeechStart>=8000" in PATCH
    assert "now-wakeFallbackLastVoice>=900" in PATCH
    assert "started-750" in PATCH


def test_native_recognition_remains_first_and_avoids_duplicate_transcription() -> None:
    assert "wakeNativeMatchAt>=started" in PATCH
    assert "startWakeFallback().catch(()=>{});stopWake(true)" in PATCH
    assert "matchWakePhrase(transcript)" in PATCH


def test_fallback_is_cost_bounded_ephemeral_and_command_capable() -> None:
    assert "const WAKE_FALLBACK_LIMIT=20" in PATCH
    assert "wakeFallbackAttempts.length>=WAKE_FALLBACK_LIMIT" in PATCH
    assert "wakeFallbackStream.getTracks().forEach(track=>track.stop())" in PATCH
    assert "startFallbackCommandWindow()" in PATCH
    assert "no saved audio" in PATCH


def test_release_and_build_order_are_aligned() -> None:
    assert 'version: "0.12.98"' in CONFIG
    assert MANIFEST["version"] == "0.12.98"
    copy = "COPY apply_bounded_wake_transcription_fallback_v01298.py ./apply_bounded_wake_transcription_fallback_v01298.py"
    run = "python3 ./apply_bounded_wake_transcription_fallback_v01298.py"
    assert copy in DOCKER
    assert run in DOCKER
    assert DOCKER.index("python3 ./apply_chrome_wake_phrase_matching_v01297.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
