"""Tests for plivo_agentstack.messaging.client — MessagesClient REST operations."""

from __future__ import annotations

import httpx

from plivo_agentstack.messaging.client import MessagesClient

AUTH_ID = "TESTAUTH123"
MSG_UUID = "msg-uuid-001"


async def test_create_sms(mock_api, http_transport):
    """POST creates an SMS message with src, dst, text."""
    mock_api.post(f"/v1/Account/{AUTH_ID}/Message/").mock(
        return_value=httpx.Response(
            200,
            json={"message_uuid": [MSG_UUID], "api_id": "api-1"},
        )
    )
    client = MessagesClient(http_transport)
    result = await client.create(
        src="+14155551234",
        dst="+14155559876",
        text="Hello from Plivo!",
    )
    assert result["message_uuid"] == [MSG_UUID]


async def test_create_whatsapp(mock_api, http_transport):
    """POST creates a WhatsApp message with type_ and template."""
    mock_api.post(f"/v1/Account/{AUTH_ID}/Message/").mock(
        return_value=httpx.Response(
            200,
            json={"message_uuid": [MSG_UUID]},
        )
    )
    template = {"name": "hello_world", "language": "en"}
    client = MessagesClient(http_transport)
    result = await client.create(
        src="+14155551234",
        dst="+14155559876",
        type_="whatsapp",
        template=template,
    )
    assert result["message_uuid"] == [MSG_UUID]

    # Verify the request body includes the type and template
    sent_body = mock_api.calls[0].request
    import json

    body = json.loads(sent_body.content)
    assert body["type"] == "whatsapp"
    assert body["template"] == template


async def test_create_mms(mock_api, http_transport):
    """POST creates an MMS message with media_urls."""
    mock_api.post(f"/v1/Account/{AUTH_ID}/Message/").mock(
        return_value=httpx.Response(
            200,
            json={"message_uuid": [MSG_UUID]},
        )
    )
    media = ["https://example.com/image.jpg"]
    client = MessagesClient(http_transport)
    result = await client.create(
        src="+14155551234",
        dst="+14155559876",
        text="Check this out",
        media_urls=media,
    )
    assert result["message_uuid"] == [MSG_UUID]

    import json

    body = json.loads(mock_api.calls[0].request.content)
    assert body["media_urls"] == media


async def test_get_message(mock_api, http_transport):
    """GET retrieves a message by UUID."""
    mock_api.get(f"/v1/Account/{AUTH_ID}/Message/{MSG_UUID}/").mock(
        return_value=httpx.Response(
            200,
            json={"message_uuid": MSG_UUID, "message_state": "delivered"},
        )
    )
    client = MessagesClient(http_transport)
    result = await client.get(MSG_UUID)
    assert result["message_uuid"] == MSG_UUID
    assert result["message_state"] == "delivered"


async def test_list_messages(mock_api, http_transport):
    """GET lists messages with filters."""
    mock_api.get(f"/v1/Account/{AUTH_ID}/Message/").mock(
        return_value=httpx.Response(
            200,
            json={
                "objects": [{"message_uuid": MSG_UUID}],
                "meta": {"total_count": 1},
            },
        )
    )
    client = MessagesClient(http_transport)
    result = await client.list(limit=5, message_state="delivered")
    assert len(result["objects"]) == 1
    assert result["meta"]["total_count"] == 1


async def test_list_media(mock_api, http_transport):
    """GET lists media files for a message."""
    mock_api.get(f"/v1/Account/{AUTH_ID}/Message/{MSG_UUID}/Media/").mock(
        return_value=httpx.Response(
            200,
            json={
                "objects": [
                    {"media_id": "media-1", "content_type": "image/jpeg"}
                ]
            },
        )
    )
    client = MessagesClient(http_transport)
    result = await client.list_media(MSG_UUID)
    assert len(result["objects"]) == 1
    assert result["objects"][0]["media_id"] == "media-1"
