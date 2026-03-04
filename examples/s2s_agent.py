"""
Speech-to-Speech Example — OpenAI Realtime / Gemini Live

Config: s2s only (no stt, llm, or tts)

Speech-to-speech is a separate pipeline where a single provider handles
STT + LLM + TTS natively. Audio goes directly to the S2S provider
(e.g. OpenAI Realtime API) and synthesized audio comes back — Plivo
does not run separate STT, LLM, or TTS workers.

S2S is mutually exclusive with stt/llm/tts configs. If s2s is set,
do not set stt, llm, or tts.

Providers:
  S2S: OpenAI Realtime (gpt-4o-realtime) or Gemini Live

Usage:
  1. pip install plivo_agent[all]
  2. Set PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN, OPENAI_API_KEY env vars
  3. python s2s_agent.py
"""

import asyncio
import os

from plivo_agent import AsyncClient
from plivo_agent.agent import (
    AgentSessionEnded,
    AgentSessionStarted,
    VoiceApp,
)

PLIVO_AUTH_ID = os.environ.get("PLIVO_AUTH_ID", "")
PLIVO_AUTH_TOKEN = os.environ.get("PLIVO_AUTH_TOKEN", "")
BASE_URL = os.environ.get("PLIVO_API_URL", "https://api.plivo.com")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

plivo = AsyncClient(PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN, base_url=BASE_URL)


async def init_agent():
    """Create a speech-to-speech agent.

    Only s2s config is set — no stt, llm, or tts. The S2S provider
    handles the entire voice pipeline natively.
    """
    agent = await plivo.agent.agents.create(
        agent_name="S2S Voice Agent",
        s2s={
            "provider": "openai_realtime",
            "model": "gpt-4o-realtime",
            "voice": "alloy",
            "api_key": OPENAI_API_KEY,
        },
        websocket_url="ws://localhost:9000/ws",
    )
    print(f"Agent created: {agent['agent_uuid']}")
    return agent


# --- Event handlers ---

app = VoiceApp()


@app.on("agent_session.started")
def on_started(session, event: AgentSessionStarted):
    print(f"Session started: {session.agent_session_id}")


@app.on("error")
def on_error(session, event):
    print(f"  Error [{event.code}]: {event.message}")


@app.on("agent_session.ended")
def on_ended(session, event: AgentSessionEnded):
    print(f"Session ended: {event.duration_seconds}s")


if __name__ == "__main__":
    asyncio.run(init_agent())
    app.run(port=9000)
