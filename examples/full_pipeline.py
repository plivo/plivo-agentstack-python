"""
Full Pipeline Example — Customer Support Agent with Model Switching

Config: stt + llm + tts (Plivo runs the full AI pipeline)

Your code only handles:
  - Tool calls (e.g. order lookup, transfers, escalation)
  - Flow control (update, inject, speak, play, hangup)

Features demonstrated:
  - VoiceApp server pattern (Plivo connects to you)
  - Mid-call model switching (fast -> powerful on escalation)
  - Transfer with parallel/sequential hunt
  - Outbound calls with async voicemail detection
  - Pre-recorded audio playback (agent_session.play)
  - Per-turn latency metrics (turn.metrics)

TTS streaming:
  All speech — welcome_greeting, speak(), and LLM responses — is streamed
  through TTS by default. Audio chunks are sent to the caller as they're
  synthesized, not buffered until complete. This minimizes time-to-first-byte.

Providers:
  STT:  Deepgram Nova-3
  LLM:  OpenAI GPT-4.1-mini (conversation) / GPT-4.1 (escalation)
  TTS:  ElevenLabs Flash v2.5 (voice: Sarah)

Usage:
  1. pip install plivo_agent[all]
  2. Set PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN env vars
  3. python full_pipeline.py
  4. In a separate terminal: uvicorn callback_server:app --port 9001
"""

import asyncio
import os

from plivo_agent import AsyncClient
from plivo_agent.agent import (
    AgentHandoff,
    AgentSessionEnded,
    AgentSessionStarted,
    Interruption,
    PlayCompleted,
    ToolCall,
    TurnCompleted,
    TurnMetrics,
    UserIdle,
    VoiceApp,
    VoicemailBeep,
    VoicemailDetected,
)

PLIVO_AUTH_ID = os.environ.get("PLIVO_AUTH_ID", "")
PLIVO_AUTH_TOKEN = os.environ.get("PLIVO_AUTH_TOKEN", "")
BASE_URL = os.environ.get("PLIVO_API_URL", "https://api.plivo.com")
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
CALLBACK_HOST = os.environ.get("CALLBACK_HOST", "http://localhost:9001")

# Async REST client — kept alive for mid-call operations (dial, transfer, etc.)
client = AsyncClient(PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN, base_url=BASE_URL)


# --- Fake order database for the tool call demo ---

ORDERS = {
    "ORD-100": {"status": "shipped", "eta": "Feb 15", "tracking": "1Z999AA10123456784"},
    "ORD-200": {"status": "processing", "eta": "Feb 20", "tracking": None},
    "ORD-300": {"status": "delivered", "eta": None, "tracking": "1Z999AA10123456799"},
}


def lookup_order(order_id: str) -> dict:
    return ORDERS.get(order_id, {"error": f"Order {order_id} not found"})


# --- Tool definitions ---

LOOKUP_ORDER_TOOL = {
    "name": "lookup_order",
    "description": "Look up an order by its ID (e.g. ORD-100)",
    "parameters": {
        "type": "object",
        "properties": {
            "order_id": {"type": "string", "description": "The order ID"},
        },
        "required": ["order_id"],
    },
}

TRANSFER_TOOL = {
    "name": "transfer_to_human",
    "description": "Transfer the call to a human agent",
    "parameters": {
        "type": "object",
        "properties": {
            "reason": {"type": "string", "description": "Reason for transfer"},
        },
        "required": ["reason"],
    },
}

ESCALATE_TOOL = {
    "name": "escalate",
    "description": "Escalate to a more capable model for complex issues",
    "parameters": {
        "type": "object",
        "properties": {
            "reason": {"type": "string", "description": "Why escalation is needed"},
        },
        "required": ["reason"],
    },
}

PLAY_HOLD_MUSIC_TOOL = {
    "name": "play_hold_music",
    "description": "Play hold music while the customer waits (cannot be interrupted)",
    "parameters": {
        "type": "object",
        "properties": {},
    },
}

TOOLS = [LOOKUP_ORDER_TOOL, TRANSFER_TOOL, ESCALATE_TOOL, PLAY_HOLD_MUSIC_TOOL]

SYSTEM_PROMPT = (
    "You are a helpful customer support agent for Acme Corp. "
    "Be friendly, concise, and professional. When a customer "
    "asks about an order, use the lookup_order tool."
)


# --- Agent setup (one-time, or pre-created via dashboard) ---


