from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_ha_live_evidence_and_climate_confirmation_v01293.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")


def test_climate_power_confirmation_accepts_active_hvac_modes() -> None:
    assert 'if domain == "climate"' in PATCH
    assert '{"", "off", "unknown", "unavailable"}' in PATCH
    assert "_wait_for_ha_power_state(entity_id, domain, turn_on" in PATCH
    assert '"success": _ha_power_state_matches(domain, verified.get("state"), turn_on)' in PATCH


def test_history_has_approved_current_state_fallback() -> None:
    assert "for entity_id, state in ha_ws.state_cache.items()" in PATCH
    assert "not effective_entity_access(clean_id)" in PATCH
    assert '"source": "current"' in PATCH
    assert '"journal_count": len(journal)' in PATCH
    assert "evidence.sort(" in PATCH


def test_release_and_build_order_are_aligned() -> None:
    copy = "COPY apply_ha_live_evidence_and_climate_confirmation_v01293.py ./apply_ha_live_evidence_and_climate_confirmation_v01293.py"
    run = "python3 ./apply_ha_live_evidence_and_climate_confirmation_v01293.py"
    assert copy in DOCKER
    assert run in DOCKER
    assert DOCKER.index("python3 ./apply_history_recent_entity_refresh_v01292.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
