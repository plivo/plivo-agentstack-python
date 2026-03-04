"""FastAPI integration for Voice AI Agent.

Mounts the VoiceApp WebSocket handler inside a FastAPI application,
allowing you to combine voice agent endpoints with REST routes.

Prerequisites:
    pip install plivo_agent[all] fastapi uvicorn

Run:
    uvicorn agent_fastapi:fastapi_app --port 9000
"""

import logging

from fastapi import FastAPI, WebSocket

from plivo_agent.agent import (
    AgentSessionEnded,
    AgentSessionStarted,
    ToolCall,
    VoiceApp,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -- FastAPI app --

fastapi_app = FastAPI(title="Voice Agent")

# -- VoiceApp --

voice = VoiceApp()


@voice.on("agent_session.started")
async def on_session_started(session, event: AgentSessionStarted):
    logger.info("Session started: %s", event.agent_session_id)


@voice.on("tool_call")
async def on_tool_call(session, event: ToolCall):
    """Handle tool calls -- async handlers work natively with FastAPI."""
    logger.info("Tool call: %s(%s)", event.name, event.arguments)

    if event.name == "check_weather":
        city = event.arguments.get("city", "unknown")
        # In a real app, call an async HTTP API here
        result = {"city": city, "temp_f": 72, "condition": "sunny"}
        session.send_tool_result(event.id, result)
    elif event.name == "transfer_to_human":
        session.transfer("+18005551234")
        session.send_tool_result(event.id, {"status": "transferring"})
    else:
        session.send_tool_error(event.id, f"Unknown tool: {event.name}")


@voice.on("agent_session.ended")
async def on_session_ended(session, event: AgentSessionEnded):
    logger.info(
        "Session ended: duration=%ds turns=%s",
        event.duration_seconds,
        event.turn_count,
    )


# -- WebSocket endpoint --


@fastapi_app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    """Accept the WebSocket connection and hand off to VoiceApp."""
    await websocket.accept()
    await voice.handle_fastapi(websocket)


# -- Health check --


@fastapi_app.get("/health")
async def health():
    return {"status": "ok"}
