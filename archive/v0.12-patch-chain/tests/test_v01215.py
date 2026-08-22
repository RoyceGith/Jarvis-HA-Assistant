from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_ingress_oauth_callback_retry_v01215.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_v01215_retries_only_the_ingress_callback_401_once():
    for marker in (
        "ingressCallbackRetryUsed=false",
        'popupUrl.origin!==window.location.origin',
        'popupUrl.pathname.endsWith(\"/api/plugin-oauth/callback\")',
        'popupUrl.searchParams.has(\"state\")',
        r"/\b401\b[\s\S]*unauthorized/i",
        "popup.location.replace(popupUrl.href)",
    ):
        assert marker in PATCH


def test_v01215_keeps_oauth_security_boundaries():
    assert "OAuth state" not in PATCH
    assert "code_verifier" not in PATCH
    assert "access_token" not in PATCH
    assert "600000" in PATCH


def test_v01215_versions_and_build_order():
    assert 'version: "0.12.15"' in CONFIG
    assert "ZBRANO v0.12.15" in README
    assert DOCKER.index("python3 ./apply_zbrano_identity_v01214.py") < DOCKER.index("python3 ./apply_ingress_oauth_callback_retry_v01215.py")
    assert DOCKER.index("python3 ./apply_ingress_oauth_callback_retry_v01215.py") < DOCKER.index("validate_inline_js.py ./app/static/index.html")
    assert "COPY apply_ingress_oauth_callback_retry_v01215.py ./apply_ingress_oauth_callback_retry_v01215.py" in DOCKER
