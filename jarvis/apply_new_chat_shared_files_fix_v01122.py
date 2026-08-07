from pathlib import Path

ROOT = Path('/opt/jarvis')
MAIN = ROOT / 'app/main.py'
INDEX = ROOT / 'app/static/index.html'


def must(text, marker, label):
    if marker not in text:
        raise RuntimeError(f'Jarvis v0.11.22 patch missing: {label}')


def patch_main():
    text = MAIN.read_text(encoding='utf-8')
    must(text, 'version="0.11.21"', 'backend version')
    text = text.replace('version="0.11.21"', 'version="0.11.22"', 1)
    text = text.replace('"version": "0.11.21"', '"version": "0.11.22"', 1)
    MAIN.write_text(text, encoding='utf-8')


def patch_index():
    text = INDEX.read_text(encoding='utf-8')

    old = '''async function createNewChat() {
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
    new = '''async function createNewChat() {
  if (activeRequest) {
    activeRequest.stopped = true;
    const staleSocket = activeRequest.socket;
    try {
      if (staleSocket?.readyState === WebSocket.OPEN) {
        staleSocket.send(JSON.stringify({type: "stop"}));
      }
      staleSocket?.close();
    } catch (_) {}
    activeRequest = null;
  }
  stopAudioPlayback("VOICE READY");
  input.disabled = false;
  sendButton.disabled = false;
  micButton.disabled = false;
  stopButton.disabled = true;
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
    must(text, old, 'v0.11.21 New Chat lifecycle')
    text = text.replace(old, new, 1)

    duplicate_button = '      <button id="clear-chat" type="button">New Chat</button>\n'
    must(text, duplicate_button, 'legacy Entities New Chat button')
    text = text.replace(duplicate_button, '', 1)
    text = text.replace('const clearChat = document.getElementById("clear-chat");\n', '', 1)
    text = text.replace('clearChat?.addEventListener("click", createNewChat);\n\n', '', 1)

    old_empty = 'shared=d.files||[];rows.replaceChildren();shared.forEach(x=>{'
    new_empty = 'shared=d.files||[];rows.replaceChildren();if(!shared.length){let r=document.createElement("tr");r.innerHTML=`<td colspan="5" class="muted">No shared files. Upload using Add to Shared Files.</td>`;rows.appendChild(r)}shared.forEach(x=>{'
    must(text, old_empty, 'Shared Files row renderer')
    text = text.replace(old_empty, new_empty, 1)

    old_tab = 'tab?.addEventListener("click",async()=>{showPanel("files");await list()});'
    new_tab = 'tab?.addEventListener("click",async()=>{showPanel("files");const summary=document.getElementById("shared-summary");if(summary)summary.textContent="Loading shared files…";try{await list()}catch(e){rows.replaceChildren();if(summary)summary.textContent=`Shared Files failed to load: ${e.message||e}`}});'
    must(text, old_tab, 'Shared Files tab loader')
    text = text.replace(old_tab, new_tab, 1)

    text = text.replace('HUD 0.11.21', 'HUD 0.11.22', 1)
    INDEX.write_text(text, encoding='utf-8')


def verify():
    main = MAIN.read_text(encoding='utf-8')
    index = INDEX.read_text(encoding='utf-8')
    must(main, 'version="0.11.22"', 'backend version 0.11.22')
    must(index, 'HUD 0.11.22', 'HUD version 0.11.22')
    must(index, 'activeRequest = null;', 'stale request reset')
    must(index, 'staleSocket?.close();', 'stale socket close')
    must(index, 'No shared files. Upload using Add to Shared Files.', 'Shared Files empty state')
    must(index, 'Shared Files failed to load:', 'Shared Files error state')
    if 'id="clear-chat"' in index:
        raise RuntimeError('Jarvis v0.11.22 verification failed: legacy Entities New Chat remains')
    start = index.find('async function createNewChat()')
    end = index.find('async function deleteChat', start)
    if 'if (activeRequest) return;' in index[start:end]:
        raise RuntimeError('Jarvis v0.11.22 verification failed: New Chat still silently returns')


if __name__ == '__main__':
    patch_main()
    patch_index()
    verify()
