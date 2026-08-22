from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_zbrano_identity_v01214.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_v01214_uses_zbrano_as_runtime_identity():
    assert 'title=\"ZBRANO\"' in PATCH
    assert "You are ZBRANO, a practical workshop intelligence core assistant." in PATCH
    assert '\"name\": \"zbrano-workshop-assistant\"' in PATCH
    assert '\"name\":\"ZBRANO Plugin Manager\"' in PATCH
    assert "X-ZBRANO-Voice" in PATCH


def test_v01214_updates_addon_identity_and_version():
    assert 'name: "ZBRANO"' in CONFIG
    assert 'version: "0.12.14"' in CONFIG
    assert "Local ZBRANO intelligence core assistant" in CONFIG
    assert "ZBRANO v0.12.14" in README


def test_v01214_preserves_upgrade_compatibility_identifiers():
    assert 'slug: "jarvis_workshop_assistant"' in CONFIG
    assert 'ROOT = Path("/opt/jarvis")' in PATCH
    assert "run_jarvis" not in PATCH
    assert "existing GitHub repository name remain unchanged" in README


def test_v01214_build_order():
    assert DOCKER.index("python3 ./apply_release_alignment_v01213.py") < DOCKER.index("python3 ./apply_zbrano_identity_v01214.py")
    assert DOCKER.index("python3 ./apply_zbrano_identity_v01214.py") < DOCKER.index("validate_inline_js.py ./app/static/index.html")
    assert "COPY apply_zbrano_identity_v01214.py ./apply_zbrano_identity_v01214.py" in DOCKER
