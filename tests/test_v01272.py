import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_natural_voice_prosody_v01272.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01272_uses_natural_boundaries_and_preserves_punctuation():
    assert "TTS treats every request boundary like punctuation" in PATCH
    assert "{36,320}" in PATCH
    assert "remaining.length >= 120" in PATCH
    assert 'remaining.lastIndexOf(", ", clauseLimit)' in PATCH
    assert "splitAt + delimiterLength" in PATCH
    assert "remaining.length > 360" in PATCH


def test_v01272_removes_artificial_short_word_splits():
    assert "retained the artificial early word-boundary split" in PATCH
    assert 'if \'remaining.lastIndexOf(" ", phraseLimit)\' in frontend' in PATCH
    assert 'or "remaining.length >= 56" in frontend' in PATCH
    assert '.replace(/\\s*\\n+\\s*/g, " ")' in PATCH
    assert '.replace(/[ \\t]{2,}/g, " ")' in PATCH


def test_v01272_preserves_live_streaming_and_prefetch():
    assert "speechPrefetch = {text, blob: fetchSpeechBlob(text, force)}" in PATCH
    assert "speech.chunks.forEach(chunk => queueSpeech(chunk));" in PATCH
    assert "response completion" not in PATCH.lower()


def test_v01272_runs_last_and_aligns_release():
    name = "apply_natural_voice_prosody_v01272.py"
    assert f"COPY {name}" in DOCKER
    assert DOCKER.index("python3 ./apply_calendar_center_v01271.py") < DOCKER.index(f"python3 ./{name}")
    assert DOCKER.index(f"python3 ./{name}") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.72"' in CONFIG
    assert MANIFEST["version"] == "0.12.72"
    assert "ZBRANO v0.12.72" in README
    assert 'version="0.12.72"' in PATCH
