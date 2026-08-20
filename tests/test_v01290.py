import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_real_automation_engine_v01290.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_history_uses_live_events_and_entity_identity() -> None:
    assert "HA_LIVE_EVENTS: deque" in PATCH
    assert "_dispatch_ha_state_changed(event)" in PATCH
    assert 'raw_by_entity[identity] = raw_series' in PATCH
    assert 'return_exceptions=True' in PATCH
    assert 'Logbook unavailable:' in PATCH
    assert '@app.get("/api/ha/live-events")' in PATCH
    assert 'id="zbrano-v01290-live-history"' in PATCH
    assert 'if(input.value.trim()){await window.zbranoHaHistory?.load();return}' in PATCH
    assert 'data.warnings.join' in PATCH


def test_real_engine_is_event_driven_without_model_polling() -> None:
    assert "async def _automation_evaluate_state_change" in PATCH
    assert "async def _automation_commit_match" in PATCH
    assert 'AUTOMATION_PENDING_TASKS' in PATCH
    evaluator = PATCH.split("async def _automation_evaluate_state_change", 1)[1].split('@app.post("/api/automations/suggestions', 1)[0]
    assert "run_jarvis(" not in evaluator
    assert "create_openai_response(" not in evaluator


def test_engine_enforces_structured_conditions_and_authority() -> None:
    for marker in (
        'any_change|changes_to|equals|not_equals|above|below',
        '_automation_presence_confirmed',
        '_automation_rate_available',
        '_automation_autonomous_allowed',
        'AUTOMATION_AUTONOMOUS_DOMAINS',
        'risk == "high"',
        'operating_mode") != "selective_autonomy"',
        'payload["action_entity"] = payload["action_entity"].strip().lower()',
    ):
        assert marker in PATCH
    assert 'evaluator intentionally inactive' in PATCH
    assert 'p.get("engine", {}).get("status") in {"active", "waiting_for_home_assistant"}' in PATCH


def test_existing_rules_remain_disabled_and_suggestions_are_decidable() -> None:
    assert 'enabled: bool = False' in PATCH
    assert 'if payload["enabled"] and not payload["trigger_entity"]' in PATCH
    assert '@app.post("/api/automations/suggestions/{suggestion_id}/approve")' in PATCH
    assert '@app.post("/api/automations/suggestions/{suggestion_id}/dismiss")' in PATCH
    assert 'data-suggestion-approve' in PATCH
    assert 'data-suggestion-dismiss' in PATCH


def test_light_theme_completed_state_is_dark_green() -> None:
    assert ':root[data-theme="light"] .calendar-reminder-state[data-state="completed"]' in PATCH
    assert ':root[data-theme="light"] .calendar-month-reminder-state[data-state="completed"]' in PATCH
    assert ':root[data-theme="light"] .calendar-reminder-badge[data-status="delivered"]' in PATCH
    assert '#126b3a' in PATCH


def test_month_view_can_delete_appointments() -> None:
    assert 'data-calendar-month-delete' in PATCH
    assert 'Delete this appointment and cancel its pending reminders?' in PATCH
    assert 'remove.dataset.calendarMonthDelete' in PATCH
    assert 'await loadCalendar()' in PATCH


def test_release_and_build_order_are_aligned() -> None:
    assert 'version: "0.12.90"' in CONFIG
    assert MANIFEST["version"] == "0.12.90"
    copy = "COPY apply_real_automation_engine_v01290.py ./apply_real_automation_engine_v01290.py"
    run = "python3 ./apply_real_automation_engine_v01290.py"
    assert copy in DOCKER
    assert run in DOCKER
    assert DOCKER.index("python3 ./apply_two_way_telegram_v01289.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
