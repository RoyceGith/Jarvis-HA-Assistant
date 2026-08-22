import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.68 patch missing: {label}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"ZBRANO v0.12.68 expected one {label} marker; found {count}"
        )
    return text.replace(old, new, 1)


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    execute_marker = "\nasync def execute_tool_calls(\n"
    require(backend, execute_marker, "tool executor")
    reconciliation_helpers = r'''
def workshop_result_error(result: Any) -> str | None:
    if not isinstance(result, dict):
        return "Workshop Memory returned an invalid result."
    error = result.get("error")
    if error:
        return str(error)
    if result.get("isError") is True:
        return str(result.get("message") or "Workshop Memory reported an error.")
    return None


async def call_workshop_memory_tool_uncached(
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Call Workshop Memory without using a possibly stale post-write cache."""
    async with MCP_LOCK:
        endpoint_url = await select_workshop_memory_endpoint(force=True)
        return await _call_workshop_memory_endpoint(
            endpoint_url,
            tool_name,
            arguments,
        )


def reconciled_workshop_result(
    tool_name: str,
    result: dict[str, Any],
    detail: str,
) -> dict[str, Any]:
    reconciled = dict(result)
    reconciled.pop("error", None)
    reconciled["reconciled_after_ambiguous_error"] = True
    reconciled["reconciliation_tool"] = tool_name
    reconciled["reconciliation_detail"] = detail
    return reconciled


async def reconcile_workshop_memory_write(
    tool_name: str,
    arguments: dict[str, Any],
    original_result: dict[str, Any],
) -> dict[str, Any]:
    """Verify ambiguous writes and retry only operations known to be safe."""
    if tool_name == "write_project_note":
        relative_path = str(arguments.get("relative_path") or "").strip()
        expected = str(arguments.get("content") or "")
        mode = str(arguments.get("mode") or "create").strip().lower()
        if not relative_path:
            return original_result

        existing: dict[str, Any] | None = None
        try:
            existing = await call_workshop_memory_tool_uncached(
                "read_project_note",
                {"relative_path": relative_path},
            )
        except Exception:
            existing = None

        actual = str((existing or {}).get("content") or "")
        already_applied = actual == expected or (
            mode == "append" and bool(expected) and actual.endswith(expected)
        )
        if already_applied:
            return reconciled_workshop_result(
                tool_name,
                {"relative_path": relative_path, "mode": mode, "verified": True},
                "The saved note content was read back and matched the approved write.",
            )

        if mode == "create" and existing and not workshop_result_error(existing):
            return {
                "error": (
                    "Workshop Memory returned an ambiguous create result, and the note "
                    "now exists with different content. Automatic retry stopped to avoid "
                    "overwriting a conflict."
                ),
                "relative_path": relative_path,
                "reconciliation_conflict": True,
            }
        if mode == "append":
            return {
                "error": (
                    "Workshop Memory returned an ambiguous append result and exact suffix "
                    "verification did not confirm it. Automatic retry stopped to prevent "
                    "duplicate appended content."
                ),
                "relative_path": relative_path,
                "reconciliation_uncertain": True,
            }

        # A create of a missing note and an explicitly approved replacement are
        # safe to retry once. The original approval already covered these exact
        # arguments; no broader mutation is introduced here.
        try:
            retry_result = await call_workshop_memory_tool_uncached(
                tool_name,
                arguments,
            )
        except Exception as exc:
            return {
                **original_result,
                "reconciliation_attempted": True,
                "reconciliation_error": str(exc)[:300],
            }
        if workshop_result_error(retry_result):
            return {
                **retry_result,
                "reconciliation_attempted": True,
            }
        return reconciled_workshop_result(
            tool_name,
            retry_result,
            "The missing approved note operation succeeded on one bounded retry.",
        )

    if tool_name == "apply_project_template_pack":
        # Template packs are server-defined create-missing operations. Repeating
        # the exact approved call preserves existing notes and cannot duplicate
        # or overwrite them.
        try:
            retry_result = await call_workshop_memory_tool_uncached(
                tool_name,
                arguments,
            )
        except Exception as exc:
            return {
                **original_result,
                "reconciliation_attempted": True,
                "reconciliation_error": str(exc)[:300],
            }
        if workshop_result_error(retry_result):
            return {
                **retry_result,
                "reconciliation_attempted": True,
            }
        return reconciled_workshop_result(
            tool_name,
            retry_result,
            "The idempotent template pack was rerun and only missing notes were created.",
        )

    # Unknown write tools are never retried automatically. Their state may be
    # inspected by a later read-only request, but guessing could duplicate or
    # overwrite permanent project data.
    return {
        **original_result,
        "reconciliation_supported": False,
        "reconciliation_detail": (
            "Automatic retry is unavailable for this write type; inspect current "
            "Workshop Memory state before retrying."
        ),
    }


def workshop_execution_fallback_reply(tool_outputs: Any) -> str:
    succeeded = 0
    failed = 0
    reconciled = 0
    for output in tool_outputs if isinstance(tool_outputs, list) else []:
        if not isinstance(output, dict):
            continue
        raw = output.get("output")
        try:
            result = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            result = {"error": "Invalid tool result"}
        if workshop_result_error(result):
            failed += 1
        else:
            succeeded += 1
            if isinstance(result, dict) and result.get("reconciled_after_ambiguous_error"):
                reconciled += 1
    if failed:
        return (
            "Workshop Memory execution completed, but the response step failed. "
            f"State reconciliation confirmed {succeeded} operation(s); {failed} "
            "operation(s) still reported an error. Inspect current project state "
            "before retrying the failed operations."
        )
    detail = f" Reconciled after an ambiguous result: {reconciled}." if reconciled else ""
    return (
        "Workshop Memory execution completed successfully, but the normal response "
        f"could not be generated. Confirmed operations: {succeeded}.{detail} No "
        "automatic duplicate retry is required."
    )


async def create_workshop_continuation_response(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Return a truthful synthetic completion if post-write AI rendering fails."""
    try:
        return await create_openai_response(payload)
    except Exception:
        reply = workshop_execution_fallback_reply(payload.get("input"))
        return {
            "id": str(payload.get("previous_response_id") or "workshop-reconciled"),
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": reply}],
                }
            ],
        }

'''
    backend = backend.replace(execute_marker, "\n" + reconciliation_helpers + execute_marker, 1)

    workshop_call_marker = '''                else:
                    result = await call_workshop_memory_tool(name, arguments)'''
    workshop_call_replacement = '''                else:
                    result = await (
                        call_workshop_memory_tool_uncached(name, arguments)
                        if permission == "write"
                        else call_workshop_memory_tool(name, arguments)
                    )'''
    backend = replace_once(
        backend,
        workshop_call_marker,
        workshop_call_replacement,
        "write-aware Workshop Memory transport",
    )

    result_marker = '''            except (asyncio.TimeoutError, MCPError, httpx.HTTPError, RuntimeError, PermissionError, ValueError, HTTPException) as exc:
                result = {"error": str(exc)}

        audit.append('''
    result_replacement = '''            except (asyncio.TimeoutError, MCPError, httpx.HTTPError, RuntimeError, PermissionError, ValueError, HTTPException) as exc:
                result = {"error": str(exc)}

        if (
            permission == "write"
            and call_id in approved_workshop_call_ids
            and workshop_result_error(result)
        ):
            result = await reconcile_workshop_memory_write(name, arguments, result)

        audit.append('''
    backend = replace_once(
        backend,
        result_marker,
        result_replacement,
        "approved write reconciliation hook",
    )

    continuation_start = backend.find("async def continue_workshop_memory_approval(")
    continuation_end = backend.find("\n\nPENDING_MCP_APPROVALS:", continuation_start)
    if continuation_start < 0 or continuation_end < 0:
        raise RuntimeError("ZBRANO v0.12.68 could not isolate approval continuation")
    continuation = backend[continuation_start:continuation_end]
    response_calls = continuation.count("await create_openai_response({")
    if response_calls != 2:
        raise RuntimeError(
            "ZBRANO v0.12.68 expected two Workshop continuation response calls; "
            f"found {response_calls}"
        )
    continuation = continuation.replace(
        "await create_openai_response({",
        "await create_workshop_continuation_response({",
    )
    backend = backend[:continuation_start] + continuation + backend[continuation_end:]

    backend = backend.replace('version="0.12.67"', 'version="0.12.68"')
    backend = backend.replace('"version": "0.12.67"', '"version": "0.12.68"')
    backend = backend.replace(
        '"X-ZBRANO-Frontend-Version": "0.12.67"',
        '"X-ZBRANO-Frontend-Version": "0.12.68"',
    )
    backend = backend.replace(
        '"name": "ZBRANO Developer Mode", "version": "0.12.67"',
        '"name": "ZBRANO Developer Mode", "version": "0.12.68"',
    )
    frontend = frontend.replace("HUD 0.12.67", "HUD 0.12.68")

    required = (
        "async def reconcile_workshop_memory_write(",
        'tool_name == "apply_project_template_pack"',
        'tool_name == "write_project_note"',
        "create_workshop_continuation_response",
        "reconciliation_uncertain",
        'version="0.12.68"',
    )
    missing = [marker for marker in required if marker not in backend]
    if missing or "HUD 0.12.68" not in frontend:
        raise RuntimeError(
            "ZBRANO v0.12.68 verification failed: " + ", ".join(missing)
        )

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
