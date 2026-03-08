"""Shared test fixtures for the plivo_agentstack SDK test suite."""

from __future__ import annotations

import pytest
import respx

from plivo_agentstack._http import HttpTransport
from plivo_agentstack.client import AsyncClient

AUTH_ID = "TESTAUTH123"
AUTH_TOKEN = "test_token_secret"
BASE_URL = "https://api.plivo.com"


@pytest.fixture()
def mock_api():
    """respx mock router scoped to the Plivo API base URL."""
    with respx.mock(base_url=BASE_URL) as router:
        yield router


@pytest.fixture()
def http_transport(mock_api):
    """HttpTransport configured with test credentials and the mock router active."""
    return HttpTransport(
        AUTH_ID,
        AUTH_TOKEN,
        BASE_URL,
        timeout=5.0,
        max_retries=3,
        backoff_factor=0.01,
    )


@pytest.fixture()
async def client(mock_api):
    """AsyncClient with test credentials — yields, then closes."""
    c = AsyncClient(AUTH_ID, AUTH_TOKEN, BASE_URL, timeout=5.0, max_retries=3)
    yield c
    await c.close()
