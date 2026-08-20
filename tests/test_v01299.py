import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_valid_wake_audio_capture_v01299.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_each_utterance_gets_a_fresh_complete_container() -> None:
    assert "new MediaRecorder(wakeFallbackStream" in PATCH
    assert "recorder.start(100)" in PATCH
    assert "recorder.onstop=()=>{" in PATCH
    assert "new Blob(chunks,{type:recorder.mimeType" in PATCH


def test_idle_listener_does_not_accumulate_rolling_webm_fragments() -> None:
    assert "wakeFallbackRecorder=null" in PATCH
    assert "wakeFallbackRecorder=recorder;wakeFallbackChunks=chunks" in PATCH
    assert "if(!wakeFallbackAnalyser)return" in PATCH


def test_obsolete_composer_helper_is_removed_to_reclaim_width() -> None:
    assert 'helper_marker = "AI-generated voice"' in PATCH
    assert 'frontend.rfind("<span", 0, helper_position)' in PATCH
    assert "still contains the obsolete composer helper label" in PATCH


def test_release_and_build_order_are_aligned() -> None:
    assert 'version: "0.12.99"' in CONFIG
    assert MANIFEST["version"] == "0.12.99"
    copy = "COPY apply_valid_wake_audio_capture_v01299.py ./apply_valid_wake_audio_capture_v01299.py"
    run = "python3 ./apply_valid_wake_audio_capture_v01299.py"
    assert copy in DOCKER
    assert run in DOCKER
    assert DOCKER.index("python3 ./apply_bounded_wake_transcription_fallback_v01298.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
