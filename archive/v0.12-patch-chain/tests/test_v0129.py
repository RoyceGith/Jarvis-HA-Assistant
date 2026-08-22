from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_plugin_oauth_v0129.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")


def test_v0129_implements_mcp_oauth_discovery_and_pkce():
    for marker in (
        "resource_metadata=", "oauth-protected-resource", "oauth-authorization-server",
        "registration_endpoint", "def _oauth_pkce(", '"code_challenge_method": "S256"',
        '"resource": flow["resource"]',
    ):
        assert marker in PATCH


def test_v0129_validates_state_and_keeps_tokens_server_side():
    assert "PLUGIN_OAUTH_FLOWS.pop(state, None)" in PATCH
    assert "OAuth state is missing, expired, or already used" in PATCH
    assert "OAuth authorization-server issuer mismatch" in PATCH
    assert 'secrets_store[plugin_id] = access_token' in PATCH
    assert "access_token" not in PATCH[PATCH.index("def _oauth_popup_response"):PATCH.index("async def _oauth_start_for_target")]


def test_v0129_cloudflare_and_canva_are_connectable_but_google_stays_configured():
    assert PATCH.count('"oauth_connectable": True') >= 2
    assert '"Connect with Cloudflare"' in PATCH
    assert '"Connect with Canva"' in PATCH
    assert 'item["oauth_available"] = bool(item.get("oauth_connectable"))' in PATCH


def test_v0129_has_connect_reauthorize_signout_and_refresh_lifecycle():
    for marker in (
        "data-oauth-connect", "startPluginOAuth", "Reauthorize", "Sign out",
        "async def _refresh_plugin_oauth_token", "_plugin_oauth_refresh_loop",
        '/oauth/disconnect',
        '"Plugin OAuth engine operational"',
    ):
        assert marker in PATCH


def test_v0129_write_tools_remain_approval_gated():
    assert 'tool["permission"] = "write"' in PATCH
    assert 'tool["enabled"] = tool.get("permission") in {"read_only", "write"}' in PATCH
    assert "write actions approval-gated" in PATCH


def test_v0129_build_order_and_version():
    assert DOCKER.index("python3 ./apply_plugin_workspace_v0128.py") < DOCKER.index("python3 ./apply_plugin_oauth_v0129.py")
    assert DOCKER.index("python3 ./apply_plugin_oauth_v0129.py") < DOCKER.index("validate_inline_js.py ./app/static/index.html")
    assert "COPY apply_plugin_oauth_v0129.py ./apply_plugin_oauth_v0129.py" in DOCKER
    assert "./apply_plugin_oauth_v0129.py ./validate_inline_js.py" in DOCKER
    assert 'version: "0.12.9"' in CONFIG
