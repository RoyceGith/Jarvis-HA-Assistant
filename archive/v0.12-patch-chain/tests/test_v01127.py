from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH27 = (ROOT / "jarvis/apply_runtime_order_fix_v01127.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v01127_restores_catalog_and_shared_runtime_order():
    assert 'zbrano-v01126-plugin-runtime' in PATCH27
    assert 'const baseCatalogCard = catalogCard;' in PATCH27
    assert 'function catalogCard(item)' in PATCH27
    assert 'const tab=document.getElementById("files-tab")' in PATCH27
    assert 'catalogCard must be defined before override' in PATCH27
    assert 'plugin runtime still executes after Shared Files runtime' in PATCH27


def test_v01127_is_wired_after_v01126_and_before_validators():
    assert 'apply_runtime_order_fix_v01127.py' in DOCKER
    assert DOCKER.index('apply_plugin_runtime_dom_fix_v01126.py') < DOCKER.index('apply_runtime_order_fix_v01127.py')
    assert DOCKER.index('apply_runtime_order_fix_v01127.py') < DOCKER.index('validate_inline_js.py ./app/static/index.html')
    assert 'version: "0.11.27"' in CONFIG
