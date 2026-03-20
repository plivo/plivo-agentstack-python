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

    type: str = "session.started"
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

    type: str = "tool.called"
    id: str = ""
    name: str = ""
    arguments: dict = field(default_factory=dict)


@dataclass
class TurnCompleted:
    """Conversational turn finished -- transcript snapshot with latency highlights."""

    type: str = "turn.completed"
    turn_number: int = 0
    user_text: str = ""
    agent_text: str = ""
    turn_id: str = ""
    agent_first: bool = False
    agent_tool_id: str | None = None
    # Key latency (seconds)
    turn_decision_s: float | None = None
    transcription_delay_s: float | None = None
    llm_ttft_s: float | None = None
    tts_ttfb_s: float | None = None
    realtime_ttft_s: float | None = None
    # Timestamps (ISO 8601)
    user_started_speaking_at: str | None = None
    user_stopped_speaking_at: str | None = None
    agent_started_speaking_at: str | None = None


@dataclass
class Prompt:
    """User speech transcript (BYOLLM/STT-only modes).

    Sent progressively with is_final=False, finalized with is_final=True.
    """

    type: str = "user.transcription"
    text: str = ""
    is_final: bool = False
    language: str | None = None
    speaker_id: str | None = None


@dataclass
class Dtmf:
    """DTMF digit detected (caller pressed a key)."""

    type: str = "user.dtmf"
    digit: str = ""


@dataclass
class DtmfSent:
    """DTMF digits were sent on the call (confirmation)."""

    type: str = "dtmf.sent"
    digits: str = ""


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

    type: str = "agent.speech_interrupted"
    interrupted_text: str | None = None
    turn_id: str | None = None
    playback_position_s: float | None = None
    timestamp: str | None = None


@dataclass
class AgentSessionEnded:
    """Session ended -- includes performance metrics."""

    type: str = "session.ended"
    duration_seconds: int = 0
    turn_count: int | None = None
    reason: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    error: str | None = None
    transcript: Any = None
    stt_duration: int | None = None
    llm_duration: int | None = None
    tts_duration: int | None = None


@dataclass
class Error:
    """An error occurred in the pipeline."""

    type: str = "session.error"
    code: str = ""
    message: str = ""


@dataclass
class VadSpeechStarted:
    """VAD detected speech onset (opt-in: events.vad_events=true)."""

    type: str = "user.speech_started"
    timestamp_ms: int = 0
    timestamp: str | None = None
    vad_idle_time_s: float | None = None
    vad_inference_count: int | None = None
    vad_inference_duration_total_ms: int | None = None


@dataclass
class VadSpeechStopped:
    """VAD detected speech offset (opt-in: events.vad_events=true)."""

    type: str = "user.speech_stopped"
    timestamp_ms: int = 0
    duration_ms: int = 0
    timestamp: str | None = None
    vad_idle_time_s: float | None = None
    vad_inference_count: int | None = None
    vad_inference_duration_total_ms: int | None = None


@dataclass
class TurnDetected:
    """Semantic turn end detected (opt-in: events.turn_events=true).

    trigger is one of: "silence", "max_duration", "text".
    turn_method: "eou_model", "silence", etc.
    turn_probability: model confidence (0.0-1.0) for eou_model method.
    """

    type: str = "user.turn_completed"
    turn_id: str = ""
    trigger: str = ""
    duration_ms: int = 0
    timestamp: str | None = None
    turn_method: str | None = None
    turn_probability: float | None = None


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


# ---------------------------------------------------------------------------
# Agent tool events -- server-side sub-agent lifecycle
# ---------------------------------------------------------------------------


@dataclass
class AgentToolStarted:
    """Agent tool sub-agent started -- parent agent suspended.

    The server is running a multi-turn sub-agent (e.g., collecting email).
    Normal turn events continue to flow, annotated with agent_tool_id.
    """

    type: str = "agent_tool.started"
    agent_tool_type: str = ""
    agent_tool_id: str = ""


@dataclass
class AgentToolCompleted:
    """Agent tool sub-agent completed -- parent agent resumed.

    result contains the collected data (varies by agent_tool_type).
    May include timed_out=True if the sub-agent exceeded its timeout.
    """

    type: str = "agent_tool.completed"
    agent_tool_type: str = ""
    agent_tool_id: str = ""
    result: dict = field(default_factory=dict)


