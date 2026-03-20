"""Tests for plivo_agentstack.agent.events — event parsing and typed models."""

from __future__ import annotations

from plivo_agentstack.agent.events import (
    _EVENT_REGISTRY,
    AgentFalseInterruption,
    AgentSessionEnded,
    AgentSessionStarted,
    AgentSpeechCompleted,
    AgentSpeechCreated,
    AgentToolCompleted,
    DtmfSent,
    Interruption,
    LlmAvailabilityChanged,
    Prompt,
    SessionUsage,
    StreamDtmf,
    StreamMedia,
    StreamStart,
    ToolCall,
    ToolExecuted,
    TurnCompleted,
    TurnDetected,
    TurnMetrics,
    UserBackchannel,
    VadSpeechStarted,
    VadSpeechStopped,
    parse_event,
)


def test_parse_agent_session_started():
    """session.started is parsed into AgentSessionStarted."""
    data = {
        "type": "session.started",
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
    """tool.called is parsed into ToolCall with arguments dict."""
    data = {
        "type": "tool.called",
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
    """turn.completed is parsed into TurnCompleted with all fields."""
    data = {
        "type": "turn.completed",
        "turn_number": 5,
        "user_text": "What is my balance?",
        "agent_text": "Your balance is $42.00.",
        "turn_id": "turn-7",
        "agent_first": True,
        "agent_tool_id": "tool-99",
        "turn_decision_s": 0.25,
        "transcription_delay_s": 0.12,
        "llm_ttft_s": 0.3,
        "tts_ttfb_s": 0.15,
        "realtime_ttft_s": 0.08,
        "user_started_speaking_at": "2025-06-01T12:00:00Z",
        "user_stopped_speaking_at": "2025-06-01T12:00:02Z",
        "agent_started_speaking_at": "2025-06-01T12:00:03Z",
    }
    event = parse_event(data)
    assert isinstance(event, TurnCompleted)
    assert event.turn_number == 5
    assert event.user_text == "What is my balance?"
    assert event.agent_text == "Your balance is $42.00."
    assert event.turn_id == "turn-7"
    assert event.agent_first is True
    assert event.agent_tool_id == "tool-99"
    assert event.turn_decision_s == 0.25
    assert event.transcription_delay_s == 0.12
    assert event.llm_ttft_s == 0.3
    assert event.tts_ttfb_s == 0.15
    assert event.realtime_ttft_s == 0.08
    assert event.user_started_speaking_at == "2025-06-01T12:00:00Z"
    assert event.user_stopped_speaking_at == "2025-06-01T12:00:02Z"
    assert event.agent_started_speaking_at == "2025-06-01T12:00:03Z"


def test_parse_turn_metrics_basic():
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


def test_parse_turn_metrics_llm_fields():
    """TurnMetrics includes all 13 LLM fields."""
    data = {
        "type": "turn.metrics",
        "turn_number": 1,
        "llm_ttft_ms": 250,
        "llm_duration_ms": 1200,
        "llm_cancelled": False,
        "llm_prompt_tokens": 500,
        "llm_completion_tokens": 100,
        "llm_total_tokens": 600,
        "llm_tokens_per_second": 83.3,
        "llm_cache_read_tokens": 200,
        "llm_cache_hit_ratio": 0.4,
        "llm_model": "gpt-4o",
        "llm_provider": "openai",
        "llm_label": "primary",
        "llm_request_id": "req-abc123",
        "llm_speech_id": "speech-001",
        "llm_timestamp": 1717200000.0,
    }
    event = parse_event(data)
    assert isinstance(event, TurnMetrics)
    assert event.llm_ttft_ms == 250
    assert event.llm_duration_ms == 1200
    assert event.llm_cancelled is False
    assert event.llm_prompt_tokens == 500
    assert event.llm_completion_tokens == 100
    assert event.llm_total_tokens == 600
    assert event.llm_tokens_per_second == 83.3
    assert event.llm_cache_read_tokens == 200
    assert event.llm_cache_hit_ratio == 0.4
    assert event.llm_model == "gpt-4o"
    assert event.llm_provider == "openai"
    assert event.llm_label == "primary"
    assert event.llm_request_id == "req-abc123"
    assert event.llm_speech_id == "speech-001"
    assert event.llm_timestamp == 1717200000.0


def test_parse_turn_metrics_stt_fields():
    """TurnMetrics includes all 9 STT fields."""
    data = {
        "type": "turn.metrics",
        "turn_number": 1,
        "stt_delay_ms": 120,
        "stt_duration_ms": 2500,
        "stt_audio_duration_ms": 2400,
        "stt_streamed": True,
        "stt_input_tokens": 100,
        "stt_output_tokens": 50,
        "stt_model": "nova-3",
        "stt_provider": "deepgram",
        "stt_confidence": 0.95,
        "stt_label": "primary",
        "stt_request_id": "req-stt-001",
        "stt_timestamp": 1717200001.0,
    }
    event = parse_event(data)
    assert isinstance(event, TurnMetrics)
    assert event.stt_delay_ms == 120
    assert event.stt_duration_ms == 2500
    assert event.stt_audio_duration_ms == 2400
    assert event.stt_streamed is True
    assert event.stt_input_tokens == 100
    assert event.stt_output_tokens == 50
    assert event.stt_model == "nova-3"
    assert event.stt_provider == "deepgram"
    assert event.stt_confidence == 0.95
    assert event.stt_label == "primary"
    assert event.stt_request_id == "req-stt-001"
    assert event.stt_timestamp == 1717200001.0


def test_parse_turn_metrics_tts_fields():
    """TurnMetrics includes all 14 TTS fields (including segment_id, speech_id)."""
    data = {
        "type": "turn.metrics",
        "turn_number": 1,
        "tts_ttfb_ms": 80,
        "tts_duration_ms": 3000,
        "tts_audio_duration_ms": 2800,
        "tts_cancelled": False,
        "tts_characters": 150,
        "tts_streamed": True,
        "tts_input_tokens": 75,
        "tts_output_tokens": 200,
        "tts_model": "eleven_flash_v2_5",
        "tts_provider": "elevenlabs",
        "tts_label": "primary",
        "tts_request_id": "req-tts-001",
        "tts_timestamp": 1717200002.0,
        "tts_speech_id": "speech-002",
        "tts_segment_id": "seg-001",
    }
    event = parse_event(data)
    assert isinstance(event, TurnMetrics)
    assert event.tts_ttfb_ms == 80
    assert event.tts_duration_ms == 3000
    assert event.tts_audio_duration_ms == 2800
    assert event.tts_cancelled is False
    assert event.tts_characters == 150
    assert event.tts_streamed is True
    assert event.tts_input_tokens == 75
    assert event.tts_output_tokens == 200
    assert event.tts_model == "eleven_flash_v2_5"
    assert event.tts_provider == "elevenlabs"
    assert event.tts_label == "primary"
    assert event.tts_request_id == "req-tts-001"
    assert event.tts_timestamp == 1717200002.0
    assert event.tts_speech_id == "speech-002"
    assert event.tts_segment_id == "seg-001"


def test_parse_turn_metrics_vad_fields():
    """TurnMetrics includes all 5 VAD fields."""
    data = {
        "type": "turn.metrics",
        "turn_number": 1,
        "vad_idle_time_s": 2.5,
        "vad_inference_count": 42,
        "vad_inference_duration_total_ms": 168,
        "vad_label": "silero_vad",
    }
    event = parse_event(data)
    assert isinstance(event, TurnMetrics)
    assert event.vad_idle_time_s == 2.5
    assert event.vad_inference_count == 42
    assert event.vad_inference_duration_total_ms == 168
    assert event.vad_label == "silero_vad"


def test_parse_turn_metrics_turn_detection_fields():
    """TurnMetrics includes all 6 turn detection fields (including speech_id)."""
    data = {
        "type": "turn.metrics",
        "turn_number": 1,
        "turn_decision_ms": 250,
        "turn_method": "eou_model",
        "turn_probability": 0.92,
        "turn_unlikely_threshold": 0.3,
        "eou_speech_id": "speech-003",
        "turn_completed_callback_ms": 5,
    }
    event = parse_event(data)
    assert isinstance(event, TurnMetrics)
    assert event.turn_decision_ms == 250
    assert event.turn_method == "eou_model"
    assert event.turn_probability == 0.92
    assert event.turn_unlikely_threshold == 0.3
    assert event.eou_speech_id == "speech-003"
    assert event.turn_completed_callback_ms == 5


def test_parse_turn_metrics_interruption_fields():
    """TurnMetrics includes all 6 interruption fields from bridge."""
    data = {
        "type": "turn.metrics",
        "turn_number": 1,
        "interrupted": True,
        "interruption_total_duration_ms": 1500,
        "interruption_prediction_ms": 80,
        "interruption_detection_delay_ms": 120,
        "num_interruptions": 2,
        "num_backchannels": 1,
        "interruption_num_requests": 3,
    }
    event = parse_event(data)
    assert isinstance(event, TurnMetrics)
    assert event.interrupted is True
    assert event.interruption_total_duration_ms == 1500
    assert event.interruption_prediction_ms == 80
    assert event.interruption_detection_delay_ms == 120
    assert event.num_interruptions == 2
    assert event.num_backchannels == 1
    assert event.interruption_num_requests == 3


def test_parse_turn_metrics_realtime_fields():
    """TurnMetrics includes all 15 RealtimeModelMetrics fields."""
    data = {
        "type": "turn.metrics",
        "turn_number": 1,
        "pipeline": "s2s",
        "realtime_ttft_ms": 120,
        "realtime_duration_ms": 5000,
        "realtime_session_duration_ms": 30000,
        "realtime_cancelled": False,
        "realtime_input_tokens": 500,
        "realtime_output_tokens": 300,
        "realtime_total_tokens": 800,
        "realtime_tokens_per_second": 60.0,
        "realtime_label": "primary",
        "realtime_request_id": "req-rt-001",
        "realtime_model": "gpt-4o-realtime",
        "realtime_provider": "openai",
        # Token detail breakdowns
        "realtime_input_audio_tokens": 200,
        "realtime_input_text_tokens": 250,
        "realtime_input_image_tokens": 50,
        "realtime_output_audio_tokens": 180,
        "realtime_output_text_tokens": 100,
        "realtime_output_image_tokens": 20,
        "realtime_cached_tokens": 100,
        "realtime_cached_audio_tokens": 40,
        "realtime_cached_text_tokens": 50,
        "realtime_cached_image_tokens": 10,
        "realtime_cache_hit_ratio": 0.2,
    }
    event = parse_event(data)
    assert isinstance(event, TurnMetrics)
    assert event.pipeline == "s2s"
    assert event.realtime_ttft_ms == 120
    assert event.realtime_duration_ms == 5000
    assert event.realtime_session_duration_ms == 30000
    assert event.realtime_cancelled is False
    assert event.realtime_input_tokens == 500
    assert event.realtime_output_tokens == 300
    assert event.realtime_total_tokens == 800
    assert event.realtime_tokens_per_second == 60.0
    assert event.realtime_label == "primary"
    assert event.realtime_request_id == "req-rt-001"
    assert event.realtime_model == "gpt-4o-realtime"
    assert event.realtime_provider == "openai"
    assert event.realtime_input_audio_tokens == 200
    assert event.realtime_input_text_tokens == 250
    assert event.realtime_input_image_tokens == 50
    assert event.realtime_output_audio_tokens == 180
    assert event.realtime_output_text_tokens == 100
    assert event.realtime_output_image_tokens == 20
    assert event.realtime_cached_tokens == 100
    assert event.realtime_cached_audio_tokens == 40
    assert event.realtime_cached_text_tokens == 50
    assert event.realtime_cached_image_tokens == 10
    assert event.realtime_cache_hit_ratio == 0.2


def test_parse_turn_metrics_sdk_latency_fields():
    """TurnMetrics includes all 8 ChatMessage.metrics fields."""
    data = {
        "type": "turn.metrics",
        "turn_number": 1,
        "sdk_llm_ttft_ms": 280,
        "sdk_tts_ttfb_ms": 90,
        "sdk_transcription_delay_ms": 110,
        "sdk_end_of_turn_delay_ms": 50,
        "sdk_turn_completed_callback_ms": 3,
        "sdk_started_speaking_at": 1717200000.5,
        "sdk_stopped_speaking_at": 1717200003.2,
        "user_perceived_ms": 850,
    }
    event = parse_event(data)
    assert isinstance(event, TurnMetrics)
    assert event.sdk_llm_ttft_ms == 280
    assert event.sdk_tts_ttfb_ms == 90
    assert event.sdk_transcription_delay_ms == 110
    assert event.sdk_end_of_turn_delay_ms == 50
    assert event.sdk_turn_completed_callback_ms == 3
    assert event.sdk_started_speaking_at == 1717200000.5
    assert event.sdk_stopped_speaking_at == 1717200003.2
    assert event.user_perceived_ms == 850


def test_parse_turn_metrics_context_fields():
    """TurnMetrics includes agent_first, agent_tool_id, user/agent_text, pipeline."""
    data = {
        "type": "turn.metrics",
        "turn_number": 2,
        "agent_first": True,
        "agent_tool_id": "tool-42",
        "user_text": "Check my order",
        "agent_text": "Let me look that up.",
        "pipeline": "stt_llm_tts",
    }
    event = parse_event(data)
    assert isinstance(event, TurnMetrics)
    assert event.agent_first is True
    assert event.agent_tool_id == "tool-42"
    assert event.user_text == "Check my order"
    assert event.agent_text == "Let me look that up."
    assert event.pipeline == "stt_llm_tts"


def test_parse_turn_metrics_endpointing_and_other_fields():
    """TurnMetrics includes endpointing EMA, speaking_rate, error_source."""
    data = {
        "type": "turn.metrics",
        "turn_number": 1,
        "endpointing_min_delay_ms": 150,
        "endpointing_max_delay_ms": 800,
        "speaking_rate": 3.2,
        "error_source": "tts",
        "llm_availability": {"openai": True, "anthropic": False},
    }
    event = parse_event(data)
    assert isinstance(event, TurnMetrics)
    assert event.endpointing_min_delay_ms == 150
    assert event.endpointing_max_delay_ms == 800
    assert event.speaking_rate == 3.2
    assert event.error_source == "tts"
    assert event.llm_availability == {"openai": True, "anthropic": False}


def test_parse_vad_speech_started():
    """user.speech_started includes VAD metric fields."""
    data = {
        "type": "user.speech_started",
        "timestamp_ms": 5000,
        "timestamp": "2025-06-01T12:00:05Z",
        "vad_idle_time_s": 2.3,
        "vad_inference_count": 15,
        "vad_inference_duration_total_ms": 60,
    }
    event = parse_event(data)
    assert isinstance(event, VadSpeechStarted)
    assert event.timestamp_ms == 5000
    assert event.timestamp == "2025-06-01T12:00:05Z"
    assert event.vad_idle_time_s == 2.3
    assert event.vad_inference_count == 15
    assert event.vad_inference_duration_total_ms == 60


def test_parse_vad_speech_stopped():
    """user.speech_stopped includes VAD metric fields."""
    data = {
        "type": "user.speech_stopped",
        "timestamp_ms": 7000,
        "duration_ms": 2000,
        "timestamp": "2025-06-01T12:00:07Z",
        "vad_idle_time_s": 0.0,
        "vad_inference_count": 25,
        "vad_inference_duration_total_ms": 100,
    }
    event = parse_event(data)
    assert isinstance(event, VadSpeechStopped)
    assert event.timestamp_ms == 7000
    assert event.duration_ms == 2000
    assert event.timestamp == "2025-06-01T12:00:07Z"
    assert event.vad_idle_time_s == 0.0
    assert event.vad_inference_count == 25
    assert event.vad_inference_duration_total_ms == 100


def test_parse_user_backchannel():
    """user.backchannel is parsed into UserBackchannel with all fields."""
    data = {
        "type": "user.backchannel",
        "is_interruption": False,
        "probability": 0.15,
        "detection_delay_ms": 120.5,
        "total_duration_ms": 350.0,
        "prediction_duration_ms": 45.2,
        "overlap_started_at": "2025-06-01T12:00:10Z",
        "num_requests": 2,
        "timestamp": "2025-06-01T12:00:10.5Z",
        "speech_input_b64": "AQID",
        "probabilities": [0.1, 0.15, 0.12],
    }
    event = parse_event(data)
    assert isinstance(event, UserBackchannel)
    assert event.is_interruption is False
    assert event.probability == 0.15
    assert event.detection_delay_ms == 120.5
    assert event.total_duration_ms == 350.0
    assert event.prediction_duration_ms == 45.2
    assert event.overlap_started_at == "2025-06-01T12:00:10Z"
    assert event.num_requests == 2
    assert event.timestamp == "2025-06-01T12:00:10.5Z"
    assert event.speech_input_b64 == "AQID"
    assert event.probabilities == [0.1, 0.15, 0.12]


def test_parse_session_usage():
    """session.usage is parsed into SessionUsage with per-model breakdowns."""
    data = {
        "type": "session.usage",
        "models": [
            {
                "type": "llm_usage",
                "provider": "openai",
                "model": "gpt-4o",
                "input_tokens": 1500,
                "input_cached_tokens": 200,
                "output_tokens": 300,
                "session_duration": 45.0,
            },
            {
                "type": "tts_usage",
                "provider": "elevenlabs",
                "model": "eleven_flash_v2_5",
                "characters_count": 500,
                "audio_duration": 12.5,
            },
            {
                "type": "stt_usage",
                "provider": "deepgram",
                "model": "nova-3",
                "audio_duration": 30.0,
            },
            {
                "type": "interruption_usage",
                "provider": "plivo",
                "total_requests": 5,
            },
        ],
    }
    event = parse_event(data)
    assert isinstance(event, SessionUsage)
    assert len(event.models) == 4
    assert event.models[0]["type"] == "llm_usage"
    assert event.models[0]["input_tokens"] == 1500
    assert event.models[0]["input_cached_tokens"] == 200
    assert event.models[1]["type"] == "tts_usage"
    assert event.models[1]["characters_count"] == 500
    assert event.models[2]["type"] == "stt_usage"
    assert event.models[2]["audio_duration"] == 30.0
    assert event.models[3]["type"] == "interruption_usage"
    assert event.models[3]["total_requests"] == 5


def test_parse_tool_executed_with_calls():
    """tool.executed includes calls list with tool results."""
    data = {
        "type": "tool.executed",
        "timestamp": "2025-06-01T12:00:00Z",
        "calls": [
            {
                "name": "lookup_order",
                "call_id": "tc-1",
                "arguments": '{"order_id": "ORD-100"}',
                "output": '{"status": "shipped"}',
                "is_error": False,
            },
            {
                "name": "get_tracking",
                "call_id": "tc-2",
                "arguments": '{"tracking_id": "1Z999"}',
                "output": "Tracking service unavailable",
                "is_error": True,
            },
        ],
    }
    event = parse_event(data)
    assert isinstance(event, ToolExecuted)
    assert event.timestamp == "2025-06-01T12:00:00Z"
    assert len(event.calls) == 2
    assert event.calls[0]["name"] == "lookup_order"
    assert event.calls[0]["call_id"] == "tc-1"
    assert event.calls[0]["is_error"] is False
    assert event.calls[1]["is_error"] is True


def test_parse_llm_availability_changed():
    """llm.availability_changed includes llm identifier."""
    data = {
        "type": "llm.availability_changed",
        "llm": "openai/gpt-4o",
        "available": False,
        "timestamp": "2025-06-01T12:00:00Z",
    }
    event = parse_event(data)
    assert isinstance(event, LlmAvailabilityChanged)
    assert event.llm == "openai/gpt-4o"
    assert event.available is False
    assert event.timestamp == "2025-06-01T12:00:00Z"


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

    The registry maps "dtmf" to StreamDtmf (audio stream protocol).
    Managed-mode DTMF uses "user.dtmf" and maps to the Dtmf class.
    """
    data = {
        "event": "dtmf",
        "dtmf": {
            "digit": "5",
        },
    }
    event = parse_event(data)
    # Registry maps "dtmf" -> StreamDtmf (audio stream protocol)
    assert isinstance(event, StreamDtmf)
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
        "type": "tool.called",
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


def test_parse_dtmf_sent():
    """dtmf.sent is parsed into DtmfSent with digits."""
    data = {
        "type": "dtmf.sent",
        "digits": "123#",
    }
    event = parse_event(data)
    assert isinstance(event, DtmfSent)
    assert event.digits == "123#"


def test_parse_agent_tool_completed():
    """agent_tool.completed is parsed into AgentToolCompleted with result dict."""
    data = {
        "type": "agent_tool.completed",
        "agent_tool_type": "collect_email",
        "agent_tool_id": "tool-99",
        "result": {"email": "user@example.com"},
    }
    event = parse_event(data)
    assert isinstance(event, AgentToolCompleted)
    assert event.agent_tool_type == "collect_email"
    assert event.agent_tool_id == "tool-99"
    assert event.result == {"email": "user@example.com"}


def test_parse_agent_speech_created():
    """agent.speech_created is parsed into AgentSpeechCreated."""
    data = {
        "type": "agent.speech_created",
        "source": "llm",
        "user_initiated": True,
        "timestamp": "2025-06-01T12:00:00Z",
    }
    event = parse_event(data)
    assert isinstance(event, AgentSpeechCreated)
    assert event.source == "llm"
    assert event.user_initiated is True
    assert event.timestamp == "2025-06-01T12:00:00Z"


def test_parse_prompt_with_language_and_speaker():
    """user.transcription includes language and speaker_id from bridge."""
    data = {
        "type": "user.transcription",
        "text": "Hello there",
        "is_final": True,
        "language": "en",
        "speaker_id": "spk-001",
    }
    event = parse_event(data)
    assert isinstance(event, Prompt)
    assert event.text == "Hello there"
    assert event.is_final is True
    assert event.language == "en"
    assert event.speaker_id == "spk-001"


def test_parse_interruption_with_playback():
    """agent.speech_interrupted includes playback_position_s and timestamp."""
    data = {
        "type": "agent.speech_interrupted",
        "interrupted_text": "I was saying...",
        "playback_position_s": 2.5,
        "timestamp": "2025-06-01T12:00:00Z",
    }
    event = parse_event(data)
    assert isinstance(event, Interruption)
    assert event.interrupted_text == "I was saying..."
    assert event.playback_position_s == 2.5
    assert event.timestamp == "2025-06-01T12:00:00Z"


def test_parse_session_ended_with_reason():
    """session.ended includes reason, started_at, ended_at, error from bridge."""
    data = {
        "type": "session.ended",
        "duration_seconds": 120,
        "turn_count": 5,
        "reason": "agent_hangup",
        "started_at": "2025-06-01T12:00:00Z",
        "ended_at": "2025-06-01T12:02:00Z",
        "error": "tts: connection failed",
    }
    event = parse_event(data)
    assert isinstance(event, AgentSessionEnded)
    assert event.duration_seconds == 120
    assert event.turn_count == 5
    assert event.reason == "agent_hangup"
    assert event.started_at == "2025-06-01T12:00:00Z"
    assert event.ended_at == "2025-06-01T12:02:00Z"
    assert event.error == "tts: connection failed"


def test_parse_turn_detected_with_method():
    """user.turn_completed includes timestamp, turn_method, turn_probability."""
    data = {
        "type": "user.turn_completed",
        "duration_ms": 1500,
        "timestamp": "2025-06-01T12:00:05Z",
        "turn_method": "eou_model",
        "turn_probability": 0.92,
    }
    event = parse_event(data)
    assert isinstance(event, TurnDetected)
    assert event.duration_ms == 1500
    assert event.timestamp == "2025-06-01T12:00:05Z"
    assert event.turn_method == "eou_model"
    assert event.turn_probability == 0.92


def test_parse_speech_completed_with_transcript():
    """agent.speech_completed includes transcript from bridge."""
    data = {
        "type": "agent.speech_completed",
        "playback_position_s": 3.5,
        "timestamp": "2025-06-01T12:00:10Z",
        "transcript": "Hello, how can I help you today?",
    }
    event = parse_event(data)
    assert isinstance(event, AgentSpeechCompleted)
    assert event.playback_position_s == 3.5
    assert event.transcript == "Hello, how can I help you today?"


def test_parse_false_interruption_with_resumed():
    """agent.false_interruption includes resumed flag from bridge."""
    data = {
        "type": "agent.false_interruption",
        "resumed": True,
        "timestamp": "2025-06-01T12:00:15Z",
    }
    event = parse_event(data)
    assert isinstance(event, AgentFalseInterruption)
    assert event.resumed is True
    assert event.timestamp == "2025-06-01T12:00:15Z"


def test_all_event_types_in_registry():
    """Registry contains all expected event types (managed + audio stream + new)."""
    # Managed-mode events
    managed_types = {
        "session.started",
        "tool.called",
        "turn.completed",
        "user.transcription",
        "user.dtmf",
        "dtmf.sent",
        "agent.speech_interrupted",
        "session.ended",
        "session.error",
        "user.speech_started",
        "user.speech_stopped",
        "user.turn_completed",
        "user.state_changed",
        "agent.state_changed",
        "agent.speech_started",
        "agent.speech_completed",
        "agent.speech_created",
        "agent.false_interruption",
        "tool.executed",
        "llm.availability_changed",
        "voicemail.detected",
        "voicemail.beep",
        "participant.added",
        "participant.removed",
        "call.transferred",
        "play.completed",
        "agent_tool.started",
        "agent_tool.completed",
        "agent_tool.failed",
        "user.idle",
        "user.backchannel",
        "session.usage",
        "turn.metrics",
        "agent.handoff",
    }
    # Audio stream events
    stream_types = {
        "start",
        "media",
        "dtmf",
        "playedStream",
        "clearedAudio",
        "stop",
    }
    expected = managed_types | stream_types
    assert set(_EVENT_REGISTRY.keys()) == expected
    assert len(_EVENT_REGISTRY) == 40
