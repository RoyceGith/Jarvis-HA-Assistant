import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_release_validator_build_fix_v01222.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01222_repairs_missing_validator_configuration():
    assert "COPY config.yaml ./config.yaml" in DOCKER
    assert DOCKER.index("COPY config.yaml ./config.yaml") < DOCKER.index("COPY validate_release_manifest.py")
    assert "python3 ./validate_release_manifest.py" in DOCKER
    assert "rm ./validate_release_manifest.py ./config.yaml" in DOCKER
    assert DOCKER.index("python3 ./validate_release_manifest.py") < DOCKER.index("rm ./validate_release_manifest.py ./config.yaml")


def test_v01222_aligns_every_release_marker():
    assert 'version: "0.12.22"' in CONFIG
    assert MANIFEST["version"] == "0.12.22"
    assert "ZBRANO v0.12.22" in README
    assert 'version="0.12.22"' in PATCH
    assert '"version": "0.12.22"' in PATCH
    assert "HUD 0.12.22" in PATCH


def test_v01222_build_fix_runs_before_manifest_validation():
    assert "COPY apply_release_validator_build_fix_v01222.py" in DOCKER
    assert DOCKER.index("python3 ./apply_release_memory_sync_v01221.py") < DOCKER.index("python3 ./apply_release_validator_build_fix_v01222.py")
    assert DOCKER.index("python3 ./apply_release_validator_build_fix_v01222.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert "&& rm ./apply_release_validator_build_fix_v01222.py" in DOCKER
