"""Tests for plivo_agentstack.agent.client — AgentClient REST operations."""

from __future__ import annotations

import json

import httpx
import pytest

from plivo_agentstack.agent.client import (
    EAGERNESS_PRESETS,
    AgentClient,
    _expand_semantic_vad,
)

AGENT_UUID = "550e8400-e29b-41d4-a716-446655440000"
CALL_UUID = "call-uuid-001"


async def test_create_agent(mock_api, http_transport):
    """POST /v1/Account/TESTAUTH123/Agent creates an agent."""
    mock_api.post("/v1/Account/TESTAUTH123/Agent").mock(
        return_value=httpx.Response(
            201,
            json={
                "api_id": "abc-123",
                "message": "agent created",
                "agent_uuid": AGENT_UUID,
                "agent_name": "My Agent",
            },
        )
    )
    client = AgentClient(http_transport)
    result = await client.agents.create(agent_name="My Agent", websocket_url="wss://example.com/ws")
    assert result["agent_uuid"] == AGENT_UUID
    assert result["agent_name"] == "My Agent"


async def test_get_agent(mock_api, http_transport):
    """GET /v1/Account/TESTAUTH123/Agent/{uuid} retrieves an agent."""
    mock_api.get(f"/v1/Account/TESTAUTH123/Agent/{AGENT_UUID}").mock(
        return_value=httpx.Response(
            200,
            json={"api_id": "abc-123", "agent_uuid": AGENT_UUID, "agent_name": "My Agent"},
        )
    )
    client = AgentClient(http_transport)
    result = await client.agents.get(AGENT_UUID)
    assert result["agent_uuid"] == AGENT_UUID


async def test_list_agents(mock_api, http_transport):
    """GET /v1/Account/TESTAUTH123/Agent lists agents with query params."""
    mock_api.get("/v1/Account/TESTAUTH123/Agent").mock(
        return_value=httpx.Response(
            200,
            json={
                "api_id": "abc-123",
                "objects": [{"agent_uuid": AGENT_UUID}],
                "meta": {
                    "limit": 10,
                    "offset": 0,
                    "total_count": 1,
                    "previous": None,
                    "next": None,
                },
            },
        )
    )
    client = AgentClient(http_transport)
    result = await client.agents.list(limit=10, offset=0)
    assert result["meta"]["total_count"] == 1
    assert len(result["objects"]) == 1


async def test_update_agent(mock_api, http_transport):
    """PATCH /v1/Account/TESTAUTH123/Agent/{uuid} updates an agent."""
    mock_api.patch(f"/v1/Account/TESTAUTH123/Agent/{AGENT_UUID}").mock(
        return_value=httpx.Response(
            200,
            json={"api_id": "abc-123", "agent_uuid": AGENT_UUID, "agent_name": "Updated Agent"},
        )
    )
    client = AgentClient(http_transport)
    result = await client.agents.update(AGENT_UUID, agent_name="Updated Agent")
    assert result["agent_name"] == "Updated Agent"


async def test_delete_agent(mock_api, http_transport):
    """DELETE /v1/Account/TESTAUTH123/Agent/{uuid} deletes an agent (204)."""
    mock_api.delete(f"/v1/Account/TESTAUTH123/Agent/{AGENT_UUID}").mock(
        return_value=httpx.Response(204)
    )
    client = AgentClient(http_transport)
    result = await client.agents.delete(AGENT_UUID)
    assert result is None


async def test_call_initiate(mock_api, http_transport):
    """POST /v1/Account/TESTAUTH123/AgentCall initiates an outbound call."""
    mock_api.post("/v1/Account/TESTAUTH123/AgentCall").mock(
        return_value=httpx.Response(
            201,
            json={
                "api_id": "abc-123",
                "message": "call initiated",
                "call_uuid": CALL_UUID,
                "status": "initiated",
            },
        )
    )
    client = AgentClient(http_transport)
    result = await client.calls.initiate(
        agent_uuid=AGENT_UUID,
        from_="+14155551234",
        to="+14155559876",
    )
    assert result["call_uuid"] == CALL_UUID
    assert result["status"] == "initiated"


