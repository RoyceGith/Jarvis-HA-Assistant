import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_continuous_voice_playback_v01270.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01270_keeps_speech_live_while_text_is_streaming():
    assert "speech.chunks.forEach(chunk => queueSpeech(chunk));" in PATCH
    assert "no longer starts speech while text is streaming" in PATCH
    assert "queueContinuousSpeech" not in PATCH


def test_v01270_prefetches_next_voice_segment_during_current_playback():
    assert "async function fetchSpeechBlob(text, force = false)" in PATCH
    assert "function primeSpeechPrefetch(force = false)" in PATCH
    assert "speechPrefetch = {text, blob: fetchSpeechBlob(text, force)}" in PATCH
    assert "await playSpeechText(nextText, force, prepared)" in PATCH
    assert "if (speechPrefetchAbortController) speechPrefetchAbortController.abort()" in PATCH


def test_v01270_runs_last_and_aligns_release():
    name = "apply_continuous_voice_playback_v01270.py"
    assert f"COPY {name}" in DOCKER
    assert DOCKER.index("python3 ./apply_grinder_incident_routing_v01269.py") < DOCKER.index(
        f"python3 ./{name}"
    )
    assert DOCKER.index(f"python3 ./{name}") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.70"' in CONFIG
    assert MANIFEST["version"] == "0.12.70"
    assert "ZBRANO v0.12.70" in README
    assert 'version="0.12.70"' in PATCH
    assert "HUD 0.12.70" in PATCH
