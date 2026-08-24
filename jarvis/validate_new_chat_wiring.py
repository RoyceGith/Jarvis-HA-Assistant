from pathlib import Path
import re
import sys

path = Path(sys.argv[1] if len(sys.argv) > 1 else '/opt/jarvis/app/static/index.html')
html = path.read_text(encoding='utf-8')
sources = [html]
for match in re.finditer(r'<script\b([^>]*)>.*?</script>', html, flags=re.I | re.S):
    source_match = re.search(r'\bsrc="([^"]+)"', match.group(1), flags=re.I)
    if not source_match:
        continue
    source_path = (path.parent / source_match.group(1)).resolve()
    try:
        source_path.relative_to(path.parent.resolve())
    except ValueError as exc:
        raise SystemExit('New Chat wiring validation failed: script path escapes static directory') from exc
    if not source_path.is_file():
        raise SystemExit('New Chat wiring validation failed: missing script ' + source_match.group(1))
    sources.append(source_path.read_text(encoding='utf-8'))
text = '\n'.join(sources)

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
