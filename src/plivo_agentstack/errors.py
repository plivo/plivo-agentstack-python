"""Exception hierarchy for the Plivo SDK.

Mapping:
    400 -> ValidationError
    401 -> AuthenticationError
    403 -> ForbiddenError
    404 -> NotFoundError
    429 -> RateLimitError
    5xx -> ServerError
    WS  -> WebSocketError
"""

from __future__ import annotations


class PlivoError(Exception):
    """Base exception for all Plivo SDK errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        body: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body or {}


class AuthenticationError(PlivoError):
    """401 — invalid auth_id or auth_token."""


class ForbiddenError(AuthenticationError):
    """403 — valid credentials but insufficient permissions."""


class ValidationError(PlivoError):
    """400 — request payload failed validation."""


class NotFoundError(PlivoError):
    """404 — resource does not exist."""


class RateLimitError(PlivoError):
    """429 — too many requests."""

    def __init__(
        self,
        message: str,
        retry_after: float | None = None,
        **kwargs,
    ) -> None:
        super().__init__(message, status_code=429, **kwargs)
        self.retry_after = retry_after


class ServerError(PlivoError):
    """5xx — Plivo internal server error."""


class WebSocketError(PlivoError):
    """WebSocket connection or protocol error."""
