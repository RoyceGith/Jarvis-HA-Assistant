from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_release_bump_v01259.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")


def test_v01259_release_version_and_build_order():
    assert "COPY apply_release_bump_v01259.py ./apply_release_bump_v01259.py" in DOCKER
    assert DOCKER.index("python3 ./apply_plugin_settings_visibility_v01258.py") < DOCKER.index("python3 ./apply_release_bump_v01259.py")
    assert DOCKER.index("python3 ./apply_release_bump_v01259.py") < DOCKER.index("python3 ./apply_release_bump_v01260.py")
    assert 'version="0.12.59"' in PATCH
    assert "HUD 0.12.59" in PATCH
