from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_plugin_workspace_v0128.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v0128_installed_plugins_are_first_internal_view():
    assert PATCH.index('id="plugins-installed-view"') < PATCH.index('id="plugins-browse-view"')
    for marker in ('id="plugins-installed-tab"', 'id="plugins-browse-tab"', "showPluginView"):
        assert marker in PATCH


def test_v0128_catalog_respects_installed_state():
    assert "if(item.installed)" in PATCH
    assert 'item.installed_enabled?"Installed · enabled":"Installed · disabled"' in PATCH
    assert "await Promise.all([loadPlugins(),loadCatalog(false)])" in PATCH


def test_v0128_adds_brand_icons_with_safe_fallbacks():
    for marker in ("def plugin_icon_url(", "function pluginIconMarkup(", "activateIconFallbacks", "plugin-icon-fallback"):
        assert marker in PATCH
    assert PATCH.count('"icon_url": plugin_icon_url(title, url)') == 2


def test_v0128_expands_official_remote_catalog_without_fake_install_buttons():
    for plugin_id in ("gmail-official", "google-drive-official", "google-calendar-official", "canva-official", "cloudflare-official", "adobe-analytics-official"):
        assert f'"id": "{plugin_id}"' in PATCH
    assert "while pages < 10" in PATCH
    assert "result[:500]" in PATCH
    assert 'entry.get("installable") is False' in PATCH
    assert "OAuth setup required" in PATCH


def test_v0128_build_order_and_version():
    assert DOCKER.index("python3 ./apply_persistent_chat_attachment_labels_v0127.py") < DOCKER.index("python3 ./apply_plugin_workspace_v0128.py")
    assert DOCKER.index("python3 ./apply_plugin_workspace_v0128.py") < DOCKER.index("validate_inline_js.py ./app/static/index.html")
    assert "COPY apply_plugin_workspace_v0128.py ./apply_plugin_workspace_v0128.py" in DOCKER
    assert "./apply_plugin_workspace_v0128.py ./validate_inline_js.py" in DOCKER
    assert 'version: "0.12.8"' in CONFIG
