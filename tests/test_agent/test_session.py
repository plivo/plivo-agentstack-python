"""Tests for plivo_agent.agent.session.Session."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from plivo_agent.agent.session import Session


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
    """send_tool_result enqueues a tool_result message."""
    session = _make_session()
    session.send_tool_result("tc-1", {"answer": 42})
    msg = await _drain(session)
    assert msg == {"type": "tool_result", "id": "tc-1", "result": {"answer": 42}}


async def test_send_tool_error_enqueues():
    """send_tool_error enqueues a tool_error message."""
    session = _make_session()
    session.send_tool_error("tc-2", "something broke")
    msg = await _drain(session)
    assert msg == {"type": "tool_error", "id": "tc-2", "error": "something broke"}


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


async def test_transfer_to_number_string():
    """transfer_to_number with a single string wraps it into a list."""
    session = _make_session()
    session.transfer_to_number("+14155551234")
    msg = await _drain(session)
    assert msg["type"] == "agent_session.transfer"
    assert msg["destination"] == ["+14155551234"]
    assert msg["dial_mode"] == "parallel"
    assert msg["timeout"] == 30


async def test_transfer_to_number_list():
    """transfer_to_number with a list passes destinations through."""
    session = _make_session()
    session.transfer_to_number(["+14155551234", "+18005559876"], dial_mode="sequential")
    msg = await _drain(session)
    assert msg["destination"] == ["+14155551234", "+18005559876"]
    assert msg["dial_mode"] == "sequential"


async def test_transfer_to_sip():
    """transfer_to_sip sends SIP URI with sip flag."""
    session = _make_session()
    session.transfer_to_sip("sip:agent@phone.plivo.com")
    msg = await _drain(session)
    assert msg["type"] == "agent_session.transfer"
    assert msg["destination"] == ["sip:agent@phone.plivo.com"]
    assert msg["sip"] is True
    assert msg["timeout"] == 30
    assert "sip_headers" not in msg


async def test_transfer_to_sip_with_headers():
    """transfer_to_sip includes custom SIP headers when provided."""
    session = _make_session()
    session.transfer_to_sip(
        "sip:agent@pbx.example.com",
        sip_headers={"X-Agent-Id": "a42", "X-Context": "escalation"},
        timeout=15,
    )
    msg = await _drain(session)
    assert msg["destination"] == ["sip:agent@pbx.example.com"]
    assert msg["sip"] is True
    assert msg["sip_headers"] == {"X-Agent-Id": "a42", "X-Context": "escalation"}
    assert msg["timeout"] == 15


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
