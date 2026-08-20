import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (ROOT / "jarvis/apply_telegram_chat_id_and_entity_search_v01291.py").read_text(encoding="utf-8")
DOCKER = (ROOT / "jarvis/Dockerfile").read_text(encoding="utf-8")
CONFIG = (ROOT / "jarvis/config.yaml").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


def test_telegram_reply_uses_chat_id() -> None:
    assert "deprecated Telegram target payload" in PATCH
    assert '{"chat_id": int(chat_id), "message": part}' in PATCH
    assert "still contains the deprecated Telegram reply target" in PATCH


def test_all_automation_entity_fields_use_search_picker() -> None:
    for field in (
        "automation-presence",
        "automation-signals",
        "automation-trigger-entity",
        "automation-action-entity",
        "autonomy-presence-entity",
    ):
        assert field in PATCH
    assert 'input.setAttribute("role","combobox")' in PATCH
    assert 'item.name} ${item.id} ${item.state}' in PATCH
    assert 'slice(0,40)' in PATCH


def test_picker_supports_mouse_keyboard_and_multi_entity_selection() -> None:
    assert 'event.key==="ArrowDown"||event.key==="ArrowUp"' in PATCH
    assert 'event.key==="Enter"' in PATCH
    assert 'event.key==="Escape"' in PATCH
    assert 'input.id==="automation-signals"' in PATCH
    assert 'parts.join(", ")' in PATCH


def test_release_and_build_order_are_aligned() -> None:
    assert 'version: "0.12.91"' in CONFIG
    assert MANIFEST["version"] == "0.12.91"
    copy = "COPY apply_telegram_chat_id_and_entity_search_v01291.py ./apply_telegram_chat_id_and_entity_search_v01291.py"
    run = "python3 ./apply_telegram_chat_id_and_entity_search_v01291.py"
    assert copy in DOCKER
    assert run in DOCKER
    assert DOCKER.index("python3 ./apply_real_automation_engine_v01290.py") < DOCKER.index(run)
    assert DOCKER.index(run) < DOCKER.index("python3 ./validate_release_manifest.py")
