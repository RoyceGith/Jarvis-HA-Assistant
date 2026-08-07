from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_plugin_manager_recovery_v01128.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v01128_removes_obsolete_plugins_recovery_router():
    assert 'jarvis-v0102-tab-recovery' in PATCH
    assert 'legacy capture-phase tab recovery still present' in PATCH
    assert 'pluginsTab.addEventListener("click",async()=>{showPanel("plugins");await Promise.all([loadPlugins(),loadCatalog(false)])});' in PATCH


def test_v01128_plugins_panel_scrolls_and_reports_chat_availability():
    assert '#plugins-panel {' in PATCH
    assert 'overflow-y: auto;' in PATCH
    assert 'Available to chat' in PATCH
    assert 'Not available to chat' in PATCH
    assert 'enabled_tool_count' in PATCH
    assert '"available_to_chat": bool(p.get("enabled") and enabled_tool_count)' in PATCH


def test_v01128_bounds_catalog_latency():
    assert 'while pages < 3:' in PATCH
    assert 'timeout=httpx.Timeout(4.0, connect=2.0)' in PATCH
    assert 'if cached is not None:' in PATCH
    assert 'while pages < 20:' in PATCH


def test_v01128_is_wired_after_v01127_before_validators():
    assert 'apply_plugin_manager_recovery_v01128.py' in DOCKER
    assert DOCKER.index('apply_runtime_order_fix_v01127.py') < DOCKER.index('apply_plugin_manager_recovery_v01128.py')
    assert DOCKER.index('apply_plugin_manager_recovery_v01128.py') < DOCKER.index('validate_inline_js.py ./app/static/index.html')
    assert 'version: "0.11.28"' in CONFIG
