from __future__ import annotations

import json
from typing import Any

import httpx

class MCPError(RuntimeError):
    pass

def _decode_sse(text: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    data_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        if not line:
            if data_lines:
                payload = "\n".join(data_lines)
                try:
                    messages.append(json.loads(payload))
                except json.JSONDecodeError as exc:
                    raise MCPError(f"Invalid MCP SSE JSON: {exc}") from exc
                data_lines = []
            continue

        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())

    if data_lines:
        payload = "\n".join(data_lines)
        try:
            messages.append(json.loads(payload))
        except json.JSONDecodeError as exc:
            raise MCPError(f"Invalid MCP SSE JSON: {exc}") from exc

    return messages

async def _read_mcp_response(response: httpx.Response) -> list[dict[str, Any]]:
    if response.is_error:
        detail = response.text[:1000]
        raise MCPError(f"MCP HTTP {response.status_code}: {detail}")

    if response.status_code in (202, 204) or not response.content.strip():
        return []

    content_type = response.headers.get("content-type", "").lower()
    if "text/event-stream" in content_type:
        return _decode_sse(response.text)

    if "application/json" in content_type:
        try:
            body = response.json()
        except json.JSONDecodeError as exc:
            raise MCPError(
                f"Invalid MCP JSON response: {response.text[:500]}"
            ) from exc
        return body if isinstance(body, list) else [body]

    raise MCPError(f"Unsupported MCP response type: {content_type or 'missing'}")

def _find_result(messages: list[dict[str, Any]], request_id: int) -> dict[str, Any]:
    for message in messages:
        if message.get("id") == request_id:
            if "error" in message:
                error = message["error"]
                raise MCPError(
                    f"MCP error {error.get('code')}: {error.get('message')}"
                )
            return message.get("result", {})
    raise MCPError(f"No MCP result received for request id {request_id}")

def decode_workshop_tool_result(result: Any) -> dict[str, Any]:
    """Decode MCP tool output for application use, preferring structured data."""
    if not isinstance(result, dict):
        raise MCPError("Workshop Memory returned an invalid tool result")
    content = result.get("content") if isinstance(result.get("content"), list) else []
    text_parts = [
        str(item.get("text") or "")
        for item in content
        if isinstance(item, dict) and item.get("type") == "text"
    ]
    combined = "\n".join(part for part in text_parts if part)
    if result.get("isError") is True:
        raise MCPError(combined or "Workshop Memory tool execution failed")

    structured = result.get("structuredContent")
    if structured is not None:
        return structured if isinstance(structured, dict) else {"result": structured}
    if not combined:
        return result
    try:
        parsed = json.loads(combined)
    except json.JSONDecodeError:
        return {"text": combined}
    return parsed if isinstance(parsed, dict) else {"result": parsed}
