from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_navigation_settings_and_chat_wrap_v01220.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_v01220_orders_navigation_and_detaches_developer():
    ordered = (
        'id="chat-tab" class="active">Chat</button>\n'
        '    <button id="files-tab">Shared Files</button>\n'
        '    <button id="plugins-tab">Plugins</button>\n'
        '    <button id="entities-tab">Entities</button>\n'
        '    <button id="automations-tab">Automations</button>\n'
        '    <button id="settings-tab">Settings</button>\n'
        '    <button id="developer-tab">Developer</button>'
    )
    assert ordered in PATCH
    assert "#developer-tab {" in PATCH
    assert "margin-left: auto" in PATCH


def test_v01220_adds_accessible_settings_categories():
    for category in ("appearance", "voice", "responses", "instructions", "playback", "memory"):
        assert f'data-settings-target="{category}"' in PATCH
    assert 'role="tablist"' in PATCH
    assert 'role="tab"' in PATCH
    assert 'aria-selected="true"' in PATCH
    assert "ArrowLeft" in PATCH and "ArrowRight" in PATCH
    assert "zbrano_settings_category_v1" in PATCH


def test_v01220_keeps_empty_chat_neuron_full_then_uses_saved_opacity():
    assert ".core-stage.neuron-intense #brain-network { opacity: 1 !important; }" in PATCH
    assert "setNeuronIntensity(false);" in PATCH
    assert 'document.body.classList.remove("jarvis-input-active");' in PATCH
    assert "--neural-opacity" not in PATCH.split(".core-stage.neuron-intense #brain-network", 1)[1].split("}", 1)[0]


def test_v01220_wraps_assistant_responses_without_recoloring_them():
    assert ".message.jarvis pre" in PATCH
    assert "overflow-wrap: anywhere" in PATCH
    assert "word-break: break-word" in PATCH
    assert "white-space: break-spaces" in PATCH
    assert "color:" not in PATCH.split(".message.jarvis,", 1)[1].split(".core-stage.neuron-intense", 1)[0]


def test_v01220_versions_and_build_order():
    assert 'version: "0.12.20"' in CONFIG
    assert "ZBRANO v0.12.20" in README
    assert "COPY apply_navigation_settings_and_chat_wrap_v01220.py" in DOCKER
    assert DOCKER.index("python3 ./apply_modern_controls_and_neural_settings_v01219.py") < DOCKER.index("python3 ./apply_navigation_settings_and_chat_wrap_v01220.py")
    assert DOCKER.index("python3 ./apply_navigation_settings_and_chat_wrap_v01220.py") < DOCKER.index("validate_inline_js.py ./app/static/index.html")
    assert "&& rm ./apply_navigation_settings_and_chat_wrap_v01220.py" in DOCKER
