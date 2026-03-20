"""Agent Stack module -- VoiceApp, Session, and typed events.

Usage (standalone)::

    from plivo_agentstack.agent import VoiceApp, ToolCall

    app = VoiceApp()

    @app.on("tool.called")
    def on_tool_call(session, event: ToolCall):
        session.send_tool_result(event.id, {"ok": True})

    app.run(port=9000)

Usage (FastAPI integration)::

    from fastapi import FastAPI, WebSocket
    from plivo_agentstack.agent import VoiceApp, ToolCall

    fastapi_app = FastAPI()
    voice = VoiceApp()

    @voice.on("tool.called")
    def on_tool_call(session, event: ToolCall):
        session.send_tool_result(event.id, {"ok": True})

    @fastapi_app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket):
        await websocket.accept()
        await voice.handle_fastapi(websocket)
"""

from plivo_agentstack.agent.app import VoiceApp
from plivo_agentstack.agent.client import EAGERNESS_PRESETS, AgentClient
from plivo_agentstack.agent.events import (
    AgentFalseInterruption,
    AgentHandoff,
    AgentSessionEnded,
    AgentSessionStarted,
    AgentSpeechCompleted,
    AgentSpeechCreated,
    AgentSpeechStarted,
    AgentStateChanged,
    AgentToolCompleted,
    AgentToolFailed,
    AgentToolStarted,
    CallTransferred,
    ClearedAudio,
    Dtmf,
    DtmfSent,
    Error,
    Interruption,
    LlmAvailabilityChanged,
    ParticipantAdded,
    ParticipantRemoved,
    PlayCompleted,
    PlayedStream,
    Prompt,
    SessionUsage,
    StreamDtmf,
    StreamMedia,
    StreamStart,
    StreamStop,
    ToolCall,
    ToolExecuted,
    TurnCompleted,
    TurnDetected,
    TurnMetrics,
    UserBackchannel,
    UserIdle,
    UserStateChanged,
    VadSpeechStarted,
    VadSpeechStopped,
    VoicemailBeep,
    VoicemailDetected,
    parse_event,
)
from plivo_agentstack.agent.session import Session
from plivo_agentstack.agent.tools import (
    CollectAddress,
    CollectCreditCard,
    CollectDigits,
    CollectDOB,
    CollectEmail,
    CollectName,
    CollectPhone,
    EndCall,
    SendDtmf,
    WarmTransfer,
)

__all__ = [
    # Core
    "VoiceApp",
    "Session",
    "AgentClient",
    "EAGERNESS_PRESETS",
    # Event parsing
    "parse_event",
    # Session & lifecycle events
    "AgentSessionStarted",
    "AgentSessionEnded",
    "Error",
    # Conversation events
    "ToolCall",
    "TurnCompleted",
    "Prompt",
    "Interruption",
    "AgentHandoff",
    "Dtmf",
    "DtmfSent",
    # Agent tool events
    "AgentToolStarted",
    "AgentToolCompleted",
    "AgentToolFailed",
    # Speech lifecycle events
    "AgentSpeechCreated",
    "AgentSpeechStarted",
    "AgentSpeechCompleted",
    "AgentFalseInterruption",
    # State change events
    "UserStateChanged",
    "AgentStateChanged",
    # Diagnostics
    "VadSpeechStarted",
    "VadSpeechStopped",
    "TurnDetected",
    "TurnMetrics",
    "ToolExecuted",
    "LlmAvailabilityChanged",
    # Voicemail
    "VoicemailDetected",
    "VoicemailBeep",
    # Multi-party
    "ParticipantAdded",
    "ParticipantRemoved",
    "CallTransferred",
    # Playback
    "PlayCompleted",
    "UserIdle",
    # Adaptive interruption
    "UserBackchannel",
    # Usage
    "SessionUsage",
    # Audio stream events
    "StreamStart",
    "StreamMedia",
    "StreamDtmf",
    "PlayedStream",
    "ClearedAudio",
    "StreamStop",
    # Prebuilt tools (simple)
    "EndCall",
    "SendDtmf",
    "WarmTransfer",
    # Prebuilt tools (agent tools / server-side sub-agents)
    "CollectEmail",
    "CollectAddress",
    "CollectPhone",
    "CollectName",
    "CollectDOB",
    "CollectDigits",
    "CollectCreditCard",
]
