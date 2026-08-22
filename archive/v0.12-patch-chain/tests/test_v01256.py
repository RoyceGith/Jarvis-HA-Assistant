import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_gmail_oauth_least_privilege_v01256.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_v01256_uses_exact_gmail_scope_allowlist():
    assert "GMAIL_MCP_OAUTH_SCOPES = (" in PATCH
    assert '"https://www.googleapis.com/auth/gmail.readonly"' in PATCH
    assert '"https://www.googleapis.com/auth/gmail.compose"' in PATCH
    assert '" ".join(GMAIL_MCP_OAUTH_SCOPES)' in PATCH


def test_v01256_rejects_and_revokes_noncompliant_grants():
    assert "if granted != required:" in PATCH
    assert "await _revoke_rejected_oauth_token(flow, token)" in PATCH
    assert "missing = sorted(required - granted)" in PATCH
    assert "unexpected = sorted(granted - required)" in PATCH
    assert "await _validate_gmail_oauth_grant(flow, token)" in PATCH


def test_v01256_quarantines_old_broad_tokens():
    assert "async def enforce_stored_gmail_scope_policy()" in PATCH
    assert "secrets.pop(plugin_id, None)" in PATCH
    assert "records.pop(plugin_id, None)" in PATCH
    assert "Gmail OAuth scope policy changed; reconnect required" in PATCH
    assert "await enforce_stored_gmail_scope_policy()" in PATCH


def test_v01256_forces_account_selection_without_incremental_scopes():
    assert '"prompt": "select_account consent"' in PATCH
    assert '"include_granted_scopes": "true"' in PATCH
    assert 'query.update({"access_type": "offline", "prompt": "select_account consent"})' in PATCH


def test_v01256_reports_identity_and_scopes_without_credentials():
    assert '"https://gmail.googleapis.com/gmail/v1/users/me/profile"' in PATCH
    assert '"oauth_account": oauth_account' in PATCH
    assert '"oauth_scopes": sorted(' in PATCH
    assert "OAuth account: ${esc(p.oauth_account" in PATCH
    assert "Granted scopes: ${esc((p.oauth_scopes" in PATCH


def test_v01256_smooths_ingress_callback_retry():
    assert 'popup.document.title="Completing authorization"' in PATCH
    assert "Returning securely through Home Assistant" in PATCH


def test_v01256_runs_after_v01255_and_aligns_release():
    name = "apply_gmail_oauth_least_privilege_v01256.py"
    assert f"COPY {name}" in DOCKER
    assert DOCKER.index("python3 ./apply_customizable_entity_columns_v01255.py") < DOCKER.index(f"python3 ./{name}")
    assert DOCKER.index(f"python3 ./{name}") < DOCKER.index("python3 ./validate_release_manifest.py")
    assert 'version: "0.12.56"' in CONFIG
    assert MANIFEST["version"] == "0.12.56"
    assert "ZBRANO v0.12.56" in README
    assert 'version="0.12.56"' in PATCH
    assert "HUD 0.12.56" in PATCH
