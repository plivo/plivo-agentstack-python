"""Tests for plivo_agentstack._http.HttpTransport."""

from __future__ import annotations

import httpx
import pytest

from plivo_agentstack._http import HttpTransport
from plivo_agentstack.errors import (
    AuthenticationError,
    NotFoundError,
    ServerError,
    ValidationError,
)

BASE_URL = "https://api.plivo.com"
AUTH_ID = "TESTAUTH123"
AUTH_TOKEN = "test_token_secret"


@pytest.fixture()
def fast_transport(mock_api):
    """HttpTransport with a very small backoff for fast retry tests."""
    return HttpTransport(
        AUTH_ID,
        AUTH_TOKEN,
        BASE_URL,
        timeout=5.0,
        max_retries=3,
        backoff_factor=0.01,
    )


async def test_successful_request(mock_api, http_transport):
    """200 response returns parsed JSON dict."""
    mock_api.get("/v1/test").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )
    result = await http_transport.request("GET", "/v1/test")
    assert result == {"status": "ok"}


async def test_204_returns_none(mock_api, http_transport):
    """DELETE returning 204 yields None."""
    mock_api.delete("/v1/resource/123").mock(
        return_value=httpx.Response(204)
    )
    result = await http_transport.request("DELETE", "/v1/resource/123")
    assert result is None


async def test_401_raises_authentication_error(mock_api, http_transport):
    """401 response raises AuthenticationError."""
    mock_api.get("/v1/secret").mock(
        return_value=httpx.Response(401, json={"error": "Invalid credentials"})
    )
    with pytest.raises(AuthenticationError) as exc_info:
        await http_transport.request("GET", "/v1/secret")
    assert exc_info.value.status_code == 401
    assert "Invalid credentials" in str(exc_info.value)


async def test_404_raises_not_found(mock_api, http_transport):
    """404 response raises NotFoundError."""
    mock_api.get("/v1/missing").mock(
        return_value=httpx.Response(404, json={"error": "Not found"})
    )
    with pytest.raises(NotFoundError) as exc_info:
        await http_transport.request("GET", "/v1/missing")
    assert exc_info.value.status_code == 404


async def test_400_raises_validation_error(mock_api, http_transport):
    """400 response raises ValidationError."""
    mock_api.post("/v1/validate").mock(
        return_value=httpx.Response(400, json={"error": "Bad request"})
    )
    with pytest.raises(ValidationError) as exc_info:
        await http_transport.request("POST", "/v1/validate", json={"bad": "data"})
    assert exc_info.value.status_code == 400


async def test_429_retries_with_backoff(mock_api, fast_transport):
    """429 on first attempt retries, second attempt succeeds."""
    route = mock_api.get("/v1/limited")
    route.side_effect = [
        httpx.Response(429, json={"error": "Rate limited"}),
        httpx.Response(200, json={"ok": True}),
    ]
    result = await fast_transport.request("GET", "/v1/limited")
    assert result == {"ok": True}
    assert route.call_count == 2


async def test_429_respects_retry_after_header(mock_api, fast_transport):
    """429 with Retry-After header uses that value for sleep."""
    route = mock_api.get("/v1/throttled")
    route.side_effect = [
        httpx.Response(
            429,
            json={"error": "Rate limited"},
            headers={"Retry-After": "0.01"},
        ),
        httpx.Response(200, json={"done": True}),
    ]
    result = await fast_transport.request("GET", "/v1/throttled")
    assert result == {"done": True}
    assert route.call_count == 2


async def test_5xx_retries_then_raises(mock_api, fast_transport):
    """Persistent 503 exhausts retries and raises ServerError."""
    mock_api.get("/v1/broken").mock(
        return_value=httpx.Response(503, json={"error": "Service unavailable"})
    )
    with pytest.raises(ServerError) as exc_info:
        await fast_transport.request("GET", "/v1/broken")
    assert exc_info.value.status_code == 503


async def test_none_params_stripped(mock_api, http_transport):
    """None values in params dict are removed before the request."""
    route = mock_api.get("/v1/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    await http_transport.request(
        "GET", "/v1/search", params={"q": "hello", "page": None, "limit": 10}
    )
    sent_request = route.calls[0].request
    # None value for 'page' should be stripped
    assert b"page" not in sent_request.url.query
    assert b"q=hello" in sent_request.url.query
    assert b"limit=10" in sent_request.url.query
