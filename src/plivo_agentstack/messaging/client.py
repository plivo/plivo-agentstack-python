"""Messages REST client -- send and manage SMS, MMS, WhatsApp messages."""

from __future__ import annotations

from typing import Any

from plivo_agentstack._http import HttpTransport


class MessagesClient:
    """Messages CRUD -- send SMS, MMS, WhatsApp messages.

    Usage::
        async with AsyncClient(auth_id, auth_token) as client:
            resp = await client.messages.create(
                src="+14155551234",
                dst="+14155559876",
                text="Hello from Plivo!",
            )
    """

    def __init__(self, http: HttpTransport) -> None:
        self._http = http

    async def create(
        self,
        *,
        dst: str,
        src: str | None = None,
        text: str | None = None,
        type_: str = "sms",
        url: str | None = None,
        method: str = "POST",
        media_urls: list[str] | None = None,
        media_ids: list[str] | None = None,
        powerpack_uuid: str | None = None,
        template: dict | None = None,
        interactive: dict | None = None,
        location: dict | None = None,
        log: bool | None = None,
        trackable: bool | None = None,
        message_expiry: int | None = None,
        dlt_entity_id: str | None = None,
        dlt_template_id: str | None = None,
        dlt_template_category: str | None = None,
    ) -> dict:
        """Send a message (SMS, MMS, or WhatsApp)."""
        body: dict[str, Any] = {"dst": dst}
        if src:
            body["src"] = src
        if text is not None:
            body["text"] = text
        if type_ != "sms":
            body["type"] = type_
        if url:
            body["url"] = url
        if method != "POST":
            body["method"] = method
        if media_urls:
            body["media_urls"] = media_urls
        if media_ids:
            body["media_ids"] = media_ids
        if powerpack_uuid:
            body["powerpack_uuid"] = powerpack_uuid
        if template:
            body["template"] = template
        if interactive:
            body["interactive"] = interactive
        if location:
            body["location"] = location
        if log is not None:
            body["log"] = log
        if trackable is not None:
            body["trackable"] = trackable
        if message_expiry is not None:
            body["message_expiry"] = message_expiry
        if dlt_entity_id:
            body["dlt_entity_id"] = dlt_entity_id
        if dlt_template_id:
            body["dlt_template_id"] = dlt_template_id
        if dlt_template_category:
            body["dlt_template_category"] = dlt_template_category

        return await self._http.request(
            "POST",
            f"/v1/Account/{self._http.auth_id}/Message/",
            json=body,
        )

    async def get(self, message_uuid: str) -> dict:
        """Get message details."""
        return await self._http.request(
            "GET",
            f"/v1/Account/{self._http.auth_id}/Message/{message_uuid}/",
        )

    async def list(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        message_direction: str | None = None,
        message_state: str | None = None,
        message_type: str | None = None,
        message_time__gt: str | None = None,
        message_time__gte: str | None = None,
        message_time__lt: str | None = None,
        message_time__lte: str | None = None,
        subaccount: str | None = None,
        error_code: int | None = None,
        powerpack_id: str | None = None,
        from_number: str | None = None,
        to_number: str | None = None,
        conversation_id: str | None = None,
        conversation_origin: str | None = None,
        **kwargs: Any,
    ) -> dict:
        """List messages with filters."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        for key, val in {
            "message_direction": message_direction,
            "message_state": message_state,
            "message_type": message_type,
            "message_time__gt": message_time__gt,
            "message_time__gte": message_time__gte,
            "message_time__lt": message_time__lt,
            "message_time__lte": message_time__lte,
            "subaccount": subaccount,
            "error_code": error_code,
            "powerpack_id": powerpack_id,
            "from_number": from_number,
            "to_number": to_number,
            "conversation_id": conversation_id,
            "conversation_origin": conversation_origin,
        }.items():
            if val is not None:
                params[key] = val
        params.update(kwargs)

        return await self._http.request(
            "GET",
            f"/v1/Account/{self._http.auth_id}/Message/",
            params=params,
        )

    async def list_media(self, message_uuid: str) -> dict:
        """List media files for a message."""
        return await self._http.request(
            "GET",
            f"/v1/Account/{self._http.auth_id}/Message/{message_uuid}/Media/",
        )
