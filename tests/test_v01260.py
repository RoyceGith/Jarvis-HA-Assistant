from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_release_bump_v01260.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github/workflows/build.yaml").read_text(encoding="utf-8")


def test_v01260_uses_prebuilt_home_assistant_image():
    assert 'image: "ghcr.io/roycegith/jarvis-ha-assistant"' in CONFIG
    assert "home-assistant/builder/actions/build-image@2026.06.0" in WORKFLOW
    assert "home-assistant/builder/actions/publish-multi-arch-manifest@2026.06.0" in WORKFLOW
    assert "context: ./jarvis" in WORKFLOW
    assert "packages: write" in WORKFLOW
    assert "version=${{ steps.info.outputs.version }}" in WORKFLOW
    assert "version: ${{ steps.normalize.outputs.version }}" in WORKFLOW


def test_v01260_release_version_and_build_order():
    assert "COPY apply_release_bump_v01260.py ./apply_release_bump_v01260.py" in DOCKER
    assert DOCKER.index("python3 ./apply_release_bump_v01259.py") < DOCKER.index("python3 ./apply_release_bump_v01260.py")
    assert DOCKER.index("python3 ./apply_release_bump_v01260.py") < DOCKER.index("python3 ./apply_plugin_compact_repair_v01261.py")
    assert 'version="0.12.60"' in PATCH
    assert "HUD 0.12.60" in PATCH
