import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ZBRANO v0.12.35 patch expected one {label} marker; found {count}")
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.35 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    backend = replace_once(
        backend,
        '''        approval_input = [
            {
                "type": "mcp_approval_response",
                "approval_request_id": request["id"],
                "approve": approval_decision,
                "reason": "Approved by user in ZBRANO chat" if approval_decision else "Denied by user in ZBRANO chat",
            }
            for request in pending_approval["requests"]
        ]''',
        '''        # Cancellation returned above, so this continuation is approval-only.
        # OpenAI rejects `reason` when approve is true.
        approval_input = [
            {
                "type": "mcp_approval_response",
                "approval_request_id": request["id"],
                "approve": True,
            }
            for request in pending_approval["requests"]
        ]''',
        "approved MCP response payload",
    )

    backend = backend.replace('version="0.12.34"', 'version="0.12.35"')
    backend = backend.replace('"version": "0.12.34"', '"version": "0.12.35"')
    backend = backend.replace('"X-ZBRANO-Frontend-Version": "0.12.34"', '"X-ZBRANO-Frontend-Version": "0.12.35"')
    frontend = frontend.replace("HUD 0.12.34", "HUD 0.12.35")

    require(backend, "Cancellation returned above, so this continuation is approval-only", "approval-only continuation")
    require(backend, '"approve": True,', "valid approved MCP response")
    approval_start = backend.find("        approval_input = [")
    approval_end = backend.find("\n        async for event in stream_openai_response_with_progress(", approval_start)
    if approval_start < 0 or approval_end < 0:
        raise RuntimeError("ZBRANO v0.12.35 could not verify the approval payload bounds")
    if '"reason"' in backend[approval_start:approval_end]:
        raise RuntimeError("ZBRANO v0.12.35 approved MCP response still contains reason")
    require(backend, 'version="0.12.35"', "backend version")
    require(frontend, "HUD 0.12.35", "HUD version")

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
