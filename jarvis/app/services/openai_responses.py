from __future__ import annotations

import json
from typing import Any

import httpx


OPENAI_API_KEY = ""
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


class OpenAIError(RuntimeError):
    pass


def configure_openai_responses(*, api_key: str, responses_url: str) -> None:
    global OPENAI_API_KEY, OPENAI_RESPONSES_URL
    OPENAI_API_KEY = api_key
    OPENAI_RESPONSES_URL = responses_url


def openai_error_message(response: httpx.Response) -> str:
    try:
        detail = response.json()
    except json.JSONDecodeError:
        detail = response.text[:1000]
    return f"OpenAI HTTP {response.status_code}: {detail}"


async def create_openai_response(payload: dict[str, Any]) -> dict[str, Any]:
    if not OPENAI_API_KEY:
        raise OpenAIError("OpenAI API key is not configured")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(
            OPENAI_RESPONSES_URL,
            headers=headers,
            json=payload,
        )

    if response.is_error:
        raise OpenAIError(openai_error_message(response))

    return response.json()


def response_text(response: dict[str, Any]) -> str:
    texts: list[str] = []
    for item in response.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    texts.append(content.get("text", ""))
    return "\n".join(text for text in texts if text).strip()


def function_calls(response: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in response.get("output", [])
        if item.get("type") == "function_call"
    ]
