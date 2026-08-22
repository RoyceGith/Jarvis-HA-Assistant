import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_local_plugin_icons_and_composer_stack_v01230.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))
ICON_DIR = ROOT / "jarvis/app/static/plugin-icons"


def test_v01230_bundles_current_enabled_plugin_icons():
    for name in ("playwright", "github", "cloudflare"):
        icon = ICON_DIR / f"{name}.svg"
        assert icon.is_file()
        assert "<svg" in icon.read_text(encoding="utf-8")
        assert f'plugin-icons/{name}.svg' in PATCH


def test_v01230_bundles_supported_catalog_icons_and_fallbacks():
    for name in ("gmail", "googledrive", "googlecalendar", "googlechat"):
        assert (ICON_DIR / f"{name}.svg").is_file()
    assert '"https://cdn.simpleicons.org/canva/00C4CC": ""' in PATCH
    assert '"https://cdn.simpleicons.org/adobe/FF0000": ""' in PATCH
    assert '"https://cdn.simpleicons.org/googleworkspace/4285F4": ""' in PATCH


def test_v01230_places_controls_inside_textarea_stack():
    assert 'class="composer-input-stack"' in PATCH
    assert "external composer context row" in PATCH
    assert 'class="composer-context-row"' in PATCH
    assert 'id="web-search-mode"' in PATCH


def test_v01230_keeps_diagnostic_chats_out_of_user_history():
    assert 'INTERNAL_CHAT_SESSION_PREFIXES = ("zbrano-diagnostic-",)' in PATCH
    assert "def purge_internal_chat_sessions" in PATCH
    assert "if not is_internal_chat_session(request.session_id)" in PATCH
    assert "if not is_internal_chat_session(session_id)" in PATCH
    assert "internal chat API filter" in PATCH
    assert "clear_chat_history(chat_session)" in PATCH
    assert "cancellation-safe diagnostic chat cleanup" in PATCH


def test_v01230_runs_last_and_aligns_release_markers():
    assert "COPY apply_local_plugin_icons_and_composer_stack_v01230.py" in DOCKER
    assert DOCKER.index("python3 ./apply_frontend_cache_refresh_v01229.py") < DOCKER.index("python3 ./apply_local_plugin_icons_and_composer_stack_v01230.py")
    assert DOCKER.index("python3 ./apply_local_plugin_icons_and_composer_stack_v01230.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.30"' in CONFIG
    assert MANIFEST["version"] == "0.12.30"
    assert "ZBRANO v0.12.30" in README
    assert 'version="0.12.30"' in PATCH
    assert "HUD 0.12.30" in PATCH
