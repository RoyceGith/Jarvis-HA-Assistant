from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_plugin_settings_visibility_v01258.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")


def test_v01258_plugin_settings_visibility_build_order():
    assert "COPY apply_plugin_settings_visibility_v01258.py ./apply_plugin_settings_visibility_v01258.py" in DOCKER
    assert DOCKER.index("python3 ./apply_gmail_direct_v01257.py") < DOCKER.index("python3 ./apply_plugin_settings_visibility_v01258.py")
    assert DOCKER.index("python3 ./apply_plugin_settings_visibility_v01258.py") < DOCKER.index("python3 ./apply_release_bump_v01259.py")
    assert 'version="0.12.58"' in PATCH
    assert "HUD 0.12.58" in PATCH


def test_v01258_installed_plugin_settings_stay_compact():
    assert 'toggle.className = "plugin-settings-toggle"' in PATCH
    assert 'settings.className = "plugin-settings"' in PATCH
    assert 'row.querySelector(":scope > .plugin-settings")' in PATCH
    assert 'actions.prepend(toggle)' in PATCH
