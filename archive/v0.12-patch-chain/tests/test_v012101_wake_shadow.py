from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_local_wake_shadow_v012101.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
MODEL = ROOT / "jarvis/models/wakeword/hey_zbrano.onnx"


def test_shadow_mode_is_silent_local_and_observable() -> None:
    assert '@app.websocket("/api/voice/wake-shadow")' in PATCH
    assert 'inference_framework="onnx"' in PATCH
    assert 'never retain audio or activate chat' in PATCH
    assert 'if(!wakeFallbackAnalyser||wakeShadowEnabled.checked)return' in PATCH
    assert 'Chat was not activated' in PATCH
    assert 'localStorage.setItem(WAKE_SHADOW_KEY' in PATCH
    assert 'wake-shadow-mark-false' in PATCH
    assert 'wake-shadow-threshold' in PATCH


def test_model_is_exact_trained_artifact() -> None:
    import hashlib

    assert MODEL.stat().st_size == 205430
    assert hashlib.sha256(MODEL.read_bytes()).hexdigest() == "7ab701e62e79b0d4a4d996417102b96907a25a9fd5ebe34f9ca1eb509ec4df42"


def test_build_installs_arm_runtime_and_applies_shadow_last() -> None:
    assert "py3-onnxruntime" in DOCKER
    assert "--no-deps openwakeword==0.6.0" in DOCKER
    assert "COPY models/wakeword ./models/wakeword" in DOCKER
    copy = "COPY apply_local_wake_shadow_v012101.py ./apply_local_wake_shadow_v012101.py"
    run = "python3 ./apply_local_wake_shadow_v012101.py"
    assert copy in DOCKER and run in DOCKER
    assert DOCKER.index("python3 ./apply_wake_capture_watchdog_v012101.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
