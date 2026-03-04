"""
BYOLLM Example — Bring Your Own LLM

Config: stt + tts (Plivo runs STT + TTS, you run the LLM)

This is for when you need full control over the LLM — fine-tuned models,
custom RAG, multi-agent orchestration, or complex conversation logic.

Plivo handles: audio transport, VAD, turn detection, STT, TTS, barge-in.
You handle: everything text-based (LLM inference, tool calling, context).

Features demonstrated:
  - VoiceApp server pattern (Plivo connects to you)
  - Async handler for streaming LLM tokens
  - Per-session conversation history via session.data

Providers:
  STT:  Deepgram Nova-3  (Plivo-managed)
  TTS:  ElevenLabs Sarah  (Plivo-managed)
  LLM:  OpenAI GPT-4.1-mini  (your API key, your code)

Usage:
  1. pip install plivo_agent[all] openai
  2. Set PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN, OPENAI_API_KEY env vars
  3. python byollm.py
"""

import asyncio
import os

from openai import AsyncOpenAI

from plivo_agent import AsyncClient
from plivo_agent.agent import (
    AgentSessionEnded,
    AgentSessionStarted,
    Dtmf,
    Error,
    Interruption,
    Prompt,
    UserIdle,
    VoiceApp,
)

PLIVO_AUTH_ID = os.environ.get("PLIVO_AUTH_ID", "")
PLIVO_AUTH_TOKEN = os.environ.get("PLIVO_AUTH_TOKEN", "")
BASE_URL = os.environ.get("PLIVO_API_URL", "https://api.plivo.com")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


# --- Agent setup ---

plivo_client = AsyncClient(PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN, base_url=BASE_URL)


async def init_agent():
    agent = await plivo_client.agent.agents.create(
        agent_name="Mario's Pizza Bot",
        stt={
            "provider": "deepgram", "model": "nova-3",
            "language": "en", "api_key": DEEPGRAM_API_KEY,
        },
        tts={
            "provider": "elevenlabs", "voice": "sarah",
            "model": "eleven_turbo_v2", "api_key": ELEVENLABS_API_KEY,
        },
        vad={"threshold": 0.5},
        turn_detector={
            "silence_threshold_ms": 500,
            "min_speech_duration_ms": 100,
            "max_turn_duration_ms": 1000,
            "turn_enabled": True,
            "turn_threshold": 0.5,
        },
        welcome_greeting="Welcome to Mario's Pizza! What can I get for you today?",
        websocket_url="ws://localhost:9000/ws",
        interruption_enabled=True,
        idle_timeout={
            "no_response_timeout_s": 15,
            "reminder_message": "Are you still there? Would you like to place an order?",
            "extended_wait_time_s": 30,
            "max_retries": 3,
            "hangup_message": "I haven't heard from you. Goodbye!",
        },
    )
    print(f"Agent created: {agent['agent_uuid']}")


# --- Event handlers ---

app = VoiceApp()


@app.on("agent_session.started")
def on_started(session, event: AgentSessionStarted):
    session.data["messages"] = [
        {
            "role": "system",
            "content": (
                "You are a friendly pizza ordering assistant for Mario's Pizza. "
                "Help the customer place an order. Be concise — this is a phone call, "
                "not a chat. Keep responses under 2 sentences when possible."
            ),
        }
    ]
    print(f"Session started: {session.agent_session_id}")


EXTEND_WAIT_TOOL = {
    "type": "function",
    "function": {
        "name": "extend_wait",
        "description": "Call when user asks for more time (hold on, give me a minute, etc.)",
        "parameters": {"type": "object", "properties": {}},
    },
}


@app.on("prompt")
async def on_prompt(session, event: Prompt):
    if not event.is_final or not event.text.strip():
        return

    print(f"  User said: '{event.text}'")
    session.data["messages"].append({"role": "user", "content": event.text})

    response = await openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=session.data["messages"],
        tools=[EXTEND_WAIT_TOOL],
        stream=True,
        temperature=0.7,
        max_tokens=200,
    )

    full_response = []
    tool_calls = []
    async for chunk in response:
        delta = chunk.choices[0].delta
        if delta.content:
            token = delta.content
            full_response.append(token)
            session.send_text(token)
        if delta.tool_calls:
            for tc in delta.tool_calls:
                if tc.function and tc.function.name == "extend_wait":
                    tool_calls.append("extend_wait")

    session.send_text("", last=True)

    # Handle extend_wait tool call
    if "extend_wait" in tool_calls:
        session.extend_wait()
        print("  extend_wait: timer extended")

    assistant_text = "".join(full_response)
    session.data["messages"].append({"role": "assistant", "content": assistant_text})
    print(f"  LLM response: '{assistant_text}'")


@app.on("interruption")
def on_interruption(session, event: Interruption):
    print("  User interrupted — TTS was cut")


@app.on("dtmf")
def on_dtmf(session, event: Dtmf):
    print(f"  DTMF: {event.digit}")
    if event.digit == "0":
        session.transfer("+18005551234")


@app.on("user.idle")
def on_user_idle(session, event: UserIdle):
    print(f"  User idle: retry={event.retry_count}, reason={event.reason}")


@app.on("error")
def on_error(session, event: Error):
    print(f"  Error [{event.code}]: {event.message}")


@app.on("agent_session.ended")
def on_ended(session, event: AgentSessionEnded):
    print(f"Session ended: {event.duration_seconds}s")


if __name__ == "__main__":
    asyncio.run(init_agent())
    app.run(port=9000)
