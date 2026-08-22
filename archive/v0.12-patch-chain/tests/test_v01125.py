from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH24 = (ROOT / "jarvis/apply_remove_legacy_new_chat_interceptor_v01124.py").read_text(encoding="utf-8")
PATCH25 = (ROOT / "jarvis/apply_build_recovery_v01125.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v01125_recovers_build_when_legacy_interceptor_is_already_absent():
    assert 'if start_marker in text:' in PATCH24
    assert "must(text, start_marker, 'legacy capture-phase New Chat interceptor')" not in PATCH24
    assert 'version="0.11.25"' in PATCH25
    assert 'HUD 0.11.25' in PATCH25
    assert 'apply_build_recovery_v01125.py' in DOCKER
    assert DOCKER.index('apply_remove_legacy_new_chat_interceptor_v01124.py') < DOCKER.index('apply_build_recovery_v01125.py')
    assert DOCKER.index('apply_build_recovery_v01125.py') < DOCKER.index('validate_new_chat_wiring.py ./app/static/index.html')
    assert 'version: "0.11.25"' in CONFIG
