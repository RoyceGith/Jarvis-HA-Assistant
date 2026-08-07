from pathlib import Path
import re
import sys

path = Path(sys.argv[1] if len(sys.argv) > 1 else '/opt/jarvis/app/static/index.html')
text = path.read_text(encoding='utf-8')

required = [
    'id="new-chat-button"',
    'newChatButton.addEventListener("click", createNewChat);',
    'function renderDraftChatRow()',
]
missing = [marker for marker in required if marker not in text]
if missing:
    raise SystemExit('New Chat wiring validation failed; missing: ' + ', '.join(missing))

if 'id="clear-chat"' in text:
    raise SystemExit('New Chat wiring validation failed: legacy #clear-chat control remains')

capture_handlers = re.findall(r'document\.addEventListener\("click",[\s\S]*?\},\s*true\);', text)
for handler in capture_handlers:
    if '#new-chat-button' in handler or '#clear-chat' in handler:
        raise SystemExit('New Chat wiring validation failed: capture-phase handler intercepts New Chat')

print('New Chat wiring validated')
