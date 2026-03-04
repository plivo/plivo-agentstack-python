"""Main SDK entry point — AsyncClient."""

from __future__ import annotations

import os
from typing import Any

from plivo_agent._http import HttpTransport


class AsyncClient:
    """Async Plivo client — the single entry point for the SDK.

    Usage::

        async with AsyncClient("AUTH_ID", "AUTH_TOKEN") as client:
            msg = await client.messages.create(src="+1...", dst="+1...", text="Hi")

    Sub-clients:
        client.agent       — Agent CRUD, calls, numbers (Agent Stack)
        client.messages    — SMS, MMS, WhatsApp
        client.numbers     — Number search, buy, manage, lookup
    """

    def __init__(
        self,
        auth_id: str | None = None,
        auth_token: str | None = None,
        base_url: str = "https://api.plivo.com",
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        _auth_id = auth_id or os.environ.get("PLIVO_AUTH_ID", "")
        _auth_token = auth_token or os.environ.get("PLIVO_AUTH_TOKEN", "")

        if not _auth_id or not _auth_token:
            raise ValueError(
                "auth_id and auth_token are required. "
                "Pass them directly or set PLIVO_AUTH_ID and PLIVO_AUTH_TOKEN env vars."
            )

        self._http = HttpTransport(
            _auth_id,
            _auth_token,
            base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

        self._agent: Any = None
        self._messages: Any = None
        self._numbers: Any = None

    @property
    def agent(self):
        """Agent Stack REST client."""
        if self._agent is None:
            from plivo_agent.agent.client import AgentClient

            self._agent = AgentClient(self._http)
        return self._agent

    @property
    def messages(self):
        """Messages REST client."""
        if self._messages is None:
            from plivo_agent.messaging.client import MessagesClient

            self._messages = MessagesClient(self._http)
        return self._messages

    @property
    def numbers(self):
        """Numbers REST client."""
        if self._numbers is None:
            from plivo_agent.numbers.client import NumbersClient

            self._numbers = NumbersClient(self._http)
        return self._numbers

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP transport."""
        await self._http.close()
