import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_composer_web_plugins_v01228.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01228_places_compact_web_selector_below_prompt():
    assert 'class="composer-context-row"' in PATCH
    assert '<option value="auto">Auto</option>' in PATCH
    assert '<option value="search">On</option>' in PATCH
    assert '<option value="off">Off</option>' in PATCH


def test_v01228_renders_only_enabled_plugin_indicators():
    assert 'filter(plugin=>plugin&&plugin.enabled)' in PATCH
    assert 'id="composer-plugin-icons"' in PATCH
    assert "available_to_chat" in PATCH
    assert "enabled_tool_count" in PATCH
    assert "visibleLimit=7" in PATCH


def test_v01228_keeps_indicators_current_and_accessible():
    assert "renderComposerPluginIndicators(ps)" in PATCH
    assert 'aria-label="Enabled plugins"' in PATCH
    assert 'document.getElementById("plugins-tab")?.click()' in PATCH
    assert 'referrerpolicy="no-referrer"' in PATCH


def test_v01228_runs_last_and_aligns_release_markers():
    assert "COPY apply_composer_web_plugins_v01228.py" in DOCKER
    assert DOCKER.index("python3 ./apply_playwright_host_port_fix_v01227.py") < DOCKER.index("python3 ./apply_composer_web_plugins_v01228.py")
    assert DOCKER.index("python3 ./apply_composer_web_plugins_v01228.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.28"' in CONFIG
    assert MANIFEST["version"] == "0.12.28"
    assert "ZBRANO v0.12.28" in README
    assert 'version="0.12.28"' in PATCH
    assert "HUD 0.12.28" in PATCH
