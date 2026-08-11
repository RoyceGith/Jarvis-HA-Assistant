import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPACT_PATCH = (ROOT / "jarvis/apply_catalog_and_plugin_compact_v01131.py").read_text(encoding="utf-8")
RELEASE_PATCH = (ROOT / "jarvis/apply_plugin_compact_repair_v01261.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_v01261_repairs_every_installed_plugin_row():
    assert 'if (row.classList.contains("compact-plugin")) continue;' not in COMPACT_PATCH
    assert "child !== head && child !== settings" in COMPACT_PATCH
    assert "for (const child of movable) settings.appendChild(child);" in COMPACT_PATCH
    assert "new MutationObserver(compactPluginRows)" in COMPACT_PATCH
    assert "pluginRowsObserver.observe(pluginListNode, {childList: true})" in COMPACT_PATCH


def test_v01261_release_version_and_build_order():
    assert "COPY apply_plugin_compact_repair_v01261.py ./apply_plugin_compact_repair_v01261.py" in DOCKER
    assert DOCKER.index("python3 ./apply_release_bump_v01260.py") < DOCKER.index("python3 ./apply_plugin_compact_repair_v01261.py")
    assert DOCKER.index("python3 ./apply_plugin_compact_repair_v01261.py") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.61"' in CONFIG
    assert MANIFEST["version"] == "0.12.61"
    assert "ZBRANO v0.12.61" in README
    assert 'version="0.12.61"' in RELEASE_PATCH
    assert "HUD 0.12.61" in RELEASE_PATCH
