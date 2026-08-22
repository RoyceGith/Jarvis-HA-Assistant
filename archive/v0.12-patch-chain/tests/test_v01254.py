import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_gmail_pre_registered_oauth_v01254.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
RUN = (ROOT / "jarvis/run.sh").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01254_accepts_pre_registered_google_oauth_client():
    assert "allow_pre_registered=False" in PATCH
    assert 'os.getenv("GOOGLE_OAUTH_CLIENT_ID"' in PATCH
    assert 'os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"' in PATCH
    assert '"token_endpoint_auth_method": "client_secret_post"' in PATCH


def test_v01254_requests_refresh_access_and_provider_scopes():
    assert 'resource_metadata.get("scopes_supported")' in PATCH
    assert 'query["scope"] = flow["scope"]' in PATCH
    assert '"access_type": "offline"' in PATCH
    assert '"prompt": "consent"' in PATCH
    assert '"include_granted_scopes": "true"' in PATCH


def test_v01254_exposes_gmail_connect_and_callback_setup():
    assert 'item.get("id") == "gmail-official"' in PATCH
    assert '"Connect with Google"' in PATCH
    assert "data-copy-google-callback" in PATCH
    assert "navigator.clipboard.writeText(callback)" in PATCH
    assert '"Gmail OAuth configuration"' in PATCH


def test_v01254_keeps_google_secrets_out_of_source_defaults():
    assert 'google_oauth_client_id: ""' in CONFIG
    assert 'google_oauth_client_secret: ""' in CONFIG
    assert 'google_oauth_client_secret: "password"' in CONFIG
    assert "GOOGLE_OAUTH_CLIENT_ID" in RUN
    assert "GOOGLE_OAUTH_CLIENT_SECRET" in RUN


def test_v01254_prioritizes_home_assistant_for_device_power_language():
    assert "def is_home_assistant_priority_intent(message: str)" in PATCH
    assert 're.search(r"\\b(?:turn|switch)\\s+(?:on|off)\\b"' in PATCH
    assert '"repository", "github", "git branch", "commit", "push"' in PATCH
    assert "return home_assistant_priority_tools()" in PATCH
    assert "runtime_chat_tools(message=message)" in PATCH
    assert "runtime_chat_tools(search_mode, message)" in PATCH
    assert "priority_system_instructions(effective_system_instructions(), message)" in PATCH
    assert "allowed_names.update(HOME_ASSISTANT_PRIORITY_TOOL_NAMES)" in PATCH


def test_v01254_coalesces_home_assistant_tool_rounds_into_one_activity():
    assert '"local-home-assistant"' in PATCH
    assert 'activity_meta.get("provider") == "home_assistant"' in PATCH
    assert 'eventData.provider === "home_assistant"' in PATCH
    assert '? "local-home-assistant"' in PATCH


def test_v01254_shared_files_activity_is_semantic_and_acknowledged():
    assert '"files": _tab_activity_value_revision([' in PATCH
    assert 'for key in ("file_id", "name", "mime_type", "size", "sha256", "created_at")' in PATCH
    assert '#automations-panel::before, #files-panel::before { display: none; }' in PATCH
    assert 'if (isViewed(binding.button, binding.panel)) clear(binding.button);' in PATCH
    assert 'requestAnimationFrame(() => clear(button));' in PATCH


def test_v01254_runs_after_v01253_and_aligns_release():
    name = "apply_gmail_pre_registered_oauth_v01254.py"
    assert f"COPY {name}" in DOCKER
    assert DOCKER.index("python3 ./apply_voice_latency_and_activity_revisions_v01253.py") < DOCKER.index(f"python3 ./{name}")
    assert DOCKER.index(f"python3 ./{name}") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.54"' in CONFIG
    assert MANIFEST["version"] == "0.12.54"
    assert "ZBRANO v0.12.54" in README
    assert 'version="0.12.54"' in PATCH
    assert "HUD 0.12.54" in PATCH
