"""Tests for plivo_agent.numbers.client — NumbersClient REST operations."""

from __future__ import annotations

import httpx

from plivo_agent.numbers.client import NumbersClient

AUTH_ID = "TESTAUTH123"
NUMBER = "+14155551234"


async def test_list_numbers(mock_api, http_transport):
    """GET /v1/Account/{id}/Number/ lists owned numbers."""
    mock_api.get(f"/v1/Account/{AUTH_ID}/Number/").mock(
        return_value=httpx.Response(
            200,
            json={
                "objects": [{"number": NUMBER}],
                "meta": {"total_count": 1},
            },
        )
    )
    client = NumbersClient(http_transport)
    result = await client.list(limit=10)
    assert len(result["objects"]) == 1
    assert result["objects"][0]["number"] == NUMBER


async def test_get_number(mock_api, http_transport):
    """GET /v1/Account/{id}/Number/{number}/ retrieves number details."""
    mock_api.get(f"/v1/Account/{AUTH_ID}/Number/{NUMBER}/").mock(
        return_value=httpx.Response(
            200,
            json={"number": NUMBER, "alias": "main-line"},
        )
    )
    client = NumbersClient(http_transport)
    result = await client.get(NUMBER)
    assert result["number"] == NUMBER
    assert result["alias"] == "main-line"


async def test_buy_number(mock_api, http_transport):
    """POST /v1/Account/{id}/PhoneNumber/{num}/ buys a number."""
    mock_api.post(f"/v1/Account/{AUTH_ID}/PhoneNumber/{NUMBER}/").mock(
        return_value=httpx.Response(
            200,
            json={"status": "fulfilled", "numbers": [{"number": NUMBER}]},
        )
    )
    client = NumbersClient(http_transport)
    result = await client.buy(NUMBER)
    assert result["status"] == "fulfilled"
    assert result["numbers"][0]["number"] == NUMBER


async def test_search_numbers(mock_api, http_transport):
    """GET /v1/Account/{id}/PhoneNumber/ searches available numbers."""
    mock_api.get(f"/v1/Account/{AUTH_ID}/PhoneNumber/").mock(
        return_value=httpx.Response(
            200,
            json={
                "objects": [{"number": NUMBER, "type": "local"}],
                "meta": {"total_count": 1},
            },
        )
    )
    client = NumbersClient(http_transport)
    result = await client.search("US", type="local")
    assert len(result["objects"]) == 1
    assert result["objects"][0]["type"] == "local"

    # Verify country_iso was sent as a query param
    sent_request = mock_api.calls[0].request
    assert b"country_iso=US" in sent_request.url.query


async def test_update_number(mock_api, http_transport):
    """POST /v1/Account/{id}/Number/{number}/ updates number configuration."""
    mock_api.post(f"/v1/Account/{AUTH_ID}/Number/{NUMBER}/").mock(
        return_value=httpx.Response(
            200,
            json={"message": "changed", "api_id": "api-1"},
        )
    )
    client = NumbersClient(http_transport)
    result = await client.update(NUMBER, alias="new-alias")
    assert result["message"] == "changed"


async def test_delete_number(mock_api, http_transport):
    """DELETE /v1/Account/{id}/Number/{number}/ unrents a number (204)."""
    mock_api.delete(f"/v1/Account/{AUTH_ID}/Number/{NUMBER}/").mock(
        return_value=httpx.Response(204)
    )
    client = NumbersClient(http_transport)
    result = await client.delete(NUMBER)
    assert result is None


async def test_lookup(mock_api, http_transport):
    """GET /v1/Number/{number} looks up carrier information."""
    mock_api.get(f"/v1/Number/{NUMBER}").mock(
        return_value=httpx.Response(
            200,
            json={
                "phone_number": NUMBER,
                "carrier": {"name": "Verizon"},
                "type": "mobile",
            },
        )
    )
    client = NumbersClient(http_transport)
    result = await client.lookup.get(NUMBER)
    assert result["phone_number"] == NUMBER
    assert result["carrier"]["name"] == "Verizon"
    assert result["type"] == "mobile"
