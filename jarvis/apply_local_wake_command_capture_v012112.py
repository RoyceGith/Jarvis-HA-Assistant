import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.112 patch expected one {label}; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.112 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    require(backend, 'version="0.12.111"', "backend version")
    require(frontend, "HUD 0.12.111", "frontend version")
    frontend = replace_once(
        frontend,
        '''    if(!wakeFallbackAnalyser||wakeShadowEnabled.checked)return;''',
        '''    if(!wakeFallbackAnalyser||(wakeShadowEnabled.checked&&wakeFallbackMode==="wake"))return;''',
        "local command voice-activity gate",
    )
    frontend = replace_once(
        frontend,
        '''        <label class="toggle-row"><input id="wake-word-enabled" type="checkbox"> Enable browser wake phrase</label>
        <label class="toggle-row"><input id="wake-conversation-enabled" type="checkbox"> Keep listening for follow-up conversation after voice replies</label>''',
        '''        <label class="toggle-row"><input id="wake-word-enabled" type="checkbox"> Enable always listening mode</label>
        <label class="toggle-row"><input id="wake-local-activate" type="checkbox"> Use the local wake model to activate ZBRANO</label>
        <label class="toggle-row"><input id="wake-conversation-enabled" type="checkbox"> Keep listening for follow-up conversation after voice replies</label>''',
        "hands-free wake controls",
    )
    frontend = replace_once(
        frontend,
        '''          <label class="toggle-row"><input id="wake-local-activate" type="checkbox"> Use the local wake model to activate ZBRANO</label>
''',
        "",
        "duplicate diagnostic activation control",
    )

    backend = backend.replace('version="0.12.111"', 'version="0.12.112"')
    backend = backend.replace('"version": "0.12.111"', '"version": "0.12.112"')
    frontend = frontend.replace("HUD 0.12.111", "HUD 0.12.112")

    require(backend, 'version="0.12.112"', "updated backend version")
    require(frontend, "HUD 0.12.112", "updated frontend version")
    require(
        frontend,
        'wakeShadowEnabled.checked&&wakeFallbackMode==="wake"',
        "command-mode VAD exception",
    )
    require(frontend, "Enable always listening mode", "always-listening label")
    if frontend.count('id="wake-local-activate"') != 1:
        raise RuntimeError("ZBRANO v0.12.112 local wake activation control must appear once")
    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