async def test_call_connect(mock_api, http_transport):
    """POST /v1/Account/TESTAUTH123/AgentCall/{uuid}/connect connects a call to an agent."""
    mock_api.post(f"/v1/Account/TESTAUTH123/AgentCall/{CALL_UUID}/connect").mock(
        return_value=httpx.Response(
            201,
            json={
                "api_id": "abc-123",
                "message": "call connected",
                "agent_session_id": "sess-001",
                "status": "connecting",
            },
        )
    )
    client = AgentClient(http_transport)
    result = await client.calls.connect(CALL_UUID, AGENT_UUID)
    assert result["status"] == "connecting"
    assert result["agent_session_id"] == "sess-001"


async def test_number_assign(mock_api, http_transport):
    """POST /v1/Account/TESTAUTH123/Agent/{uuid}/Number assigns a number to an agent."""
    mock_api.post(f"/v1/Account/TESTAUTH123/Agent/{AGENT_UUID}/Number").mock(
        return_value=httpx.Response(
            201,
            json={
                "api_id": "abc-123",
                "message": "number assigned",
                "agent_uuid": AGENT_UUID,
                "number": "+14155551234",
            },
        )
    )
    client = AgentClient(http_transport)
    result = await client.numbers.assign(AGENT_UUID, "+14155551234")
    assert result["message"] == "number assigned"
    assert result["number"] == "+14155551234"


async def test_number_unassign(mock_api, http_transport):
    """DELETE /v1/Account/TESTAUTH123/Agent/{uuid}/Number/{num} unassigns a number."""
    number = "+14155551234"
    mock_api.delete(f"/v1/Account/TESTAUTH123/Agent/{AGENT_UUID}/Number/{number}").mock(
        return_value=httpx.Response(204)
    )
    client = AgentClient(http_transport)
    result = await client.numbers.unassign(AGENT_UUID, number)
    assert result is None


SESSION_ID = "sess-001"


async def test_session_list(mock_api, http_transport):
    """GET /v1/Account/TESTAUTH123/AgentSession lists sessions."""
    mock_api.get("/v1/Account/TESTAUTH123/AgentSession").mock(
        return_value=httpx.Response(
            200,
            json={
                "api_id": "abc-123",
                "objects": [
                    {"agent_session_id": SESSION_ID, "duration_seconds": 120}
                ],
                "meta": {
                    "limit": 10,
                    "offset": 0,
                    "total_count": 1,
                    "previous": None,
                    "next": None,
                },
            },
        )
    )
    client = AgentClient(http_transport)
    result = await client.sessions.list(limit=10, offset=0)
    assert result["meta"]["total_count"] == 1
    assert result["objects"][0]["agent_session_id"] == SESSION_ID


async def test_session_list_with_filters(mock_api, http_transport):
    """GET /v1/Account/TESTAUTH123/AgentSession passes filter params."""
    mock_api.get("/v1/Account/TESTAUTH123/AgentSession").mock(
        return_value=httpx.Response(
            200,
            json={
                "api_id": "abc-123",
                "objects": [],
                "meta": {
                    "limit": 20,
                    "offset": 0,
                    "total_count": 0,
                    "previous": None,
                    "next": None,
                },
            },
        )
    )
    client = AgentClient(http_transport)
    result = await client.sessions.list(
        agent_id=AGENT_UUID, phone_number="+14155551234"
    )
    assert result["meta"]["total_count"] == 0
    request = mock_api.calls[0].request
    assert request.url.params["agent_id"] == AGENT_UUID
    assert request.url.params["phone_number"] == "+14155551234"


