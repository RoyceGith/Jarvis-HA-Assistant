from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_catalog_and_plugin_compact_v01131.py").read_text(encoding="utf-8")
BUILD_FIX_29 = (ROOT / "jarvis/apply_github_tool_approval_build_fix_v01129.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v01129_policy_preserves_catalog_backend_for_later_releases():
    assert '"PLUGIN_CATALOG_CACHE_PATH ="' in BUILD_FIX_29
    assert "active MCP/catalog boundary" in BUILD_FIX_29
    assert "catalog preservation verification failed" in BUILD_FIX_29
    assert "'@app.get(\"/api/plugins\")'" not in BUILD_FIX_29.split("old_active_boundary =", 1)[-1].split("new_active_boundary =", 1)[-1].split("if old_active_boundary", 1)[0]


def test_v01131_catalog_always_merges_featured_entries():
    assert "def _catalog_with_featured(items):" in PATCH
    assert "return _catalog_with_featured(cached), True, None" in PATCH
    assert "FEATURED_REMOTE_PLUGINS" in PATCH
    assert 'fetch_marker = "async def _fetch_plugin_catalog(force=False):\\n"' in PATCH


def test_v01131_installed_plugins_are_compact_by_default():
    assert 'zbrano-v01131-plugin-compact' in PATCH
    assert 'plugin-settings-toggle' in PATCH
    assert '.plugin-row.compact-plugin .plugin-settings{display:none' in PATCH
    assert '.plugin-row.compact-plugin.open .plugin-settings{display:block' in PATCH
    assert 'toggle.textContent = "Settings"' in PATCH
    assert 'event.stopImmediatePropagation()' in PATCH


def test_v01131_patch_runs_after_shared_files_recovery():
    assert 'apply_catalog_and_plugin_compact_v01131.py' in DOCKER
    assert DOCKER.index('python3 ./apply_github_tool_approval_build_fix_v01129.py') < DOCKER.index('python3 ./apply_github_tool_approval_policy_v01129.py')
    assert DOCKER.index('python3 ./apply_shared_files_runtime_recovery_v01130.py') < DOCKER.index('python3 ./apply_catalog_and_plugin_compact_v01131.py')
    assert DOCKER.index('python3 ./apply_catalog_and_plugin_compact_v01131.py') < DOCKER.index('validate_inline_js.py ./app/static/index.html')


def test_v01131_release_version():
    assert 'version: "0.11.31"' in CONFIG
