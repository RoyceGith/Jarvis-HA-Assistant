import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_semantic_tab_activity_v01251.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01251_removes_generic_dom_mutation_detection():
    semantic = PATCH.split("semantic_runtime = r'''", 1)[1].split("'''", 1)[0]
    assert "MutationObserver" not in semantic
    assert "observer.observe" not in semantic
    assert 'id="zbrano-v01251-semantic-tab-activity"' in semantic
    assert 'id="zbrano-v01248-tab-activity"' not in semantic


def test_v01251_marks_only_explicit_meaningful_events():
    assert 'window.zbranoMarkTabChanged?.("chat-tab")' in PATCH
    assert 'path.includes("/api/files/")' in PATCH
    assert 'path.includes("/api/plugins")' in PATCH
    assert 'path.includes("/api/automations")' in PATCH
    assert 'path.includes("/api/notifications")' in PATCH
    assert 'event.data?.type === "zbrano-plugin-oauth"' in PATCH
    assert "checkNotificationActivity" in PATCH


def test_v01251_does_not_mark_background_get_refreshes():
    assert '!["GET", "HEAD", "OPTIONS"].includes(method)' in PATCH
    assert 'const nativeFetch = window.fetch.bind(window)' in PATCH
    assert 'nativeFetch("api/notifications/activity"' in PATCH
    assert "setInterval(checkNotificationActivity, 15000)" in PATCH


def test_v01251_preserves_tab_clear_behavior_and_telegram_delivery():
    assert 'button.addEventListener("click"' in PATCH
    assert "requestAnimationFrame(() => clear(button))" in PATCH
    assert "isViewed(binding.button, binding.panel)" in PATCH
    assert 'service_domain = "telegram_bot" if channel["platform"] == "telegram" else "notify"' in PATCH


def test_v01251_runs_after_v01250_and_aligns_release():
    name = "apply_semantic_tab_activity_v01251.py"
    assert f"COPY {name}" in DOCKER
    assert DOCKER.index("python3 ./apply_telegram_service_routing_v01250.py") < DOCKER.index(f"python3 ./{name}")
    assert DOCKER.index(f"python3 ./{name}") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.51"' in CONFIG
    assert MANIFEST["version"] == "0.12.51"
    assert "ZBRANO v0.12.51" in README
    assert 'version="0.12.51"' in PATCH
    assert "HUD 0.12.51" in PATCH
