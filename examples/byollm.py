"""
BYOLLM Example -- Bring Your Own LLM

Config: stt + tts (Plivo runs STT + TTS, you run the LLM)

This is for when you need full control over the LLM -- fine-tuned models,
custom RAG, multi-agent orchestration, or complex conversation logic.

Plivo handles: audio transport, VAD, turn detection, STT, TTS, barge-in.
You handle: everything text-based (LLM inference, tool calling, context).

Note on tools:
  - Regular tools (lookup_order, transfer, etc.) work in BYOLLM -- but your
    external LLM handles tool calling, not the server. Define tools in your
    LLM's tool list, handle tool calls in your code, and stream text results
    back as tokens.
  - Simple customer-side tools (EndCall, etc.) work -- they are patterns in
    your WebSocket handler, not server-side tools.
  - Agent tools (CollectEmail, CollectAddress, etc.) do NOT work in BYOLLM.
    They require a server-side LLM to drive the multi-turn collection dialog,
    and the ByollmLLM adapter cannot do that. Implement collection logic in
    your own LLM code instead.

Features demonstrated:
  - VoiceApp server pattern (Plivo connects to you)
  - Async handler for streaming LLM tokens
  - Per-session conversation history via session.data
  - Context injection for external data (CRM, user profile)
  - Dynamic system prompt updates based on conversation state
  - Full tool calling loop (your LLM owns tool execution)

Providers:
  STT:  Deepgram Nova-3  (Plivo-managed)
  TTS:  ElevenLabs Sarah  (Plivo-managed)
  LLM:  OpenAI GPT-4o  (your API key, your code)

Usage:
  1. pip install plivo_agentstack[all] openai
  2. Set PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN, OPENAI_API_KEY env vars
  3. python byollm.py
"""

import asyncio
import os

from openai import AsyncOpenAI

from plivo_agentstack import AsyncClient
from plivo_agentstack.agent import (
    AgentSessionEnded,
    AgentSessionStarted,
    Dtmf,
    Error,
    Interruption,
    Prompt,
    TurnCompleted,
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
            # deepgram, google, azure, assemblyai, groq, openai
            "provider": "deepgram", "model": "nova-3",
            "language": "en", "api_key": DEEPGRAM_API_KEY,
        },
        tts={
            # elevenlabs, cartesia, google, azure, openai, deepgram
            "provider": "elevenlabs", "voice": "EXAVITQu4vr4xnSDxMaL",
            "model": "eleven_turbo_v2", "api_key": ELEVENLABS_API_KEY,
        },
        semantic_vad={
            "speech_activation_threshold": 0.5,
            "completed_turn_delay_ms": 250,
        },
        welcome_greeting="Welcome to Mario's Pizza! What can I get for you today?",
        websocket_url="ws://localhost:9000/ws",
        allow_interruptions=True,

        # User idle timeout -- in BYOLLM mode, reminder_message must be set
        # (no platform LLM to generate contextual nudges).
        # The extend_wait tool is auto-included in the agent config tools list.
        # Add it to your LLM's tool list. When your LLM calls extend_wait,
        # send {"type": "agent_session.extend_wait"} on the WS to extend the timer.
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


@app.on("session.started")
def on_started(session, event: AgentSessionStarted):
    session.data["messages"] = [
        {
            "role": "system",
            "content": (
                "You are a friendly pizza ordering assistant for Mario's Pizza. "
                "Help the customer place an order. Be concise -- this is a phone call, "
                "not a chat. Keep responses under 2 sentences when possible."
            ),
        }
    ]

    # session.data persists across events for this session.
    # Use it for conversation history, customer context, or any state
    # your LLM needs across turns.
    session.data["order_items"] = []
    session.data["customer_context"] = None

    # Inject external context (e.g., from CRM lookup) into the conversation.
    # In BYOLLM mode, inject() adds a system-level message that the platform
    # includes when sending transcripts. Your LLM won't see it directly --
    # use session.data instead for context you manage yourself.
    # session.inject("Customer is a returning customer. Last order: 2 large pizzas.")

    print(f"Session started: {session.agent_session_id}")


EXTEND_WAIT_TOOL = {
    "type": "function",
    "function": {
        "name": "extend_wait",
        "description": "Call when user asks for more time (hold on, give me a minute, etc.)",
        "parameters": {"type": "object", "properties": {}},
    },
}


@app.on("user.transcription")
async def on_prompt(session, event: Prompt):
    if not event.is_final or not event.text.strip():
        return

    print(f"  User said: '{event.text}'")
    session.data["messages"].append({"role": "user", "content": event.text})

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
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

    # Handle extend_wait tool call -- send WS command to extend idle timer
    if "extend_wait" in tool_calls:
        session.send_raw({"type": "agent_session.extend_wait"})
        print("  extend_wait: timer extended")

    # Tool calling in BYOLLM: your LLM handles tools entirely.
    # 1. Define tools in your LLM's format (OpenAI function calling, etc.)
    # 2. Parse tool_calls from the streaming response
    # 3. Execute the tool locally
    # 4. Feed the result back to the LLM in the next request
    # 5. Stream the LLM's final response as text tokens
    #
    # Unlike the full pipeline (where tool.called events arrive via WS),
    # in BYOLLM you handle the full tool execution loop yourself.

    assistant_text = "".join(full_response)
    session.data["messages"].append({"role": "assistant", "content": assistant_text})
    print(f"  LLM response: '{assistant_text}'")


@app.on("turn.completed")
def on_turn(session, event: TurnCompleted):
    """Track conversation state and update context dynamically."""
    # Example: after 3 turns, add urgency to the system prompt
    turn_count = len([m for m in session.data.get("messages", []) if m["role"] == "user"])
    if turn_count >= 3 and not session.data.get("customer_context"):
        session.data["customer_context"] = "returning_customer"
        # Update the system prompt for subsequent turns
        session.data["messages"][0]["content"] += (
            "\n\nNote: This customer has been chatting for a while. "
            "Be extra helpful and try to close the order."
        )
        print(f"  Context updated: returning customer after {turn_count} turns")


@app.on("agent.speech_interrupted")
def on_interruption(session, event: Interruption):
    print("  User interrupted -- TTS was cut")


@app.on("user.dtmf")
def on_dtmf(session, event: Dtmf):
    print(f"  DTMF: {event.digit}")
    if event.digit == "0":
        session.transfer("+18005551234")


@app.on("user.idle")
def on_user_idle(session, event: UserIdle):
    print(f"  User idle: retry={event.retry_count}, reason={event.reason}")


@app.on("session.error")
def on_error(session, event: Error):
    print(f"  Error [{event.code}]: {event.message}")


@app.on("session.ended")
def on_ended(session, event: AgentSessionEnded):
    print(f"Session ended: {event.duration_seconds}s")


if __name__ == "__main__":
    asyncio.run(init_agent())
    app.run(port=9000)