@dataclass
class AgentToolFailed:
    """Agent tool sub-agent failed -- parent agent resumed with error."""

    type: str = "agent_tool.failed"
    agent_tool_type: str = ""
    agent_tool_id: str = ""
    error: str = ""


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
    """Per-turn latency and usage metrics -- comprehensive pipeline observability.

    Emitted after each conversational turn with timing breakdown and provider stats.
    All *_ms fields are milliseconds. All timestamps are ISO 8601 / RFC 3339.
    """

    type: str = "turn.metrics"
    turn_number: int = 0
    interrupted: bool = False
    agent_first: bool | None = None
    agent_tool_id: str | None = None
    user_text: str | None = None
    agent_text: str | None = None
    pipeline: str | None = None                # "s2s" when using realtime model

    # --- Latency (primary: SDK-measured from ChatMessage.metrics) ---
    user_perceived_ms: int | None = None       # SDK e2e_latency or wall-clock fallback
    sdk_llm_ttft_ms: int | None = None
    sdk_tts_ttfb_ms: int | None = None
    sdk_transcription_delay_ms: int | None = None
    sdk_end_of_turn_delay_ms: int | None = None
    sdk_turn_completed_callback_ms: int | None = None
    sdk_started_speaking_at: float | None = None
    sdk_stopped_speaking_at: float | None = None

    # --- Turn detection ---
    stt_delay_ms: int | None = None
    turn_decision_ms: int | None = None
    turn_completed_callback_ms: int | None = None
    eou_speech_id: str | None = None
    turn_method: str | None = None
    turn_probability: float | None = None
    turn_unlikely_threshold: float | None = None

    # --- Dynamic endpointing EMA state ---
    endpointing_min_delay_ms: int | None = None
    endpointing_max_delay_ms: int | None = None

    # --- VAD ---
    vad_idle_time_s: float | None = None
    vad_inference_count: int | None = None
    vad_inference_duration_total_ms: int | None = None
    vad_label: str | None = None

    # --- LLM ---
    llm_ttft_ms: int | None = None
    llm_duration_ms: int | None = None
    llm_cancelled: bool | None = None
    llm_prompt_tokens: int | None = None
    llm_completion_tokens: int | None = None
    llm_total_tokens: int | None = None
    llm_tokens_per_second: float | None = None
    llm_cache_read_tokens: int | None = None
    llm_cache_hit_ratio: float | None = None
    llm_model: str | None = None
    llm_provider: str | None = None
    llm_label: str | None = None
    llm_request_id: str | None = None
    llm_timestamp: float | None = None
    llm_speech_id: str | None = None

    # --- TTS ---
    tts_ttfb_ms: int | None = None
    tts_duration_ms: int | None = None
    tts_audio_duration_ms: int | None = None
    tts_cancelled: bool | None = None
    tts_characters: int | None = None
    tts_streamed: bool | None = None
    tts_input_tokens: int | None = None
    tts_output_tokens: int | None = None
    tts_model: str | None = None
    tts_provider: str | None = None
    tts_label: str | None = None
    tts_request_id: str | None = None
    tts_timestamp: float | None = None
    tts_speech_id: str | None = None
    tts_segment_id: str | None = None

    # --- STT ---
    stt_duration_ms: int | None = None
    stt_audio_duration_ms: int | None = None
    stt_streamed: bool | None = None
    stt_input_tokens: int | None = None
    stt_output_tokens: int | None = None
    stt_model: str | None = None
    stt_provider: str | None = None
    stt_confidence: float | None = None
    stt_label: str | None = None
    stt_request_id: str | None = None
    stt_timestamp: float | None = None

    # --- Adaptive interruption ---
    interruption_total_duration_ms: int | None = None
    interruption_prediction_ms: int | None = None
    interruption_detection_delay_ms: int | None = None
    num_interruptions: int | None = None
    num_backchannels: int | None = None
    interruption_num_requests: int | None = None

    # --- S2S / Realtime model ---
    realtime_ttft_ms: int | None = None
    realtime_duration_ms: int | None = None
    realtime_session_duration_ms: int | None = None
    realtime_cancelled: bool | None = None
    realtime_input_tokens: int | None = None
    realtime_output_tokens: int | None = None
    realtime_total_tokens: int | None = None
    realtime_tokens_per_second: float | None = None
    realtime_label: str | None = None
    realtime_request_id: str | None = None
    realtime_model: str | None = None
    realtime_provider: str | None = None
    # S2S token breakdowns
    realtime_input_audio_tokens: int | None = None
    realtime_input_text_tokens: int | None = None
    realtime_input_image_tokens: int | None = None
    realtime_output_audio_tokens: int | None = None
    realtime_output_text_tokens: int | None = None
    realtime_output_image_tokens: int | None = None
    realtime_cached_tokens: int | None = None
    realtime_cached_audio_tokens: int | None = None
    realtime_cached_text_tokens: int | None = None
    realtime_cached_image_tokens: int | None = None
    realtime_cache_hit_ratio: float | None = None

    # --- Wall-clock timestamps (ISO 8601) ---
    user_started_speaking_at: str | None = None
    user_stopped_speaking_at: str | None = None
    agent_started_speaking_at: str | None = None
    agent_stopped_speaking_at: str | None = None

    # --- Other ---
    speaking_rate: float | None = None
    error_source: str | None = None
    llm_availability: dict | None = None


# ---------------------------------------------------------------------------
# State change & lifecycle events
# ---------------------------------------------------------------------------


