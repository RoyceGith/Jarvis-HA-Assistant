from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import REQUEST_TIMEOUT


class ZbranoApiError(Exception):
    """Raised when the local ZBRANO bridge cannot complete a request."""


@dataclass(slots=True)
class ZbranoApi:
    session: ClientSession
    url: str
    token: str

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            async with self.session.request(
                method,
                f"{self.url.rstrip('/')}{path}",
                headers=headers,
                timeout=ClientTimeout(total=REQUEST_TIMEOUT),
                **kwargs,
            ) as response:
                payload = await response.json(content_type=None)
                if response.status >= 400:
                    raise ZbranoApiError(str(payload.get("detail") or f"HTTP {response.status}"))
                return payload
        except (ClientError, TimeoutError, ValueError) as exc:
            raise ZbranoApiError(f"Cannot reach the local ZBRANO app: {exc}") from exc

    async def health(self) -> dict[str, Any]:
        return await self._request("GET", "/api/assist/health")

    async def converse(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/api/assist/conversation", json=payload)
