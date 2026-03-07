"""Base HTTP transport with retry, auth, and error mapping."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from plivo_agent.errors import (
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    PlivoError,
    RateLimitError,
    ServerError,
    ValidationError,
)

logger = logging.getLogger("plivo_agent.http")

_STATUS_MAP: dict[int, type[PlivoError]] = {
    400: ValidationError,
    401: AuthenticationError,
    403: ForbiddenError,
    404: NotFoundError,
    429: RateLimitError,
}


class HttpTransport:
    """Async HTTP transport wrapping httpx.AsyncClient.

    Features:
        - HTTP Basic Auth
        - Automatic retry with exponential backoff on 429 and 5xx
        - Clean error mapping from HTTP status codes
        - Configurable timeout and max retries
    """

    def __init__(
        self,
        auth_id: str,
        auth_token: str,
        base_url: str = "https://api.plivo.com",
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> None:
        self._auth_id = auth_id
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._client = httpx.AsyncClient(
            auth=httpx.BasicAuth(auth_id, auth_token),
            base_url=self._base_url,
            timeout=httpx.Timeout(timeout),
            headers={
                "User-Agent": "plivo-agent-python/0.1.0",
                "Content-Type": "application/json",
            },
        )

    @property
    def auth_id(self) -> str:
        return self._auth_id

    @property
    def agents_base_url(self) -> str:
        return f"{self._base_url}/v1/Account/{self._auth_id}"

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        data: Any = None,
        files: Any = None,
    ) -> dict | None:
        """Execute an HTTP request with automatic retry on 429/5xx."""
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.request(
                    method,
                    path,
                    json=json,
                    params=params,
                    data=data,
                    files=files,
                )
                return self._process_response(response)

            except RateLimitError as exc:
                last_exc = exc
                wait = exc.retry_after or (self._backoff_factor * (2**attempt))
                logger.warning(
                    "Rate limited (429). Retry %d/%d in %.1fs",
                    attempt + 1,
                    self._max_retries,
                    wait,
                )
                await asyncio.sleep(wait)

            except ServerError as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    wait = self._backoff_factor * (2**attempt)
                    logger.warning(
                        "Server error (%d). Retry %d/%d in %.1fs",
                        exc.status_code,
                        attempt + 1,
                        self._max_retries,
                        wait,
                    )
                    await asyncio.sleep(wait)

        raise last_exc  # type: ignore[misc]

    def _process_response(self, response: httpx.Response) -> dict | None:
        """Map HTTP response to result or exception."""
        status = response.status_code

        if status == 204:
            return None

        if 200 <= status < 300:
            return response.json()

        try:
            body = response.json()
        except Exception:
            body = {"message": response.text}

        message = body.get("error", body.get("message", f"HTTP {status}"))

        if status == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                message,
                retry_after=float(retry_after) if retry_after else None,
                body=body,
            )

        exc_cls = _STATUS_MAP.get(status, ServerError if status >= 500 else PlivoError)
        raise exc_cls(message, status_code=status, body=body)

    async def close(self) -> None:
        await self._client.aclose()
