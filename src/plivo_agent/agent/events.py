"""Typed event models for Agent Stack WebSocket events.

Server-to-client events are parsed into dataclass instances for type safety
and IDE autocomplete.  Unknown event types fall through as raw dicts so the
SDK is forward-compatible with new server versions.

Audio-stream events (Plivo Audio Streaming protocol) are also included for
low-level media handling.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Typed event models -- server -> client
# ---------------------------------------------------------------------------


@dataclass
class AgentSessionStarted:
    """Session started -- first event on every connection."""

    type: str = "agent_session.started"
    agent_session_id: str = ""
    call_id: str = ""
    caller: str | None = None
    callee: str | None = None
    agent_id: str | None = None
    audio_format: str | None = None
    sample_rate: int | None = None
    channels: int | None = None
    frame_size_ms: int | None = None
    plc_enabled: bool | None = None


@dataclass
class ToolCall:
    """LLM invoked a customer-defined tool."""

    type: str = "tool_call"
    id: str = ""
    name: str = ""
    arguments: dict = field(default_factory=dict)


@dataclass
class TurnCompleted:
    """Conversational turn finished -- transcript snapshot."""

    type: str = "turn.completed"
    user_text: str = ""
    agent_text: str = ""
    turn_id: str = ""


@dataclass
class Prompt:
    """User speech transcript (BYOLLM/STT-only modes).

    Sent progressively with is_final=False, finalized with is_final=True.
    """

    type: str = "prompt"
    text: str = ""
    is_final: bool = False


@dataclass
class Dtmf:
    """DTMF digit detected (caller pressed a key)."""

    type: str = "dtmf"
    digit: str = ""


@dataclass
class AgentHandoff:
    """Agent handoff detected -- session.update changed agent persona.

    Emitted when a session.update changes system_prompt alongside tools
    or llm config (i.e., an agent handoff pattern).
    """

    type: str = "agent.handoff"
    new_agent: str | None = None


@dataclass
class Interruption:
    """User interrupted the agent (barge-in).

    interrupted_text is the partial TTS output that was cut off.
    None in text/BYOLLM mode.
    """

    type: str = "interruption"
    interrupted_text: str | None = None
    turn_id: str | None = None


@dataclass
class AgentSessionEnded:
    """Session ended -- includes performance metrics."""

    type: str = "agent_session.ended"
    duration_seconds: int = 0
    turn_count: int | None = None
    transcript: Any = None
    stt_duration: int | None = None
    llm_duration: int | None = None
    tts_duration: int | None = None


@dataclass
class Error:
    """An error occurred in the pipeline."""

    type: str = "error"
    code: str = ""
    message: str = ""


@dataclass
class VadSpeechStarted:
    """VAD detected speech onset (opt-in: events.vad_events=true)."""

    type: str = "vad.speech_started"
    timestamp_ms: int = 0


@dataclass
class VadSpeechStopped:
    """VAD detected speech offset (opt-in: events.vad_events=true)."""

    type: str = "vad.speech_stopped"
    timestamp_ms: int = 0
    duration_ms: int = 0


@dataclass
class TurnDetected:
    """Semantic turn end detected (opt-in: events.turn_events=true).

    trigger is one of: "silence", "max_duration", "smart_turn".
    """

    type: str = "turn.detected"
    turn_id: str = ""
    trigger: str = ""
    duration_ms: int = 0


@dataclass
class VoicemailDetected:
    """Voicemail/AMD detection result.

    result: "machine" or "human"
    method: "audio" (energy analysis) or "llm" (transcript classification)
    """

    type: str = "voicemail.detected"
    result: str = ""
    method: str = ""
    transcript: str | None = None


@dataclass
class VoicemailBeep:
    """Beep detected -- voicemail greeting done, recording started."""

    type: str = "voicemail.beep"
    frequency_hz: float = 0.0
    duration_ms: int = 0


@dataclass
class ParticipantAdded:
    """Multi-party: participant joined the call."""

    type: str = "participant.added"
    member_id: str = ""
    role: str = ""
    target: str = ""


@dataclass
class ParticipantRemoved:
    """Multi-party: participant left the call."""

    type: str = "participant.removed"
    member_id: str = ""
    role: str = ""


@dataclass
class CallTransferred:
    """Call was transferred (dual mode)."""

    type: str = "call.transferred"
    destination: list[str] = field(default_factory=list)


@dataclass
class PlayCompleted:
    """Audio playback from agent_session.play completed."""

    type: str = "play.completed"


@dataclass
class UserIdle:
    """User has been idle (silent) after agent finished speaking.

    Emitted on each reminder attempt and on final hangup.
    retry_count: how many reminders have been sent so far.
    reason: "no_response" (reminder sent) or "max_retries_exhausted" (hanging up).
    """

    type: str = "user.idle"
    retry_count: int = 0
    reason: str = ""


@dataclass
class TurnMetrics:
    """Per-turn latency and usage metrics (opt-in: events.metrics_events=true).

    Emitted after each conversational turn with timing breakdown and provider stats.
    All *_ms fields are milliseconds. All timestamps are ISO 8601 / RFC 3339.
    """

    type: str = "turn.metrics"
    turn_number: int = 0
    interrupted: bool = False
    # Latency chain (Rust-measured, end-to-end)
    user_perceived_ms: int | None = None
    stt_delay_ms: int | None = None
    turn_decision_ms: int | None = None
    llm_ttft_ms: int | None = None
    tts_pipeline_ms: int | None = None
    tts_gate_wait_ms: int | None = None
    # Turn detection
    turn_method: str | None = None
    turn_probability: float | None = None
    fallback_silence_ms: int | None = None
    # LLM usage
    llm_prompt_tokens: int | None = None
    llm_completion_tokens: int | None = None
    llm_total_tokens: int | None = None
    llm_cache_read_tokens: int | None = None
    llm_model: str | None = None
    context_msg_count: int | None = None
    # TTS usage
    tts_ttfb_ms: int | None = None
    tts_characters: int | None = None
    tts_audio_duration_ms: int | None = None
    # Interruption
    interruption_reason: str | None = None
    pause_duration_ms: int | None = None
    # Provider info
    stt_provider: str | None = None
    llm_provider: str | None = None
    tts_provider: str | None = None
    # Wall-clock timestamps (ISO 8601)
    user_started_speaking_at: str | None = None
    user_stopped_speaking_at: str | None = None
    agent_started_speaking_at: str | None = None
    agent_stopped_speaking_at: str | None = None
    # STT confidence
    stt_confidence: float | None = None
    on_user_turn_completed_ms: int | None = None


# ---------------------------------------------------------------------------
# Typed event models -- audio stream (Plivo Audio Streaming protocol)
# ---------------------------------------------------------------------------


@dataclass
class StreamStart:
    """Plivo audio stream started -- contains stream metadata."""

    event: str = "start"
    stream_id: str = ""
    call_id: str = ""
    content_type: str = ""
    sample_rate: int = 8000


@dataclass
class StreamMedia:
    """Audio data from the caller (base64-encoded)."""

    event: str = "media"
    payload: str = ""
    content_type: str = ""
    sample_rate: int = 8000
    timestamp: str = ""


@dataclass
class StreamDtmf:
    """DTMF digit from Plivo audio stream."""

    event: str = "dtmf"
    digit: str = ""


@dataclass
class PlayedStream:
    """Plivo finished playing audio up to a checkpoint."""

    event: str = "playedStream"
    name: str = ""


@dataclass
class ClearedAudio:
    """Plivo cleared all queued audio."""

    event: str = "clearedAudio"


@dataclass
class StreamStop:
    """Plivo audio stream ended."""

    event: str = "stop"


# ---------------------------------------------------------------------------
# Event parsing
# ---------------------------------------------------------------------------

_EVENT_REGISTRY: dict[str, type] = {
    "agent_session.started": AgentSessionStarted,
    "tool_call": ToolCall,
    "turn.completed": TurnCompleted,
    "prompt": Prompt,
    "dtmf": Dtmf,
    "interruption": Interruption,
    "agent_session.ended": AgentSessionEnded,
    "error": Error,
    "vad.speech_started": VadSpeechStarted,
    "vad.speech_stopped": VadSpeechStopped,
    "turn.detected": TurnDetected,
    "voicemail.detected": VoicemailDetected,
    "voicemail.beep": VoicemailBeep,
    "participant.added": ParticipantAdded,
    "participant.removed": ParticipantRemoved,
    "call.transferred": CallTransferred,
    "play.completed": PlayCompleted,
    "user.idle": UserIdle,
    "turn.metrics": TurnMetrics,
    "agent.handoff": AgentHandoff,
    "start": StreamStart,
    "media": StreamMedia,
    "playedStream": PlayedStream,
    "clearedAudio": ClearedAudio,
    "stop": StreamStop,
}


def parse_event(data: dict) -> Any:
    """Parse a raw JSON dict into a typed event dataclass.

    Returns the raw dict for unknown event types (forward-compatible).
    """
    event_type = data.get("type") or data.get("event")
    cls = _EVENT_REGISTRY.get(event_type) if event_type else None

    if cls is None:
        return data

    field_names = {f.name for f in dataclasses.fields(cls)}
    kwargs = {k: v for k, v in data.items() if k in field_names}

    # Handle nested Plivo audio stream events
    if event_type == "start" and "start" in data:
        start_data = data["start"]
        kwargs.setdefault("stream_id", data.get("streamId") or start_data.get("streamId", ""))
        kwargs.setdefault("call_id", start_data.get("callId", ""))
        kwargs.setdefault("content_type", start_data.get("mediaFormat", {}).get("type", ""))
        kwargs.setdefault("sample_rate", start_data.get("mediaFormat", {}).get("rate", 8000))
    elif event_type == "media" and "media" in data:
        media_data = data["media"]
        kwargs.setdefault("payload", media_data.get("payload", ""))
        kwargs.setdefault("content_type", media_data.get("contentType", ""))
        kwargs.setdefault("sample_rate", media_data.get("sampleRate", 8000))
        kwargs.setdefault("timestamp", media_data.get("timestamp", ""))
    elif event_type == "dtmf" and "dtmf" in data:
        # Audio stream mode nests digit under {"dtmf": {"digit": "1"}}
        kwargs.setdefault("digit", data["dtmf"].get("digit", ""))

    return cls(**kwargs)
