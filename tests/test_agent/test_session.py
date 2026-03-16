"""Tests for plivo_agentstack.agent.session.Session."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from plivo_agentstack.agent.session import Session


def _make_session() -> Session:
    """Create a Session with a mock WS and the running event loop."""
    loop = asyncio.get_event_loop()
    ws = MagicMock()
    session = Session(ws, loop)
    return session


async def _drain(session: Session) -> dict:
    """Get the next message from the session's internal queue.

    call_soon_threadsafe schedules put_nowait as a callback on the loop.
    We must yield control so the loop processes that callback before reading.
    """
    await asyncio.sleep(0)
    return session._queue.get_nowait()


async def test_send_tool_result_enqueues():
    """send_tool_result enqueues a tool.result message."""
    session = _make_session()
    session.send_tool_result("tc-1", {"answer": 42})
    msg = await _drain(session)
    assert msg == {"type": "tool.result", "id": "tc-1", "result": {"answer": 42}}


async def test_send_tool_error_enqueues():
    """send_tool_error enqueues a tool.error message."""
    session = _make_session()
    session.send_tool_error("tc-2", "something broke")
    msg = await _drain(session)
    assert msg == {"type": "tool.error", "id": "tc-2", "error": "something broke"}


async def test_send_text_enqueues():
    """send_text enqueues a text token message."""
    session = _make_session()
    session.send_text("Hello", last=True)
    msg = await _drain(session)
    assert msg == {"type": "text", "token": "Hello", "last": True}


async def test_hangup_enqueues():
    """hangup enqueues a hangup message."""
    session = _make_session()
    session.hangup()
    msg = await _drain(session)
    assert msg == {"type": "agent_session.hangup"}


async def test_transfer_string():
    """transfer with a single string wraps it into a list."""
    session = _make_session()
    session.transfer("+14155551234")
    msg = await _drain(session)
    assert msg["type"] == "agent_session.transfer"
    assert msg["destination"] == ["+14155551234"]
    assert msg["dial_mode"] == "parallel"
    assert msg["timeout"] == 30


async def test_transfer_list():
    """transfer with a list passes destinations through."""
    session = _make_session()
    session.transfer(["+14155551234", "+18005559876"], dial_mode="sequential")
    msg = await _drain(session)
    assert msg["destination"] == ["+14155551234", "+18005559876"]
    assert msg["dial_mode"] == "sequential"


async def test_transfer_with_timeout():
    """transfer passes custom timeout."""
    session = _make_session()
    session.transfer("+14155551234", timeout=15)
    msg = await _drain(session)
    assert msg["type"] == "agent_session.transfer"
    assert msg["destination"] == ["+14155551234"]
    assert msg["timeout"] == 15


async def test_send_dtmf_enqueues():
    """send_dtmf enqueues an agent_session.send_dtmf message."""
    session = _make_session()
    session.send_dtmf("123#")
    msg = await _drain(session)
    assert msg == {"type": "agent_session.send_dtmf", "digits": "123#"}


async def test_handoff_enqueues_update_and_inject():
    """handoff sends an update message with system_prompt, tools, llm, then injects summary."""
    session = _make_session()
    session.handoff(
        system_prompt="You are a billing specialist.",
        tools=[{"name": "check_balance"}],
        llm={"model": "gpt-4o"},
        summary="Customer wants to check their balance.",
    )
    # First message: agent_session.update with system_prompt, tools, llm
    update_msg = await _drain(session)
    assert update_msg["type"] == "agent_session.update"
    assert update_msg["system_prompt"] == "You are a billing specialist."
    assert update_msg["tools"] == [{"name": "check_balance"}]
    assert update_msg["llm"] == {"model": "gpt-4o"}

    # Second message: agent_session.inject with summary
    inject_msg = await _drain(session)
    assert inject_msg["type"] == "agent_session.inject"
    assert inject_msg["content"] == "Customer wants to check their balance."


async def test_handoff_without_optional_params():
    """handoff with only system_prompt sends a single update message."""
    session = _make_session()
    session.handoff(system_prompt="You are a new agent.")
    update_msg = await _drain(session)
    assert update_msg["type"] == "agent_session.update"
    assert update_msg["system_prompt"] == "You are a new agent."
    assert "tools" not in update_msg
    assert "llm" not in update_msg
    # No inject message when summary is None
    assert session._queue.empty()


async def test_play_background_enqueues():
    """play_background enqueues an audio.mix message."""
    session = _make_session()
    session.play_background("hold_music", volume=0.3, loop=False)
    msg = await _drain(session)
    assert msg == {
        "type": "audio.mix",
        "sound": "hold_music",
        "volume": 0.3,
        "loop": False,
    }


async def test_session_data_dict():
    """session.data is an accessible dict for per-session state."""
    session = _make_session()
    assert session.data == {}
    session.data["customer_id"] = "cust-42"
    assert session.data["customer_id"] == "cust-42"
