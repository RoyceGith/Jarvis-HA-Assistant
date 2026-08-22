import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_two_way_telegram_v01289.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_two_way_telegram_uses_home_assistant_event_stream() -> None:
    assert '"telegram_text"' in PATCH
    assert '"telegram_command"' in PATCH
    assert '"type": "subscribe_events"' in PATCH
    assert 'HA_WS_URL' in PATCH
    assert '"telegram_bot",' in PATCH
    assert '"send_message",' in PATCH
    assert "Bot tokens remain" not in PATCH


def test_pairing_and_allowlist_are_required() -> None:
    assert 'secrets.token_hex(4).upper()' in PATCH
    assert 'time.time() + 600' in PATCH
    assert 'if not linked:' in PATCH
    assert 'messages_rejected' in PATCH
    assert '/link ' in PATCH
    assert 'linked_chats' in PATCH


def test_inbound_processing_is_bounded_and_not_polling_the_model() -> None:
    assert 'await asyncio.wait_for(run_jarvis(text, session_id), timeout=120.0)' in PATCH
    assert 'if lock.locked()' in PATCH
    assert '_telegram_event_duplicate' in PATCH
    worker = PATCH.split('async def telegram_inbound_worker()', 1)[1].split('@app.get("/api/telegram-inbound")', 1)[0]
    assert 'run_jarvis(' not in worker
    assert 'await asyncio.sleep(backoff)' in worker
    assert 'backoff = min(backoff * 2.0, 30.0)' in worker


def test_remote_approval_is_an_explicit_policy() -> None:
    assert 'remote_approvals_enabled: bool = False' in PATCH
    assert 'if not data["settings"].get("remote_approvals_enabled")' in PATCH
    assert 'Remote approvals are disabled' in PATCH
    assert 'id="telegram-remote-approvals"' in PATCH


def test_ui_and_lifecycle_are_wired() -> None:
    for marker in (
        'id="telegram-inbound-form"',
        'id="telegram-generate-code"',
        'id="telegram-linked-chats"',
        '@app.on_event("startup")',
        '@app.on_event("shutdown")',
        'name="zbrano-telegram-inbound"',
    ):
        assert marker in PATCH


def test_release_and_build_order_are_aligned() -> None:
    config_version = CONFIG.split('version: "', 1)[1].split('"', 1)[0]
    assert tuple(map(int, config_version.split("."))) >= (0, 12, 89)
    assert tuple(map(int, MANIFEST["version"].split("."))) >= (0, 12, 89)
    copy = "COPY apply_two_way_telegram_v01289.py ./apply_two_way_telegram_v01289.py"
    run = "python3 ./apply_two_way_telegram_v01289.py"
    assert copy in DOCKER
    assert run in DOCKER
    assert DOCKER.index("python3 ./apply_month_reminder_status_v01288.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