@dataclass
class UserStateChanged:
    """User state transition (e.g. speaking -> listening -> away)."""

    type: str = "user.state_changed"
    old_state: str | None = None
    new_state: str | None = None
    timestamp: str | None = None


@dataclass
class AgentStateChanged:
    """Agent state transition (e.g. idle -> listening -> thinking -> speaking)."""

    type: str = "agent.state_changed"
    old_state: str | None = None
    new_state: str | None = None
    timestamp: str | None = None


@dataclass
class AgentSpeechStarted:
    """Agent started speaking -- TTS audio is playing."""

    type: str = "agent.speech_started"
    timestamp: str | None = None


@dataclass
class AgentSpeechCompleted:
    """Agent finished speaking -- TTS playback done."""

    type: str = "agent.speech_completed"
    playback_position_s: float | None = None
    timestamp: str | None = None
    transcript: str | None = None


@dataclass
class AgentSpeechCreated:
    """LLM started generating a response -- speech turn created."""

    type: str = "agent.speech_created"
    source: str | None = None
    user_initiated: bool | None = None
    timestamp: str | None = None


@dataclass
class AgentFalseInterruption:
    """False interruption detected -- agent speech resumed."""

    type: str = "agent.false_interruption"
    resumed: bool | None = None
    timestamp: str | None = None


@dataclass
class ToolExecuted:
    """Server-side tool execution completed (e.g. MCP tools).

    calls: list of dicts, each with name, call_id, arguments, output, is_error.
    """

    type: str = "tool.executed"
    calls: list = field(default_factory=list)
    timestamp: str | None = None


@dataclass
class LlmAvailabilityChanged:
    """LLM became available or unavailable."""

    type: str = "llm.availability_changed"
    llm: str | None = None
    available: bool | None = None
    timestamp: str | None = None


@dataclass
class UserBackchannel:
    """Overlapping speech detected -- backchannel or real interruption.

    Emitted when user speech overlaps with agent speech. The is_interruption
    flag indicates whether the ML model classified this as a genuine interruption
    (True) or a backchannel/noise (False). Only emitted when interruption_mode="adaptive".
    """

    type: str = "user.backchannel"
    is_interruption: bool = False
    probability: float | None = None           # ML model confidence (0.0-1.0)
    detection_delay_ms: float | None = None    # time to classify the overlap
    total_duration_ms: float | None = None     # total overlap duration
    prediction_duration_ms: float | None = None  # ML inference time
    overlap_started_at: str | None = None      # when overlap began (ISO 8601)
    num_requests: int | None = None            # cloud inference requests
    timestamp: str | None = None
    # Raw ML data (base64-encoded audio, probability array)
    speech_input_b64: str | None = None        # raw overlapping audio (base64 int16)
    probabilities: list | None = None          # per-frame ML probabilities


@dataclass
class SessionUsage:
    """Cumulative session usage updated.

    Emitted periodically with per-model token/character/audio usage breakdowns.
    Each entry in models has type, provider, model, and type-specific fields:
    - llm_usage: input_tokens, input_cached_tokens, output_tokens, session_duration
    - tts_usage: characters_count, audio_duration_s, input/output_tokens
    - stt_usage: audio_duration_s, input/output_tokens
    - interruption_usage: total_requests
    """

    type: str = "session.usage"
    models: list | None = None                 # list of per-model usage dicts


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
    "session.started": AgentSessionStarted,
    "tool.called": ToolCall,
    "turn.completed": TurnCompleted,
    "user.transcription": Prompt,
    "user.dtmf": Dtmf,
    "dtmf": StreamDtmf,
    "dtmf.sent": DtmfSent,
    "agent.handoff": AgentHandoff,
    "agent.speech_interrupted": Interruption,
    "session.ended": AgentSessionEnded,
    "session.error": Error,
    "user.speech_started": VadSpeechStarted,
    "user.speech_stopped": VadSpeechStopped,
    "user.turn_completed": TurnDetected,
    "user.state_changed": UserStateChanged,
    "agent.state_changed": AgentStateChanged,
    "agent.speech_started": AgentSpeechStarted,
    "agent.speech_completed": AgentSpeechCompleted,
    "agent.speech_created": AgentSpeechCreated,
    "agent.false_interruption": AgentFalseInterruption,
    "tool.executed": ToolExecuted,
    "llm.availability_changed": LlmAvailabilityChanged,
    "voicemail.detected": VoicemailDetected,
    "voicemail.beep": VoicemailBeep,
    "participant.added": ParticipantAdded,
    "participant.removed": ParticipantRemoved,
    "call.transferred": CallTransferred,
    "play.completed": PlayCompleted,
    "agent_tool.started": AgentToolStarted,
    "agent_tool.completed": AgentToolCompleted,
    "agent_tool.failed": AgentToolFailed,
    "user.idle": UserIdle,
    "user.backchannel": UserBackchannel,
    "session.usage": SessionUsage,
    "turn.metrics": TurnMetrics,
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
