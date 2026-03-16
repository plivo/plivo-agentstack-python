"""
Speech-to-Speech Example -- OpenAI Realtime / Gemini Live

Config: s2s only (no stt, llm, or tts)

Speech-to-speech is a separate pipeline where a single provider handles
STT + LLM + TTS natively. Audio goes directly to the S2S provider
(e.g. OpenAI Realtime API) and synthesized audio comes back -- Plivo
does not run separate STT, LLM, or TTS workers.

S2S is mutually exclusive with stt/llm/tts configs. If s2s is set,
do not set stt, llm, or tts.

Tool calling: S2S providers (OpenAI Realtime, Gemini Live) support function
calling natively via the realtime protocol. Define tools in the agent config
the same way as the full pipeline -- tool_call events arrive on the customer
WebSocket and you send tool_result back. Simple customer-side tools like
EndCall work identically to the full pipeline.

Agent tools (server-side sub-agents like CollectEmail, CollectAddress) have
limited support in S2S mode. They require a separate LLM to drive the
multi-turn collection dialog, and context suspension with realtime models
may not work cleanly. Prefer handling collection logic in your S2S system
prompt instead.

Providers:
  S2S: OpenAI Realtime (gpt-4o-realtime) or Gemini Live

Usage:
  1. pip install plivo_agentstack[all]
  2. Set PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN, OPENAI_API_KEY env vars
  3. python s2s_agent.py
"""

import asyncio
import os

from plivo_agentstack import AsyncClient
from plivo_agentstack.agent import (
    AgentSessionEnded,
    AgentSessionStarted,
    Dtmf,
    EndCall,
    ToolCall,
    VoiceApp,
)

PLIVO_AUTH_ID = os.environ.get("PLIVO_AUTH_ID", "")
PLIVO_AUTH_TOKEN = os.environ.get("PLIVO_AUTH_TOKEN", "")
BASE_URL = os.environ.get("PLIVO_API_URL", "https://api.plivo.com")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

plivo = AsyncClient(PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN, base_url=BASE_URL)

# --- Tool definitions ---
# S2S providers support function calling natively. Tools are defined the same
# way as the full pipeline -- the realtime model sees them and invokes them.

CHECK_WEATHER_TOOL = {
    "name": "check_weather",
    "description": "Get the current weather for a city",
    "parameters": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name"},
        },
        "required": ["city"],
    },
}

# EndCall: lets the S2S model end the call gracefully (customer-side tool)
end_call = EndCall(goodbye_message="Thanks for calling. Goodbye!")

TOOLS = [CHECK_WEATHER_TOOL, end_call.tool]

SYSTEM_PROMPT = (
    "You are a helpful voice assistant. Be concise -- this is a phone call. "
    "When the user asks about weather, use the check_weather tool. "
    f"{end_call.instructions}"
)


async def init_agent():
    """Create a speech-to-speech agent with tool calling.

    Only s2s config is set -- no stt, llm, or tts. The S2S provider
    handles the entire voice pipeline natively, including function calling.
    """
    agent = await plivo.agent.agents.create(
        agent_name="S2S Voice Agent",

        # Speech-to-speech -- the provider handles STT + LLM + TTS natively
        s2s={
            "provider": "openai_realtime",     # openai_realtime, gemini_live, azure_openai
            "model": "gpt-4o-realtime",
            "voice": "alloy",                  # alloy, echo, fable, onyx, nova, shimmer
            "api_key": OPENAI_API_KEY,
            "system_prompt": SYSTEM_PROMPT,
            "tools": TOOLS,
        },

        # No stt, llm, or tts -- S2S is a separate pipeline
        websocket_url="ws://localhost:9000/ws",
    )
    print(f"Agent created: {agent['agent_uuid']}")
    return agent


# --- Event handlers ---

app = VoiceApp()


@app.on("session.started")
def on_started(session, event: AgentSessionStarted):
    print(f"Session started: {session.agent_session_id}")


@app.on("tool.called")
def on_tool_call(session, event: ToolCall):
    """Handle tool calls from the S2S realtime model.

    Works identically to the full pipeline -- the S2S provider invokes tools
    natively and tool_call events arrive on the customer WebSocket.
    """
    print(f"  Tool call: {event.name}({event.arguments})")

    if event.name == "check_weather":
        city = event.arguments.get("city", "unknown")
        # In a real app, call a weather API here
        session.send_tool_result(event.id, {
            "city": city,
            "temperature": "72F",
            "condition": "sunny",
        })

    elif end_call.match(event):
        end_call.handle(session, event)

    else:
        session.send_tool_error(event.id, f"Unknown tool: {event.name}")


@app.on("user.dtmf")
def on_dtmf(session, event: Dtmf):
    """DTMF digit received from the caller."""
    print(f"  DTMF: {event.digit}")
    if event.digit == "#":
        session.hangup()


@app.on("session.error")
def on_error(session, event):
    print(f"  Error [{event.code}]: {event.message}")


@app.on("session.ended")
def on_ended(session, event: AgentSessionEnded):
    print(f"Session ended: {event.duration_seconds}s")


if __name__ == "__main__":
    asyncio.run(init_agent())
    app.run(port=9000)
