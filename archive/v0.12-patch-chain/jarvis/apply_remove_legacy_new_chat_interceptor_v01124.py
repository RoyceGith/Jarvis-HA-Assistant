from pathlib import Path

ROOT = Path('/opt/jarvis')
MAIN = ROOT / 'app/main.py'
INDEX = ROOT / 'app/static/index.html'


def must(text, marker, label):
    if marker not in text:
        raise RuntimeError(f'Jarvis v0.11.24 patch missing: {label}')


def patch_main():
    text = MAIN.read_text(encoding='utf-8')
    must(text, 'version="0.11.23"', 'backend version')
    text = text.replace('version="0.11.23"', 'version="0.11.24"', 1)
    text = text.replace('"version": "0.11.23"', '"version": "0.11.24"', 1)
    MAIN.write_text(text, encoding='utf-8')


def patch_index():
    text = INDEX.read_text(encoding='utf-8')
    start_marker = '    const newChat = event.target.closest?.("#new-chat-button, #clear-chat");\n'
    if start_marker in text:
        start = text.index(start_marker)
        end_marker = '  }, true);\n})();'
        end = text.index(end_marker, start)
        # The New Chat branch is the last branch in this historical capture listener.
        text = text[:start] + text[end:]
    text = text.replace('HUD 0.11.23', 'HUD 0.11.24', 1)
    INDEX.write_text(text, encoding='utf-8')


def verify():
    main = MAIN.read_text(encoding='utf-8')
    index = INDEX.read_text(encoding='utf-8')
    must(main, 'version="0.11.24"', 'backend version 0.11.24')
    must(index, 'HUD 0.11.24', 'HUD version 0.11.24')
    must(index, 'newChatButton.addEventListener("click", createNewChat);', 'direct New Chat listener')
    must(index, 'function renderDraftChatRow()', 'visible draft renderer')
    if 'event.target.closest?.("#new-chat-button, #clear-chat")' in index:
        raise RuntimeError('Jarvis v0.11.24 verification failed: legacy capture interceptor remains')
    if 'id="clear-chat"' in index:
        raise RuntimeError('Jarvis v0.11.24 verification failed: legacy clear-chat button remains')


if __name__ == '__main__':
    patch_main()
    patch_index()
    verify()
