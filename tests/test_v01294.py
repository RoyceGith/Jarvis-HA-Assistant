import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_proactive_voice_and_wake_word_v01294.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_proactive_suggestions_are_polled_without_ai_requests() -> None:
    assert 'fetch("api/automations",{cache:"no-store"})' in PATCH
    assert "setInterval(pollSuggestions,5000)" in PATCH
    assert 'await speakText(prompt,true)' in PATCH
    assert "suggestionBaseline" in PATCH
    assert "zbrano_spoken_suggestions_v1" in PATCH


def test_voice_decision_uses_existing_approval_endpoints() -> None:
    assert '["pending","approval_required"]' in PATCH
    assert '${encodeURIComponent(suggestion.id)}/${verb}' in PATCH
    assert 'decision==="approve"?"approve":"dismiss"' in PATCH
    assert "Listening for approve or decline" in PATCH


def test_wake_phrase_is_explicit_and_browser_bounded() -> None:
    assert '"wake_word_enabled": False' in PATCH
    assert '"wake_phrase": "hey zbrano"' in PATCH
    assert "window.SpeechRecognition||window.webkitSpeechRecognition" in PATCH
    assert "only while this page is open" in PATCH
    assert "wakeCanRun()" in PATCH


def test_release_and_build_order_are_aligned() -> None:
    assert 'version: "0.12.94"' in CONFIG
    assert MANIFEST["version"] == "0.12.94"
    copy = "COPY apply_proactive_voice_and_wake_word_v01294.py ./apply_proactive_voice_and_wake_word_v01294.py"
    run = "python3 ./apply_proactive_voice_and_wake_word_v01294.py"
    assert copy in DOCKER
    assert run in DOCKER
    assert DOCKER.index("python3 ./apply_ha_live_evidence_and_climate_confirmation_v01293.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