async def init_agent():
    """Create a full-pipeline agent (dual mode — simple two-party call)."""
    agent = await client.agent.agents.create(
        agent_name="Acme Support Agent",

        # --- STT (Speech-to-Text) ----------------------------------------
        stt={
            "provider": "deepgram",         # deepgram (default), google, azure
            "model": "nova-3",              # nova-3 (latest), nova-3-general
            "language": "en",               # BCP 47: en, fr, es, de, pt, etc.
            "api_key": DEEPGRAM_API_KEY,
        },

        # --- LLM (Language Model) ----------------------------------------
        llm={
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "temperature": 0.2,
            "api_key": OPENAI_API_KEY,
            "system_prompt": SYSTEM_PROMPT,
            "tools": TOOLS,
        },

        # --- TTS (Text-to-Speech) ----------------------------------------
        tts={
            "provider": "elevenlabs",
            "voice": "EXAVITQu4vr4xnSDxMaL",
            "model": "eleven_flash_v2_5",
            "api_key": ELEVENLABS_API_KEY,
            "output_format": "pcm_16000",
            "stability": 0.5,
            "similarity_boost": 0.75,
        },

        # --- VAD (Voice Activity Detection) -------------------------------
        vad={
            "threshold": 0.5,
        },

        # --- Turn Detector ------------------------------------------------
        turn_detector={
            "silence_threshold_ms": 500,
            "silence_fallback_ms": 1400,
            "min_speech_duration_ms": 100,
            "max_turn_duration_ms": 30000,
            "turn_enabled": True,
            "turn_threshold": 0.5,
            "early_trigger_min_silence_ms": 200,
            "min_interruption_duration_ms": 200,
            "resume_false_interruption": True,
            "false_interruption_timeout_ms": 500,
            "min_silence_for_resume_ms": 400,
        },

        # --- Agent behavior -----------------------------------------------
        welcome_greeting="Hi there! Thanks for calling Acme Corp. How can I help you today?",
        websocket_url="ws://localhost:9000/ws",
        speaks_first="agent",
        interruption_enabled=True,
        greeting_interruptible=True,

        # User idle timeout
        idle_timeout={
            "no_response_timeout_s": 15,
            "extended_wait_time_s": 30,
            "max_retries": 3,
            "hangup_message": "I haven't heard from you, so I'll end the call. Goodbye.",
        },

        # Webhook callbacks
        callbacks={
            "hangup": {"url": f"{CALLBACK_HOST}/callbacks/hangup", "method": "POST"},
            "recording": {"url": f"{CALLBACK_HOST}/callbacks/recording", "method": "POST"},
        },
    )
    agent_uuid = agent["agent_uuid"]
    print(f"Agent created: {agent_uuid}")

    # --- Assign a phone number for inbound calls ---
    # await client.agent.numbers.assign(agent_uuid, "+14155551234")

    return agent


# --- Outbound calls ---


async def initiate_outbound_call(agent_uuid: str, to: str):
    """Initiate an outbound call."""
    call = await client.agent.calls.initiate(
        agent_uuid=agent_uuid,
        from_="+14155551234",
        to=to,
        ring_timeout=30,
    )
    print(f"Outbound call: {call['call_uuid']}")
    return call


# --- Event handlers ---

app = VoiceApp()


@app.on("agent_session.started")
def on_started(session, event: AgentSessionStarted):
    print(f"Session started: {session.agent_session_id}")
    session.update(events={"metrics_events": True})


@app.on("tool_call")
def on_tool_call(session, event: ToolCall):
    """Handle tool calls from the LLM."""
    print(f"  Tool call: {event.name}({event.arguments})")

    if event.name == "lookup_order":
        result = lookup_order(event.arguments.get("order_id", ""))
        session.send_tool_result(event.id, result)

    elif event.name == "transfer_to_human":
        session.speak("Let me transfer you to a specialist. One moment please.")
        session.transfer_to_number("+18005551234")

    elif event.name == "play_hold_music":
        session.play("hold_music.wav", allow_interruption=False)
        session.send_tool_result(event.id, {"status": "playing_hold_music"})

    elif event.name == "escalate":
        session.speak("Let me connect you with a specialist.")
        session.update(
            system_prompt=(
                "You are a senior support specialist at Acme Corp. "
                "You have access to refund and exchange tools. "
                "Be empathetic and resolve the issue."
            ),
            tools=[LOOKUP_ORDER_TOOL, TRANSFER_TOOL],
            llm={"model": "gpt-4.1"},
        )
        session.send_tool_result(event.id, {"status": "escalated"})

    else:
        session.send_tool_error(event.id, f"Unknown tool: {event.name}")


@app.on("voicemail.detected")
def on_voicemail(session, event: VoicemailDetected):
    if event.result == "machine":
        print(f"  Machine detected — waiting for beep: {session.call_uuid}")
    else:
        print(f"  Human answered: {session.call_uuid}")


@app.on("voicemail.beep")
def on_beep(session, event: VoicemailBeep):
    print(f"  Beep detected: freq={event.frequency_hz}Hz")
    session.speak("Hi, this is Acme Corp returning your call. Please call us back.")
    session.hangup()


@app.on("play.completed")
def on_play_completed(session, event: PlayCompleted):
    print("  Play completed — resuming conversation")
    session.speak("Thank you for waiting. I'm back.")


@app.on("agent.handoff")
def on_handoff(session, event: AgentHandoff):
    print(f"  Agent handoff: new agent = {event.new_agent}")


@app.on("user.idle")
def on_user_idle(session, event: UserIdle):
    print(f"  User idle: retry={event.retry_count}, reason={event.reason}")


@app.on("turn.metrics")
def on_metrics(session, event: TurnMetrics):
    print(
        f"  Metrics [turn {event.turn_number}]: "
        f"perceived={event.user_perceived_ms}ms "
        f"stt={event.stt_delay_ms}ms "
        f"llm_ttft={event.llm_ttft_ms}ms "
        f"tts={event.tts_pipeline_ms}ms "
        f"method={event.turn_method}"
    )


@app.on("turn.completed")
def on_turn(session, event: TurnCompleted):
    print(f"  User:  {event.user_text}")
    print(f"  Agent: {event.agent_text}")


@app.on("interruption")
def on_interruption(session, event: Interruption):
    print(f"  User interrupted: '{event.interrupted_text or ''}'")


@app.on("error")
def on_error(session, event):
    print(f"  Error [{event.code}]: {event.message}")


@app.on("agent_session.ended")
def on_ended(session, event: AgentSessionEnded):
    print(f"Session ended: {event.duration_seconds}s, {event.turn_count} turns")


@app.on_handler_error
def on_handler_error(session, event, exc):
    print(f"  Handler error: {exc}")


if __name__ == "__main__":
    asyncio.run(init_agent())
    app.run(port=9000)
