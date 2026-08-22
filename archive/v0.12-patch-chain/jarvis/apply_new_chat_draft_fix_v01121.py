from pathlib import Path

ROOT = Path('/opt/jarvis')
MAIN = ROOT / 'app/main.py'
INDEX = ROOT / 'app/static/index.html'


def must(text, marker, label):
    if marker not in text:
        raise RuntimeError(f'Jarvis v0.11.21 patch missing: {label}')


def patch_main():
    text = MAIN.read_text(encoding='utf-8')
    must(text, 'version="0.11.20"', 'backend version')
    text = text.replace('version="0.11.20"', 'version="0.11.21"', 1)
    text = text.replace('"version": "0.11.20"', '"version": "0.11.21"', 1)
    MAIN.write_text(text, encoding='utf-8')


def patch_index():
    text = INDEX.read_text(encoding='utf-8')
    old = '''async function createNewChat() {
  if (activeRequest) return;
  const sessionId = createSessionId();
  const response = await fetch("api/chats", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({session_id: sessionId}),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  showPanel("chat");
  await openChat(sessionId);
}'''
    new = '''async function createNewChat() {
  if (activeRequest) return;
  showPanel("chat");
  jarvisChatSessionId = createSessionId();
  localStorage.setItem("jarvis_chat_session_id", jarvisChatSessionId);
  updateSessionDisplay();
  showChatWelcome();
  input.value = "";
  input.dispatchEvent(new Event("input", {bubbles: true}));
  if (typeof window.zbranoClearPendingAttachments === "function") {
    window.zbranoClearPendingAttachments();
  }
  const attachmentState = document.getElementById("attachment-state");
  if (attachmentState) attachmentState.textContent = "";
  input.focus();
}'''
    must(text, old, 'v0.11.20 persistent New Chat lifecycle')
    text = text.replace(old, new, 1)
    text = text.replace('HUD 0.11.20', 'HUD 0.11.21', 1)
    INDEX.write_text(text, encoding='utf-8')


def verify():
    main = MAIN.read_text(encoding='utf-8')
    index = INDEX.read_text(encoding='utf-8')
    must(main, 'version="0.11.21"', 'backend version 0.11.21')
    must(index, 'HUD 0.11.21', 'HUD version 0.11.21')
    must(index, 'showPanel("chat");\n  jarvisChatSessionId = createSessionId();', 'draft-first New Chat')
    must(index, 'localStorage.setItem("jarvis_chat_session_id", jarvisChatSessionId);', 'draft session persistence')
    must(index, 'window.zbranoClearPendingAttachments();', 'pending attachment reset')
    start = index.find('async function createNewChat()')
    end = index.find('async function deleteChat', start)
    block = index[start:end]
    if 'fetch("api/chats"' in block or 'body: JSON.stringify({session_id: sessionId})' in block:
        raise RuntimeError('Jarvis v0.11.21 verification failed: New Chat still persists before first message')


if __name__ == '__main__':
    patch_main()
    patch_index()
    verify()
