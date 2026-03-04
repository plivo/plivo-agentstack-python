"""Tests for plivo_agent.errors exception hierarchy."""

from __future__ import annotations

from plivo_agent.errors import (
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    PlivoError,
    RateLimitError,
    ServerError,
    ValidationError,
)


def test_plivo_error_has_status_and_body():
    """PlivoError stores status_code and body."""
    err = PlivoError("something failed", status_code=500, body={"detail": "oops"})
    assert err.status_code == 500
    assert err.body == {"detail": "oops"}
    assert "something failed" in str(err)


def test_rate_limit_error_has_retry_after():
    """RateLimitError stores retry_after and defaults status_code to 429."""
    err = RateLimitError("slow down", retry_after=2.5, body={"error": "rate limited"})
    assert err.retry_after == 2.5
    assert err.status_code == 429
    assert err.body == {"error": "rate limited"}


def test_forbidden_is_authentication_error():
    """ForbiddenError is a subclass of AuthenticationError."""
    err = ForbiddenError("not allowed", status_code=403)
    assert isinstance(err, AuthenticationError)
    assert isinstance(err, PlivoError)


def test_error_hierarchy():
    """All concrete error types are subclasses of PlivoError."""
    for cls in (
        AuthenticationError,
        ForbiddenError,
        ValidationError,
        NotFoundError,
        RateLimitError,
        ServerError,
    ):
        assert issubclass(cls, PlivoError), f"{cls.__name__} must be a PlivoError"

    # ForbiddenError -> AuthenticationError -> PlivoError
    assert issubclass(ForbiddenError, AuthenticationError)
