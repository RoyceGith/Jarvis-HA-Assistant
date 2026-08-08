import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"ZBRANO v0.12.26 Playwright repair expected one {label} marker; found {count}"
        )
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.26 Playwright repair missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")

    helpers = r'''PLAYWRIGHT_MCP_LOG = Path("/tmp/zbrano-playwright-mcp.log")
PLAYWRIGHT_CHROMIUM_CANDIDATES = (
    Path("/usr/bin/chromium-browser"),
    Path("/usr/bin/chromium"),
)


def playwright_redact_evidence(value: str, *, limit: int) -> str:
    compact = " ".join(value.split())
    compact = re.sub(r"(?i)\bBearer\s+\S+", "Bearer [redacted]", compact)
    compact = re.sub(
        r"(?i)\b(authorization|api[_-]?key|token|secret|cookie)\s*[:=]\s*\S+",
        r"\1=[redacted]",
        compact,
    )
    return compact[:limit]


def playwright_chromium_executable() -> str:
    return next(
        (str(path) for path in PLAYWRIGHT_CHROMIUM_CANDIDATES if path.is_file()),
        "not found",
    )


def playwright_process_available() -> bool:
    proc = Path("/proc")
    if not proc.is_dir():
        return False
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", errors="replace"
            )
        except (OSError, PermissionError):
            continue
        if "playwright-mcp" in command and "8931" in command:
            return True
    return False


def playwright_startup_log_tail(*, max_bytes: int = 4096, max_lines: int = 12) -> str:
    try:
        with PLAYWRIGHT_MCP_LOG.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - max_bytes))
            data = handle.read(max_bytes)
    except OSError:
        return "unavailable"
    lines = data.decode("utf-8", errors="replace").splitlines()[-max_lines:]
    evidence = " | ".join(line.strip() for line in lines if line.strip())
    return playwright_redact_evidence(evidence, limit=240) or "empty"


def playwright_preflight_summary(*, include_log: bool = False) -> str:
    summary = (
        f"chromium={playwright_chromium_executable()}; "
        f"process={'available' if playwright_process_available() else 'not detected'}"
    )
    if include_log:
        summary += f"; startup log tail={playwright_startup_log_tail()}"
    return summary


def playwright_http_error(operation: str, response: httpx.Response) -> RuntimeError:
    response_detail = playwright_redact_evidence(response.text, limit=160) or "empty response"
    return RuntimeError(
        f"Playwright MCP {operation} returned HTTP {response.status_code}; "
        f"response={response_detail}; {playwright_preflight_summary(include_log=True)}"
    )


'''
    backend = replace_once(
        backend,
        "async def _playwright_rpc(\n",
        helpers + "async def _playwright_rpc(\n",
        "Playwright preflight helpers",
    )
    backend = replace_once(
        backend,
        '''    if response.is_error:
        raise RuntimeError(f"Playwright MCP {method} returned HTTP {response.status_code}")''',
        '''    if response.is_error:
        raise playwright_http_error(method, response)''',
        "Playwright RPC failure evidence",
    )
    backend = replace_once(
        backend,
        '''        if response.is_redirect or response.is_error:
            raise RuntimeError(f"Playwright MCP initialize returned HTTP {response.status_code}")''',
        '''        if response.is_redirect:
            raise RuntimeError("Local Playwright MCP initialize redirect is not allowed")
        if response.is_error:
            raise playwright_http_error("initialize", response)''',
        "Playwright initialize failure evidence",
    )
    backend = replace_once(
        backend,
        '''        if initialized.is_error:
            raise RuntimeError(f"Playwright MCP initialized notification returned HTTP {initialized.status_code}")''',
        '''        if initialized.is_error:
            raise playwright_http_error("initialized notification", initialized)''',
        "Playwright notification failure evidence",
    )
    old_client_version = (
        '"clientInfo": {"name": "ZBRANO Developer Mode", "version": "0.12.16"}'
    )
    current_client_version = (
        '"clientInfo": {"name": "ZBRANO Developer Mode", "version": "0.12.26"}'
    )
    if old_client_version in backend:
        backend = replace_once(
            backend,
            old_client_version,
            current_client_version,
            "Playwright MCP client version",
        )
    backend = replace_once(
        backend,
        '''            f"{len(playwright_tools)} browser tools discovered" if not playwright_missing else f"missing: {', '.join(playwright_missing)}",''',
        '''            (f"{len(playwright_tools)} browser tools discovered; {playwright_preflight_summary()}" if not playwright_missing else f"missing: {', '.join(playwright_missing)}; {playwright_preflight_summary(include_log=True)}"),''',
        "Playwright diagnostic preflight",
    )
    backend = replace_once(
        backend,
        '''                f"{len(playwright_tools)} local browser tools discovered" if not playwright_missing else f"missing: {', '.join(playwright_missing)}",''',
        '''                (f"{len(playwright_tools)} local browser tools discovered; {playwright_preflight_summary()}" if not playwright_missing else f"missing: {', '.join(playwright_missing)}; {playwright_preflight_summary(include_log=True)}"),''',
        "targeted Playwright diagnostic preflight",
    )

    require(backend, "def playwright_startup_log_tail", "bounded startup-log evidence")
    require(backend, "def playwright_redact_evidence", "diagnostic evidence redaction")
    require(backend, "def playwright_process_available", "MCP process preflight")
    require(backend, current_client_version, "Playwright MCP client version")
    MAIN.write_text(backend, encoding="utf-8")


if __name__ == "__main__":
    main()
