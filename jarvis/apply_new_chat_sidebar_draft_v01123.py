from pathlib import Path

ROOT = Path('/opt/jarvis')
MAIN = ROOT / 'app/main.py'
INDEX = ROOT / 'app/static/index.html'


def must(text, marker, label):
    if marker not in text:
        raise RuntimeError(f'Jarvis v0.11.23 patch missing: {label}')


def patch_main():
    text = MAIN.read_text(encoding='utf-8')
    must(text, 'version="0.11.22"', 'backend version')
    text = text.replace('version="0.11.22"', 'version="0.11.23"', 1)
    text = text.replace('"version": "0.11.22"', '"version": "0.11.23"', 1)
    MAIN.write_text(text, encoding='utf-8')


def patch_index():
    text = INDEX.read_text(encoding='utf-8')

    marker = 'async function createNewChat() {'
    must(text, marker, 'createNewChat')
    helper = '''function renderDraftChatRow() {
  const existing = chatList.querySelector('.chat-list-item[data-draft="true"]');
  if (existing) existing.remove();
  for (const row of chatList.querySelectorAll('.chat-list-item.active')) {
    row.classList.remove('active');
  }
  const row = document.createElement('div');
  row.className = 'chat-list-item active';
  row.dataset.draft = 'true';
  row.dataset.sessionId = jarvisChatSessionId;
  const open = document.createElement('button');
  open.type = 'button';
  open.className = 'chat-open';
  open.textContent = 'New chat';
  open.setAttribute('aria-current', 'page');
  row.appendChild(open);
  chatList.prepend(row);
}

'''
    text = text.replace(marker, helper + marker, 1)

    old = '''  updateSessionDisplay();
  showChatWelcome();
  input.value = "";'''
    new = '''  updateSessionDisplay();
  renderDraftChatRow();
  showChatWelcome();
  input.value = "";'''
    must(text, old, 'draft UI insertion point')
    text = text.replace(old, new, 1)

    # Ensure opening any persisted chat removes a temporary draft row first.
    open_marker = '''async function openChat(sessionId) {
  if (activeRequest) return;'''
    open_new = '''async function openChat(sessionId) {
  if (activeRequest) return;
  chatList.querySelector('.chat-list-item[data-draft="true"]')?.remove();'''
    must(text, open_marker, 'openChat lifecycle')
    text = text.replace(open_marker, open_new, 1)

    text = text.replace('HUD 0.11.22', 'HUD 0.11.23', 1)
    INDEX.write_text(text, encoding='utf-8')


def verify():
    main = MAIN.read_text(encoding='utf-8')
    index = INDEX.read_text(encoding='utf-8')
    must(main, 'version="0.11.23"', 'backend version 0.11.23')
    must(index, 'HUD 0.11.23', 'HUD version 0.11.23')
    must(index, 'function renderDraftChatRow()', 'draft renderer')
    must(index, "row.dataset.draft = 'true';", 'draft marker')
    must(index, "open.textContent = 'New chat';", 'draft label')
    must(index, 'renderDraftChatRow();', 'New Chat renders draft row')
    must(index, "chatList.querySelector('.chat-list-item[data-draft=\"true\"]')?.remove();", 'persisted chat clears draft')


if __name__ == '__main__':
    patch_main()
    patch_index()
    verify()
