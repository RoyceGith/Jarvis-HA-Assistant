import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_clean_interface_v012110.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_scanline_overlay_is_removed_in_every_theme() -> None:
    assert "body::after" in PATCH
    assert "LIGHT_SCANLINES" in PATCH
    assert 'frontend.replace(SCANLINES, "", 1)' in PATCH
    assert 'frontend.replace(LIGHT_SCANLINES, "", 1)' in PATCH
    assert "scanline overlay remains" in PATCH


def test_neural_background_and_component_borders_are_untouched() -> None:
    assert "#brain-network" not in PATCH
    assert "border:" not in PATCH


def test_release_and_build_order_are_aligned() -> None:
    assert 'version: "0.12.110"' in CONFIG
    assert MANIFEST["version"] == "0.12.110"
    copy = "COPY apply_clean_interface_v012110.py ./apply_clean_interface_v012110.py"
    run = "python3 ./apply_clean_interface_v012110.py"
    assert copy in DOCKER and run in DOCKER
    assert DOCKER.index("python3 ./apply_real_room_wake_model_v012109.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
