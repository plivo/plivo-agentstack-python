"""Tests for plivo_agentstack.agent.client — AgentClient REST operations."""

from __future__ import annotations

import httpx

from plivo_agentstack.agent.client import AgentClient

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
    """GET /v1/Account/TESTAUTH123/Agent/{uuid}/Session lists sessions."""
    mock_api.get(f"/v1/Account/TESTAUTH123/Agent/{AGENT_UUID}/Session").mock(
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
    result = await client.sessions.list(AGENT_UUID, limit=10, offset=0)
    assert result["meta"]["total_count"] == 1
    assert result["objects"][0]["agent_session_id"] == SESSION_ID


async def test_session_get(mock_api, http_transport):
    """GET /v1/Account/TESTAUTH123/Agent/{uuid}/Session/{session_id} gets session details."""
    mock_api.get(f"/v1/Account/TESTAUTH123/Agent/{AGENT_UUID}/Session/{SESSION_ID}").mock(
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
    result = await client.sessions.get(AGENT_UUID, SESSION_ID)
    assert result["agent_session_id"] == SESSION_ID
    assert result["duration_seconds"] == 120
    assert result["turn_count"] == 5
