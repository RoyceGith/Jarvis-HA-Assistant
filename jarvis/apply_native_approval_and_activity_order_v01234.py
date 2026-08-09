import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.34 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.34 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    native_approval_policy = '''For remote MCP plugin tools such as Cloudflare or GitHub, never write, simulate,
or ask a manual preflight approval question in the assistant response. When the
user requests an enabled plugin action, call the requested tool exactly once.
The platform-native MCP approval gate will pause any approval-required call
before execution and will present the safe provider-aware summary. Calling an
approval-gated tool is therefore the required way to request approval; it does
not bypass approval. Never expose raw tool arguments, executable code, account
identifiers, credentials, or internal approval payloads in chat. Only treat
`approve` or `cancel` as an approval decision when a native approval is pending.
After a denial, treat the action as finished and do not propose another approval,
equivalent command, or retry unless the user issues the original task again.

'''
    backend = replace_once(
        backend,
        '''Be direct, technically precise, and concise. Distinguish documented facts
from proposals and unresolved questions.''',
        native_approval_policy + '''Be direct, technically precise, and concise. Distinguish documented facts
from proposals and unresolved questions.''',
        "native plugin approval policy",
    )

    ai_start = frontend.find('        <div id="ai-activity"')
    tool_start = frontend.find('        <div id="tool-timeline"', ai_start)
    form_start = frontend.find('        <form id="chat-form">', tool_start)
    if ai_start < 0 or tool_start < 0 or form_start < 0 or not ai_start < tool_start < form_start:
        raise RuntimeError("ZBRANO v0.12.34 patch could not locate activity rows in their v0.12.33 order")
    ai_block = frontend[ai_start:tool_start]
    tool_block = frontend[tool_start:form_start]
    frontend = frontend[:ai_start] + tool_block + ai_block + frontend[form_start:]

    backend = backend.replace('version="0.12.33"', 'version="0.12.34"')
    backend = backend.replace('"version": "0.12.33"', '"version": "0.12.34"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.33"', '"X-ZBRANO-Frontend-Version": "0.12.34"')
    frontend = frontend.replace("HUD 0.12.33", "HUD 0.12.34")

    require(backend, "never write, simulate,\nor ask a manual preflight approval question", "manual pre-approval prohibition")
    require(backend, "call the requested tool exactly once", "native approval invocation policy")
    require(backend, "Only treat\n`approve` or `cancel` as an approval decision when a native approval is pending", "native pending approval boundary")
    if frontend.index('id="tool-timeline"') > frontend.index('id="ai-activity"'):
        raise RuntimeError("ZBRANO v0.12.34 activity rows were not swapped")
    require(backend, 'version="0.12.34"', "backend version")
    require(frontend, "HUD 0.12.34", "HUD version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
