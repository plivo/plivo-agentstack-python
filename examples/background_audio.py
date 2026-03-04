"""
Background Audio Example — Ambient Sound During Calls

Demonstrates how to use built-in background sounds to make AI agent calls
feel more natural. Background audio plays continuously (mixed with agent
speech) and can be switched or stopped at runtime.

Built-in sounds:
  - "office"                 Office ambience (chatter, keyboards, phones)
  - "city-street"            City/street ambient noise
  - "crowded-room"           Crowded room / busy venue
  - "call-center"            Call center ambience (voices, phones ringing)
  - "typing"                 Keyboard typing (longer loop, ~10s)
  - "typing-short"           Keyboard typing (shorter, ~3s)

Two ways to enable background audio:

  1. At agent creation (declarative):
     Set `background_audio={"sound": "office", "volume": 0.4}` when creating
     the agent. The sound starts automatically on every call.

  2. At runtime (WebSocket commands):
     Call `session.play_background("office", volume=0.4)` to start/switch,
     and `session.stop_background()` to stop.

Volume levels:
  0.1-0.2  Subtle background presence
  0.3-0.5  Noticeable but not distracting (recommended for calls)
  0.6-0.8  Prominent, can make speech harder to hear
  1.0      Full volume (use sparingly)

Usage:
  1. pip install plivo_agent[all]
  2. Set PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN env vars
  3. python background_audio.py
"""

import asyncio
import os

from plivo_agent import AsyncClient
from plivo_agent.agent import (
    AgentSessionEnded,
    AgentSessionStarted,
    ToolCall,
    TurnCompleted,
    VoiceApp,
)

PLIVO_AUTH_ID = os.environ.get("PLIVO_AUTH_ID", "")
PLIVO_AUTH_TOKEN = os.environ.get("PLIVO_AUTH_TOKEN", "")
BASE_URL = os.environ.get("PLIVO_API_URL", "https://api.plivo.com")
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

plivo = AsyncClient(PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN, base_url=BASE_URL)

TOOLS = [
    {
        "name": "check_status",
        "description": "Check order status",
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
]


async def init_agent():
    """Create an agent with background audio enabled from the start."""
    agent = await plivo.agent.agents.create(
        agent_name="Office Support Agent",
        stt={
            "provider": "deepgram",
            "model": "nova-3",
            "language": "en",
            "api_key": DEEPGRAM_API_KEY,
        },
        llm={
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "api_key": OPENAI_API_KEY,
            "system_prompt": (
                "You are a helpful office support agent. "
                "Be friendly, professional, and concise."
            ),
            "tools": TOOLS,
        },
        tts={
            "provider": "elevenlabs",
            "voice": "EXAVITQu4vr4xnSDxMaL",
            "model": "eleven_flash_v2_5",
            "api_key": ELEVENLABS_API_KEY,
            "output_format": "pcm_16000",
        },
        welcome_greeting="Hi! Thanks for calling support. How can I help?",
        websocket_url="ws://localhost:9000/ws",
        background_audio={
            "sound": "office",
            "volume": 0.3,
            "loop": True,
        },
    )
    print(f"Agent created: {agent['agent_uuid']}")
    return agent


# --- Event handlers ---

app = VoiceApp()


@app.on("agent_session.started")
def on_started(session, event: AgentSessionStarted):
    print(f"Session started: {session.agent_session_id}")


@app.on("tool_call")
def on_tool_call(session, event: ToolCall):
    print(f"  Tool call: {event.name}")

    if event.name == "check_status":
        # Switch to typing sound while "looking up" the order
        session.play_background("typing", volume=0.5)

        result = {"status": "shipped", "eta": "March 5"}
        session.send_tool_result(event.id, result)

        # Switch back to office ambience after responding
        session.play_background("office", volume=0.3)
    else:
        session.send_tool_error(event.id, f"Unknown tool: {event.name}")


@app.on("turn.completed")
def on_turn(session, event: TurnCompleted):
    print(f"  User:  {event.user_text}")
    print(f"  Agent: {event.agent_text}")


@app.on("agent_session.ended")
def on_ended(session, event: AgentSessionEnded):
    print(f"Session ended: {event.duration_seconds}s")


if __name__ == "__main__":
    asyncio.run(init_agent())
    app.run(port=9000)
