from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_personal_wake_verifier_v012103.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")


def test_calibration_audio_requires_explicit_bounded_wav_capture() -> None:
    assert '@app.post("/api/voice/wake-calibration/{label}")' in PATCH
    assert "16000 <= clip.getnframes() <= 80000" in PATCH
    assert "clip.getframerate() == 16000" in PATCH
    assert "Record “Hey ZBRANO”" in PATCH
    assert "if(!confirm(" in PATCH


def test_verifier_uses_positive_negative_and_false_trigger_evidence() -> None:
    assert "positive >= 20 and negative >= 20" in PATCH
    assert "get_reference_clip_features" in PATCH
    assert "train_verifier_model" in PATCH
    assert "custom_verifier_models" in PATCH
    assert "wakeShadowLastCandidate" in PATCH
    assert "False-trigger clip saved" in PATCH
    assert "Personal verifier ready in silent shadow mode" in PATCH


def test_release_and_build_order_are_aligned() -> None:
    copy = "COPY apply_personal_wake_verifier_v012103.py ./apply_personal_wake_verifier_v012103.py"
    run = "python3 ./apply_personal_wake_verifier_v012103.py"
    assert copy in DOCKER and run in DOCKER
    assert DOCKER.index("python3 ./apply_wake_shadow_resources_v012102.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
