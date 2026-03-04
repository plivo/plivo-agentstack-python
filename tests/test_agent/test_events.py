"""Tests for plivo_agent.agent.events — event parsing and typed models."""

from __future__ import annotations

from plivo_agent.agent.events import (
    _EVENT_REGISTRY,
    AgentSessionStarted,
    Dtmf,
    StreamMedia,
    StreamStart,
    ToolCall,
    TurnCompleted,
    TurnMetrics,
    parse_event,
)


def test_parse_agent_session_started():
    """agent_session.started is parsed into AgentSessionStarted."""
    data = {
        "type": "agent_session.started",
        "agent_session_id": "sess-001",
        "call_id": "call-001",
        "caller": "+14155551234",
        "callee": "+14155559876",
        "agent_id": "agent-uuid-1",
        "audio_format": "pcm",
        "sample_rate": 16000,
        "channels": 1,
        "frame_size_ms": 20,
        "plc_enabled": True,
    }
    event = parse_event(data)
    assert isinstance(event, AgentSessionStarted)
    assert event.agent_session_id == "sess-001"
    assert event.call_id == "call-001"
    assert event.caller == "+14155551234"
    assert event.callee == "+14155559876"
    assert event.agent_id == "agent-uuid-1"
    assert event.audio_format == "pcm"
    assert event.sample_rate == 16000
    assert event.channels == 1
    assert event.frame_size_ms == 20
    assert event.plc_enabled is True


def test_parse_tool_call():
    """tool_call is parsed into ToolCall with arguments dict."""
    data = {
        "type": "tool_call",
        "id": "tc-42",
        "name": "lookup_order",
        "arguments": {"order_id": "ORD-123"},
    }
    event = parse_event(data)
    assert isinstance(event, ToolCall)
    assert event.id == "tc-42"
    assert event.name == "lookup_order"
    assert event.arguments == {"order_id": "ORD-123"}


def test_parse_turn_completed():
    """turn.completed is parsed into TurnCompleted."""
    data = {
        "type": "turn.completed",
        "user_text": "What is my balance?",
        "agent_text": "Your balance is $42.00.",
        "turn_id": "turn-7",
    }
    event = parse_event(data)
    assert isinstance(event, TurnCompleted)
    assert event.user_text == "What is my balance?"
    assert event.agent_text == "Your balance is $42.00."
    assert event.turn_id == "turn-7"


def test_parse_turn_metrics():
    """turn.metrics is parsed into TurnMetrics with key fields populated."""
    data = {
        "type": "turn.metrics",
        "turn_number": 3,
        "interrupted": False,
        "user_perceived_ms": 850,
        "stt_delay_ms": 120,
        "llm_ttft_ms": 300,
        "llm_prompt_tokens": 1500,
        "llm_completion_tokens": 200,
        "llm_model": "gpt-4o",
        "tts_ttfb_ms": 150,
        "stt_provider": "deepgram",
        "llm_provider": "openai",
        "tts_provider": "elevenlabs",
    }
    event = parse_event(data)
    assert isinstance(event, TurnMetrics)
    assert event.turn_number == 3
    assert event.interrupted is False
    assert event.user_perceived_ms == 850
    assert event.stt_delay_ms == 120
    assert event.llm_ttft_ms == 300
    assert event.llm_prompt_tokens == 1500
    assert event.llm_completion_tokens == 200
    assert event.llm_model == "gpt-4o"
    assert event.tts_ttfb_ms == 150
    assert event.stt_provider == "deepgram"
    assert event.llm_provider == "openai"
    assert event.tts_provider == "elevenlabs"


def test_parse_nested_stream_start():
    """Nested 'start' event extracts stream metadata from the start sub-dict."""
    data = {
        "event": "start",
        "streamId": "stream-abc",
        "start": {
            "streamId": "stream-abc",
            "callId": "call-xyz",
            "mediaFormat": {
                "type": "audio/x-mulaw",
                "rate": 8000,
            },
        },
    }
    event = parse_event(data)
    assert isinstance(event, StreamStart)
    assert event.event == "start"
    assert event.stream_id == "stream-abc"
    assert event.call_id == "call-xyz"
    assert event.content_type == "audio/x-mulaw"
    assert event.sample_rate == 8000


def test_parse_nested_stream_media():
    """Nested 'media' event extracts payload from the media sub-dict."""
    data = {
        "event": "media",
        "media": {
            "payload": "SGVsbG8gV29ybGQ=",
            "contentType": "audio/x-mulaw",
            "sampleRate": 8000,
            "timestamp": "2025-01-01T00:00:00Z",
        },
    }
    event = parse_event(data)
    assert isinstance(event, StreamMedia)
    assert event.payload == "SGVsbG8gV29ybGQ="
    assert event.content_type == "audio/x-mulaw"
    assert event.sample_rate == 8000
    assert event.timestamp == "2025-01-01T00:00:00Z"


def test_parse_nested_stream_dtmf():
    """Nested 'dtmf' event (audio stream mode) extracts digit from sub-dict.

    The registry maps "dtmf" to the managed-mode Dtmf class. When the data
    also contains a nested "dtmf" dict (audio stream protocol), the parser
    extracts the digit from that nested dict into the Dtmf dataclass.
    """
    data = {
        "event": "dtmf",
        "dtmf": {
            "digit": "5",
        },
    }
    event = parse_event(data)
    # Registry maps "dtmf" -> Dtmf (managed-mode), not StreamDtmf
    assert isinstance(event, Dtmf)
    assert event.digit == "5"


def test_unknown_event_returns_raw_dict():
    """Unknown event type returns the raw dict unchanged."""
    data = {"type": "some.future.event", "data": "value"}
    result = parse_event(data)
    assert result is data
    assert isinstance(result, dict)


def test_extra_fields_ignored():
    """Extra fields not in the dataclass are silently dropped."""
    data = {
        "type": "tool_call",
        "id": "tc-99",
        "name": "my_tool",
        "arguments": {},
        "extra_field": "should be ignored",
        "another_extra": 42,
    }
    event = parse_event(data)
    assert isinstance(event, ToolCall)
    assert event.id == "tc-99"
    assert not hasattr(event, "extra_field")


def test_all_event_types_in_registry():
    """Registry contains all expected event types (managed + audio stream)."""
    # Managed-mode events
    managed_types = {
        "agent_session.started",
        "tool_call",
        "turn.completed",
        "prompt",
        "dtmf",
        "interruption",
        "agent_session.ended",
        "error",
        "vad.speech_started",
        "vad.speech_stopped",
        "turn.detected",
        "voicemail.detected",
        "voicemail.beep",
        "participant.added",
        "participant.removed",
        "call.transferred",
        "play.completed",
        "user.idle",
        "turn.metrics",
        "agent.handoff",
    }
    # Audio stream events
    stream_types = {
        "start",
        "media",
        "playedStream",
        "clearedAudio",
        "stop",
    }
    expected = managed_types | stream_types
    assert set(_EVENT_REGISTRY.keys()) == expected
    assert len(_EVENT_REGISTRY) == 25
