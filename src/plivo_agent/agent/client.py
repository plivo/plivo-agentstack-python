"""Async REST client for Agent Stack APIs.

Provides AgentClient with sub-resources for agent CRUD, call management,
and number assignment -- all using the shared HttpTransport.
"""

from __future__ import annotations

from typing import Any

from plivo_agent._http import HttpTransport


class AgentResource:
    """Agent CRUD -- POST/GET/PATCH/DELETE /v1/Agent

    Agent IDs are UUIDs (e.g. "550e8400-e29b-41d4-a716-446655440000").
    Creating an agent requires ``agent_name``.
    """

    def __init__(self, http: HttpTransport) -> None:
        self._http = http

    async def create(self, **kwargs: Any) -> dict:
        """POST /v1/Agent

        Required fields: ``agent_name``, ``websocket_url``.
        Returns the created agent with ``agent_uuid`` as the identifier.
        """
        return await self._http.request("POST", "/v1/Agent", json=kwargs)

    async def get(self, agent_uuid: str) -> dict:
        """GET /v1/Agent/{agent_uuid}"""
        return await self._http.request("GET", f"/v1/Agent/{agent_uuid}")

    async def list(self, **params: Any) -> dict:
        """GET /v1/Agent -- paginated list.

        Optional query params: page, per_page, sort_by, sort_order,
        agent_mode, participant_mode.

        Returns ``{"data": [...], "meta": {"page", "per_page", "total", "total_pages"}}``.
        """
        return await self._http.request("GET", "/v1/Agent", params=params)

    async def update(self, agent_uuid: str, **kwargs: Any) -> dict:
        """PATCH /v1/Agent/{agent_uuid}"""
        return await self._http.request(
            "PATCH", f"/v1/Agent/{agent_uuid}", json=kwargs
        )

    async def delete(self, agent_uuid: str) -> None:
        """DELETE /v1/Agent/{agent_uuid}"""
        await self._http.request("DELETE", f"/v1/Agent/{agent_uuid}")


class CallResource:
    """Call management -- connect, initiate, dial."""

    def __init__(self, http: HttpTransport) -> None:
        self._http = http

    async def connect(self, call_uuid: str, agent_uuid: str) -> dict:
        """POST /v1/AgentCall/{call_uuid}/connect -- connect an active call to an agent."""
        return await self._http.request(
            "POST",
            f"/v1/AgentCall/{call_uuid}/connect",
            json={"agent_id": agent_uuid},
        )

    async def initiate(
        self,
        agent_uuid: str,
        from_: str,
        to: list[str] | str,
        *,
        voicemail_detect: bool = False,
        **kwargs: Any,
    ) -> dict:
        """POST /v1/AgentCall -- initiate an outbound call.

        Args:
            agent_uuid: Agent UUID to handle the call.
            from_: Caller ID (phone number).
            to: Recipient number(s).
            voicemail_detect: Enable async voicemail/machine detection.
                Detection result arrives via "voicemail.detected" WS event.
            **kwargs: dial_mode, caller_name, time_limit, ring_timeout, etc.
        """
        if isinstance(to, str):
            to = [to]
        body: dict[str, Any] = {"agent_id": agent_uuid, "from": from_, "to": to}
        if voicemail_detect:
            body["voicemail_detect"] = True
        body.update(kwargs)
        return await self._http.request("POST", "/v1/AgentCall", json=body)

    async def dial(
        self,
        call_uuid: str,
        targets: list[dict],
        **kwargs: Any,
    ) -> dict:
        """POST /v1/AgentCall/{call_uuid}/dial -- dial out to one or more targets.

        Args:
            call_uuid: Active call UUID.
            targets: List of dicts with "number" (and optional "send_digits").
            **kwargs: dial_mode, caller_id, timeout, time_limit, etc.
        """
        body: dict[str, Any] = {"targets": targets, **kwargs}
        return await self._http.request(
            "POST", f"/v1/AgentCall/{call_uuid}/dial", json=body
        )


class NumberResource:
    """Number management -- assign, list, unassign phone numbers for agents.

    Numbers are in E.164 format (e.g. "+14155551234").
    """

    def __init__(self, http: HttpTransport) -> None:
        self._http = http

    async def assign(self, agent_uuid: str, number: str) -> dict:
        """POST /v1/Agent/{agent_uuid}/Number -- assign a number to an agent."""
        return await self._http.request(
            "POST",
            f"/v1/Agent/{agent_uuid}/Number",
            json={"number": number},
        )

    async def list(self, agent_uuid: str) -> dict:
        """GET /v1/Agent/{agent_uuid}/Number -- list numbers for an agent."""
        return await self._http.request(
            "GET", f"/v1/Agent/{agent_uuid}/Number"
        )

    async def unassign(self, agent_uuid: str, number: str) -> None:
        """DELETE /v1/Agent/{agent_uuid}/Number/{number} -- unassign a number."""
        await self._http.request(
            "DELETE", f"/v1/Agent/{agent_uuid}/Number/{number}"
        )


class SessionResource:
    """Session history -- list and get agent sessions."""

    def __init__(self, http: HttpTransport) -> None:
        self._http = http

    async def list(self, agent_uuid: str, **params: Any) -> dict:
        """GET /v1/Agent/{agent_uuid}/Session -- list sessions.

        Optional query params: page, per_page, sort_by, sort_order, agent_mode.
        """
        return await self._http.request(
            "GET", f"/v1/Agent/{agent_uuid}/Session", params=params
        )

    async def get(self, agent_uuid: str, session_id: str) -> dict:
        """GET /v1/Agent/{agent_uuid}/Session/{session_id} -- get session details."""
        return await self._http.request(
            "GET", f"/v1/Agent/{agent_uuid}/Session/{session_id}"
        )


class AgentClient:
    """Agent Stack REST client -- attached to AsyncClient as ``client.agent``.

    Sub-resources:
        .agents   -- Agent CRUD (create/get/list/update/delete)
        .calls    -- Call management (connect/initiate/dial)
        .numbers  -- Number assignment (assign/list/unassign)
        .sessions -- Session history (list/get)
    """

    def __init__(self, http: HttpTransport) -> None:
        self._http = http
        self.agents = AgentResource(http)
        self.calls = CallResource(http)
        self.numbers = NumberResource(http)
        self.sessions = SessionResource(http)
