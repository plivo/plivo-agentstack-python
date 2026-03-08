"""Standalone Voice AI Agent example using VoiceApp.

Creates an agent via the REST API, then runs a WebSocket server that
handles tool calls during live voice sessions.

Prerequisites:
    pip install plivo_agentstack[all]

Environment variables:
    PLIVO_AUTH_ID      -- Your Plivo auth ID
    PLIVO_AUTH_TOKEN   -- Your Plivo auth token

Run:
    python agent_basic.py
"""

import asyncio
import logging
import os

from plivo_agentstack import AsyncClient
from plivo_agentstack.agent import (
    AgentSessionEnded,
    AgentSessionStarted,
    ToolCall,
    VoiceApp,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -- 1. Create the agent via REST API --

WEBSOCKET_URL = os.environ.get("WEBSOCKET_URL", "wss://your-server.example.com/ws")


async def create_agent() -> str:
    """Create an agent and return its UUID."""
    async with AsyncClient() as client:
        resp = await client.agent.agents.create(
            agent_name="Support Bot",
            websocket_url=WEBSOCKET_URL,
            stt={
                "provider": "deepgram",
                "language": "en",
            },
            llm={
                "provider": "openai",
                "model": "gpt-4o",
                "system_prompt": (
                    "You are a helpful customer support agent for Acme Corp. "
                    "Use the lookup_order tool when customers ask about their orders."
                ),
                "tools": [
                    {
                        "name": "lookup_order",
                        "description": "Look up an order by ID",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "order_id": {
                                    "type": "string",
                                    "description": "The order ID, e.g. ORD-1234",
                                },
                            },
                            "required": ["order_id"],
                        },
                    },
                ],
            },
            tts={
                "provider": "eleven_labs",
                "voice": "rachel",
            },
        )
        agent_uuid = resp["agent_uuid"]
        logger.info("Created agent: %s", agent_uuid)
        return agent_uuid


# -- 2. Set up the VoiceApp WebSocket server --

app = VoiceApp()


@app.on("agent_session.started")
def on_session_started(session, event: AgentSessionStarted):
    logger.info(
        "Session started: session_id=%s call_id=%s caller=%s",
        event.agent_session_id,
        event.call_id,
        event.caller,
    )
    # Store caller info in per-session state
    session.data["caller"] = event.caller


@app.on("tool_call")
def on_tool_call(session, event: ToolCall):
    """Handle tool calls from the LLM."""
    logger.info("Tool call: name=%s args=%s", event.name, event.arguments)

    if event.name == "lookup_order":
        order_id = event.arguments.get("order_id", "")
        # In a real app, query your database here
        result = {
            "order_id": order_id,
            "status": "shipped",
            "tracking": "1Z999AA10123456784",
            "eta": "2026-03-07",
        }
        session.send_tool_result(event.id, result)
    else:
        session.send_tool_error(event.id, f"Unknown tool: {event.name}")


@app.on("agent_session.ended")
def on_session_ended(session, event: AgentSessionEnded):
    logger.info(
        "Session ended: duration=%ds turns=%s",
        event.duration_seconds,
        event.turn_count,
    )


@app.on_handler_error
def on_error(session, event, exc):
    logger.error("Handler error in session %s: %s", session.agent_session_id, exc)


# -- 3. Run --

if __name__ == "__main__":
    # Create the agent first (one-time setup)
    asyncio.run(create_agent())

    # Start the WebSocket server (blocks forever)
    logger.info("Starting VoiceApp on port 9000...")
    app.run(port=9000)
