"""Agent Stack module -- VoiceApp, Session, and typed events.

Usage (standalone)::

    from plivo_agentstack.agent import VoiceApp, ToolCall

    app = VoiceApp()

    @app.on("tool_call")
    def on_tool_call(session, event: ToolCall):
        session.send_tool_result(event.id, {"ok": True})

    app.run(port=9000)

Usage (FastAPI integration)::

    from fastapi import FastAPI, WebSocket
    from plivo_agentstack.agent import VoiceApp, ToolCall

    fastapi_app = FastAPI()
    voice = VoiceApp()

    @voice.on("tool_call")
    def on_tool_call(session, event: ToolCall):
        session.send_tool_result(event.id, {"ok": True})

    @fastapi_app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket):
        await websocket.accept()
        await voice.handle_fastapi(websocket)
"""

from plivo_agentstack.agent.app import VoiceApp
from plivo_agentstack.agent.client import AgentClient
from plivo_agentstack.agent.events import (
    AgentHandoff,
    AgentSessionEnded,
    AgentSessionStarted,
    CallTransferred,
    ClearedAudio,
    Dtmf,
    Error,
    Interruption,
    ParticipantAdded,
    ParticipantRemoved,
    PlayCompleted,
    PlayedStream,
    Prompt,
    StreamDtmf,
    StreamMedia,
    StreamStart,
    StreamStop,
    ToolCall,
    TurnCompleted,
    TurnDetected,
    TurnMetrics,
    UserIdle,
    VadSpeechStarted,
    VadSpeechStopped,
    VoicemailBeep,
    VoicemailDetected,
    parse_event,
)
from plivo_agentstack.agent.session import Session

__all__ = [
    # Core
    "VoiceApp",
    "Session",
    "AgentClient",
    # Event parsing
    "parse_event",
    # Managed-mode events
    "AgentSessionStarted",
    "AgentSessionEnded",
    "Error",
    "ToolCall",
    "TurnCompleted",
    "Prompt",
    "Interruption",
    "AgentHandoff",
    "Dtmf",
    "VadSpeechStarted",
    "VadSpeechStopped",
    "TurnDetected",
    "VoicemailDetected",
    "VoicemailBeep",
    "ParticipantAdded",
    "ParticipantRemoved",
    "CallTransferred",
    "PlayCompleted",
    "UserIdle",
    "TurnMetrics",
    # Audio stream events
    "StreamStart",
    "StreamMedia",
    "StreamDtmf",
    "PlayedStream",
    "ClearedAudio",
    "StreamStop",
]
