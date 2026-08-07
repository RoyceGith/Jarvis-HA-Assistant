from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH26 = (ROOT / "jarvis/apply_plugin_runtime_dom_fix_v01126.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v01126_moves_plugin_runtime_out_of_head():
    assert 'zbrano-v01126-plugin-runtime' in PATCH26
    assert 'text.find("</script>", runtime_start)' in PATCH26
    assert 'runtime = text[runtime_start:first_script_close].strip()' in PATCH26
    assert 'runtime_end_marker' not in PATCH26
    assert 'plugin runtime must execute after body DOM exists' in PATCH26
    assert 'stale plugin DOM lookup in head' in PATCH26
    assert 'unsafe document.body fallback in head' in PATCH26


def test_v01126_is_wired_after_v01125_and_before_validators():
    assert 'apply_plugin_runtime_dom_fix_v01126.py' in DOCKER
    assert DOCKER.index('apply_build_recovery_v01125.py') < DOCKER.index('apply_plugin_runtime_dom_fix_v01126.py')
    assert DOCKER.index('apply_plugin_runtime_dom_fix_v01126.py') < DOCKER.index('validate_inline_js.py ./app/static/index.html')
    assert 'version: "0.11.26"' in CONFIG