async def test_session_get(mock_api, http_transport):
    """GET /v1/Account/TESTAUTH123/AgentSession/{session_id} gets session details."""
    mock_api.get(f"/v1/Account/TESTAUTH123/AgentSession/{SESSION_ID}").mock(
        return_value=httpx.Response(
            200,
            json={
                "api_id": "abc-123",
                "agent_session_id": SESSION_ID,
                "agent_uuid": AGENT_UUID,
                "duration_seconds": 120,
                "turn_count": 5,
            },
        )
    )
    client = AgentClient(http_transport)
    result = await client.sessions.get(SESSION_ID)
    assert result["agent_session_id"] == SESSION_ID
    assert result["duration_seconds"] == 120
    assert result["turn_count"] == 5


# ---------------------------------------------------------------------------
# semantic_vad expansion tests
# ---------------------------------------------------------------------------


def test_expand_semantic_vad_string_preset():
    """String presets expand to the full eagerness config dict."""
    result = _expand_semantic_vad("high")
    assert result == EAGERNESS_PRESETS["high"]
    assert result["completed_turn_delay_ms"] == 150


def test_expand_semantic_vad_auto():
    """'auto' preset expands to an empty dict (server defaults)."""
    result = _expand_semantic_vad("auto")
    assert result == {}


def test_expand_semantic_vad_unknown_string():
    """Unknown string preset raises ValueError."""
    with pytest.raises(ValueError, match="Unknown semantic_vad preset"):
        _expand_semantic_vad("turbo")


def test_expand_semantic_vad_dict_with_eagerness():
    """Dict with 'eagerness' key merges preset with explicit overrides."""
    result = _expand_semantic_vad({"eagerness": "low", "completed_turn_delay_ms": 800})
    # Base from "low" preset, overridden completed_turn_delay_ms
    assert result["completed_turn_delay_ms"] == 800
    expected = EAGERNESS_PRESETS["low"]["incomplete_turn_delay_ms"]
    assert result["incomplete_turn_delay_ms"] == expected


def test_expand_semantic_vad_raw_dict():
    """Dict without 'eagerness' passes through as-is."""
    raw = {"completed_turn_delay_ms": 999, "custom_field": True}
    result = _expand_semantic_vad(raw)
    assert result["completed_turn_delay_ms"] == 999
    assert result["custom_field"] is True


def test_expand_semantic_vad_none():
    """None returns None (no semantic_vad config)."""
    assert _expand_semantic_vad(None) is None


def test_expand_semantic_vad_invalid_type():
    """Non-str/dict/None raises TypeError."""
    with pytest.raises(TypeError, match="semantic_vad must be str, dict, or None"):
        _expand_semantic_vad(42)


async def test_create_agent_with_semantic_vad_preset(mock_api, http_transport):
    """create() expands semantic_vad string preset before sending the request."""
    mock_api.post("/v1/Account/TESTAUTH123/Agent").mock(
        return_value=httpx.Response(
            201,
            json={
                "api_id": "abc-123",
                "message": "agent created",
                "agent_uuid": AGENT_UUID,
            },
        )
    )
    client = AgentClient(http_transport)
    await client.agents.create(
        agent_name="VAD Agent",
        websocket_url="wss://example.com/ws",
        semantic_vad="medium",
    )
    request = mock_api.calls[0].request
    body = json.loads(request.content)
    assert body["semantic_vad"] == EAGERNESS_PRESETS["medium"]


async def test_update_agent_with_semantic_vad_preset(mock_api, http_transport):
    """update() expands semantic_vad string preset before sending the request."""
    mock_api.patch(f"/v1/Account/TESTAUTH123/Agent/{AGENT_UUID}").mock(
        return_value=httpx.Response(
            200,
            json={"api_id": "abc-123", "agent_uuid": AGENT_UUID},
        )
    )
    client = AgentClient(http_transport)
    await client.agents.update(AGENT_UUID, semantic_vad="high")
    request = mock_api.calls[0].request
    body = json.loads(request.content)
    assert body["semantic_vad"] == EAGERNESS_PRESETS["high"]
