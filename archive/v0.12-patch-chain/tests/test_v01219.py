from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_modern_controls_and_neural_settings_v01219.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_v01219_replaces_green_buttons_without_recoloring_chat_messages():
    assert "modern neutral controls" in PATCH
    assert "linear-gradient(180deg, rgba(43, 52, 63" in PATCH
    assert "button:focus-visible" in PATCH
    assert ".danger-action, #stop-button" in PATCH
    assert "Chat message colors intentionally remain unchanged" in PATCH
    assert ".message {" not in PATCH
    assert ".message.jarvis" not in PATCH


def test_v01219_adds_persistent_neural_personalization():
    for marker in (
        'id="neural-style"',
        'id="neural-scale"',
        'id="neural-node-size"',
        'id="neural-opacity"',
        '"neural_style": "constellation"',
        "neural_scale: float",
        "neural_node_size: float",
        "neural_opacity: float",
        '"neural_opacity": request.neural_opacity',
        'CustomEvent("zbrano-neural-change")',
    ):
        assert marker in PATCH


def test_v01219_offers_four_distinct_renderer_styles():
    for style in ("constellation", "mesh", "orbital", "minimal"):
        assert f'value="{style}"' in PATCH
    assert 'neuralStyleName === "orbital"' in PATCH
    assert 'neuralStyleName === "minimal"' in PATCH
    assert 'neuralStyleName === "mesh"' in PATCH


def test_v01219_versions_and_build_order():
    assert 'version: "0.12.19"' in CONFIG
    assert "ZBRANO v0.12.19" in README
    assert "COPY apply_modern_controls_and_neural_settings_v01219.py" in DOCKER
    assert DOCKER.index("python3 ./apply_workshop_bulk_edit_capacity_v01218.py") < DOCKER.index("python3 ./apply_modern_controls_and_neural_settings_v01219.py")
    assert DOCKER.index("python3 ./apply_modern_controls_and_neural_settings_v01219.py") < DOCKER.index("validate_inline_js.py ./app/static/index.html")
    assert "&& rm ./apply_modern_controls_and_neural_settings_v01219.py" in DOCKER
