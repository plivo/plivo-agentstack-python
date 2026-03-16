"""
Full Pipeline with Provider Fallback -- Resilient Voice Agent

Config: stt + llm + tts with fallback providers for each component

Demonstrates automatic failover between providers:
  - STT: Deepgram -> OpenAI Whisper (if Deepgram fails)
  - LLM: OpenAI GPT-4o -> Anthropic Claude -> Groq (if OpenAI fails)
  - TTS: ElevenLabs -> OpenAI TTS (if ElevenLabs fails)

The FallbackAdapter retries automatically -- no customer code needed.
If a provider returns an error or times out, the next provider in
the list is tried seamlessly. The caller never hears a gap.

Usage:
  1. Set provider API keys as env vars
  2. pip install plivo_agentstack[all]
  3. python full_pipeline_fallback.py
"""

import asyncio
import os

from plivo_agentstack import AsyncClient
from plivo_agentstack.agent import (
    AgentSessionEnded,
    AgentSessionStarted,
    Interruption,
    ToolCall,
    TurnCompleted,
    TurnMetrics,
    VoiceApp,
)

PLIVO_AUTH_ID = os.environ.get("PLIVO_AUTH_ID", "")
PLIVO_AUTH_TOKEN = os.environ.get("PLIVO_AUTH_TOKEN", "")
BASE_URL = os.environ.get("PLIVO_API_URL", "https://api.plivo.com")

# Provider API keys -- set all providers you want in the fallback chain
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

client = AsyncClient(PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN, base_url=BASE_URL)


# --- Tool definitions ---

CHECK_BALANCE_TOOL = {
    "name": "check_balance",
    "description": "Check the customer's account balance",
    "parameters": {
        "type": "object",
        "properties": {
            "account_id": {"type": "string", "description": "The account ID"},
        },
        "required": ["account_id"],
    },
}

SYSTEM_PROMPT = (
    "You are a helpful banking assistant. Be concise and professional. "
    "When the customer asks about their balance, use the check_balance tool."
)


# --- Agent setup with fallback providers ---


async def init_agent():
    """Create an agent with fallback providers for resilience.

    The primary provider is in stt/llm/tts. The fallback lists are tried
    in order if the primary fails. The pipeline automatically retries
    with the next provider -- no customer code needed.
    """
    agent = await client.agent.agents.create(
        agent_name="Resilient Banking Agent",

        # --- Primary STT ---
        stt={
            "provider": "deepgram",
            "model": "nova-3",
            "language": "en",
            "api_key": DEEPGRAM_API_KEY,
        },

        # --- STT Fallback: tried in order if Deepgram fails ---
        stt_fallback=[
            {
                "provider": "openai",
                "model": "gpt-4o-transcribe",
                "api_key": OPENAI_API_KEY,
            },
            # Add more STT providers as needed:
            # Supported: deepgram, google, azure, assemblyai, groq, openai
            # {"provider": "google", "language": "en-US"},
            # {"provider": "groq", "model": "whisper-large-v3", "api_key": GROQ_API_KEY},
        ],

        # --- Primary LLM ---
        llm={
            "provider": "openai",
            "model": "gpt-4o",
            "temperature": 0.2,
            "api_key": OPENAI_API_KEY,
            "system_prompt": SYSTEM_PROMPT,
            "tools": [CHECK_BALANCE_TOOL],
        },

        # --- LLM Fallback: tried in order if OpenAI fails ---
        # Supported: openai, anthropic, groq, google, azure, together,
        #            fireworks, perplexity, mistral
        llm_fallback=[
            {
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "api_key": ANTHROPIC_API_KEY,
            },
            {
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "api_key": GROQ_API_KEY,
            },
        ],

        # --- Primary TTS ---
        tts={
            "provider": "elevenlabs",
            "voice": "EXAVITQu4vr4xnSDxMaL",  # Sarah
            "model": "eleven_flash_v2_5",
            "api_key": ELEVENLABS_API_KEY,
        },

        # --- TTS Fallback: tried in order if ElevenLabs fails ---
        # Supported: elevenlabs, cartesia, google, azure, openai, deepgram
        tts_fallback=[
            {
                "provider": "openai",
                "model": "gpt-4o-mini-tts",
                "voice": "alloy",
                "api_key": OPENAI_API_KEY,
            },
            # Add more TTS providers as needed:
            # {"provider": "cartesia", "voice": "...", "api_key": "..."},
            # {"provider": "deepgram", "api_key": DEEPGRAM_API_KEY},
        ],

        # --- Standard pipeline config ---
        welcome_greeting="Hello! Welcome to Acme Bank. How can I help you today?",
        websocket_url="ws://localhost:9000/ws",
        speaks_first="agent",
        allow_interruptions=True,
        semantic_vad={
            "completed_turn_delay_ms": 250,
            "incomplete_turn_delay_ms": 1200,
            "min_interruption_duration_ms": 200,
        },
    )
    print(f"Agent created: {agent['agent_uuid']}")
    return agent


# --- Event handlers ---

app = VoiceApp()


@app.on("session.started")
def on_started(session, event: AgentSessionStarted):
    print(f"Session started: {session.agent_session_id}")
    session.update(events={"metrics_events": True})


@app.on("tool.called")
def on_tool_call(session, event: ToolCall):
    print(f"  Tool call: {event.name}({event.arguments})")

    if event.name == "check_balance":
        # Simulated balance lookup
        session.send_tool_result(event.id, {
            "balance": "$12,345.67",
            "account_type": "checking",
            "last_transaction": "Feb 14 -- $45.00 at Coffee Shop",
        })
    else:
        session.send_tool_error(event.id, f"Unknown tool: {event.name}")


@app.on("turn.metrics")
def on_metrics(session, event: TurnMetrics):
    """Monitor which provider handled each turn.

    When a fallback fires, stt_provider/llm_provider/tts_provider will
    show the fallback provider name instead of the primary.
    """
    print(
        f"  Metrics [turn {event.turn_number}]: "
        f"perceived={event.user_perceived_ms}ms "
        f"stt={event.stt_provider} "
        f"llm={event.llm_provider} "
        f"tts={event.tts_provider}"
    )


@app.on("turn.completed")
def on_turn(session, event: TurnCompleted):
    print(f"  User:  {event.user_text}")
    print(f"  Agent: {event.agent_text}")


@app.on("agent.speech_interrupted")
def on_interruption(session, event: Interruption):
    print(f"  Interrupted: '{event.interrupted_text or ''}'")


@app.on("session.ended")
def on_ended(session, event: AgentSessionEnded):
    print(f"Session ended: {event.duration_seconds}s, {event.turn_count} turns")


if __name__ == "__main__":
    asyncio.run(init_agent())
    app.run(port=9000)
