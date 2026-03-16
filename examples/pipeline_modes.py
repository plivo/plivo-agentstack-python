"""
Config Examples -- All Pipeline Configurations
===============================================

There is no `mode` field. Behavior is determined entirely by which configs
(stt, llm, tts) you include when creating the agent:

  +------------------------+------------------------+-----------------+
  | Config provided        | Pipeline behavior      | You handle      |
  +------------------------+------------------------+-----------------+
  | stt + llm + tts        | Full AI pipeline       | Tool calls      |
  | stt + tts              | Plivo STT + TTS        | Your own LLM    |
  | stt only               | Plivo STT              | LLM + TTS       |
  | tts only               | Plivo TTS              | STT + LLM       |
  | nothing                | Raw audio relay        | Everything      |
  +------------------------+------------------------+-----------------+

The key insight: omit a config to handle that component yourself.
VAD and turn detection always run when any config is present.

Usage:
  1. pip install plivo_agentstack[all] openai
  2. Set PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN env vars
  3. python pipeline_modes.py [full-ai | customer-llm | stt-only | tts-only | raw-audio]
"""

import asyncio
import base64
import os

from plivo_agentstack import AsyncClient
from plivo_agentstack.agent import (
    AgentSessionEnded,
    AgentSessionStarted,
    Dtmf,
    PlayCompleted,
    Prompt,
    StreamDtmf,
    StreamMedia,
    StreamStart,
    ToolCall,
    TurnCompleted,
    VadSpeechStarted,
    VadSpeechStopped,
    VoiceApp,
)

PLIVO_AUTH_ID = os.environ.get("PLIVO_AUTH_ID", "")
PLIVO_AUTH_TOKEN = os.environ.get("PLIVO_AUTH_TOKEN", "")
BASE_URL = os.environ.get("PLIVO_API_URL", "https://api.plivo.com")
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

plivo = AsyncClient(PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN, base_url=BASE_URL)


# =========================================================================
# Example 1: Full AI Pipeline (stt + llm + tts)
#
# Plivo runs everything. You only handle tool calls and flow control.
# =========================================================================

async def create_full_ai_agent():
    return await plivo.agent.agents.create(
        agent_name="Full AI Support Agent",
        stt={
            "provider": "deepgram", "model": "nova-3",
            "language": "en", "api_key": DEEPGRAM_API_KEY,
        },
        llm={
            "provider": "openai",
            "model": "gpt-4o",
            "api_key": OPENAI_API_KEY,
            "system_prompt": "You are a helpful support agent.",
            "tools": [{
                "name": "lookup_order",
                "description": "Look up an order by ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string"},
                    },
                    "required": ["order_id"],
                },
            }],
        },
        tts={
            "provider": "elevenlabs", "voice": "EXAVITQu4vr4xnSDxMaL",
            "api_key": ELEVENLABS_API_KEY,
        },
        welcome_greeting="Hi! How can I help you?",
        websocket_url="ws://localhost:9000/ws",
    )


app_full_ai = VoiceApp()


@app_full_ai.on("tool.called")
def on_tool_call(session, event: ToolCall):
    # Only event you need to handle -- Plivo does everything else
    session.send_tool_result(event.id, {"status": "shipped", "eta": "Feb 20"})


@app_full_ai.on("play.completed")
def on_play_done(session, event: PlayCompleted):
    session.speak("Thanks for waiting.")


@app_full_ai.on("turn.completed")
def on_turn(session, event: TurnCompleted):
    print(f"  User:  {event.user_text}")
    print(f"  Agent: {event.agent_text}")


# =========================================================================
# Example 2: Customer LLM (stt + tts, no llm)
#
# Plivo handles speech-to-text and text-to-speech.
# You run your own LLM and stream tokens back.
# =========================================================================

async def create_customer_llm_agent():
    return await plivo.agent.agents.create(
        agent_name="Customer LLM Agent",
        stt={
            "provider": "deepgram", "model": "nova-3",
            "language": "en", "api_key": DEEPGRAM_API_KEY,
        },
        # llm: omitted -- you run your own
        tts={
            "provider": "elevenlabs", "voice": "EXAVITQu4vr4xnSDxMaL",
            "api_key": ELEVENLABS_API_KEY,
        },
        welcome_greeting="Hi! How can I help you?",
        websocket_url="ws://localhost:9000/ws",
    )


app_customer_llm = VoiceApp()


@app_customer_llm.on("user.transcription")
async def on_prompt(session, event: Prompt):
    """Plivo STT sends you the transcript. You run LLM, stream tokens back."""
    if not event.is_final:
        return

    print(f"  User said: {event.text}")

    # Run your own LLM (OpenAI, Anthropic, local model, whatever)
    from openai import AsyncOpenAI
    oai = AsyncOpenAI()

    stream = await oai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": event.text},
        ],
        stream=True,
    )

    # Stream each token back -- Plivo TTS synthesizes as tokens arrive
    async for chunk in stream:
        token = chunk.choices[0].delta.content or ""
        if token:
            session.send_text(token)

    # Signal end of response -- Plivo TTS flushes remaining audio
    session.send_text("", last=True)


# =========================================================================
# Example 3: STT Only (stt, no llm, no tts)
#
# Plivo transcribes. You handle LLM + TTS yourself.
# VAD + turn detection run automatically.
# Use case: real-time captioning, custom LLM + custom TTS, analytics.
# =========================================================================

async def create_stt_only_agent():
    return await plivo.agent.agents.create(
        agent_name="STT Relay Agent",
        stt={
            "provider": "deepgram", "model": "nova-3",
            "language": "en", "api_key": DEEPGRAM_API_KEY,
        },
        # llm: omitted -- you handle it
        # tts: omitted -- you handle it
        events={"vad_events": True},  # enable VAD events for on_vad_start/stop handlers
        websocket_url="ws://localhost:9000/ws",
    )


app_stt_only = VoiceApp()


@app_stt_only.on("user.transcription")
def on_transcript(session, event: Prompt):
    """You get transcripts from Plivo STT. Handle LLM + TTS yourself."""
    if event.is_final:
        print(f"  Transcript: {event.text}")

        # No Plivo TTS -- send audio directly if you want to respond
        # wav_b64 = my_tts_engine.synthesize(f"You said: {event.text}")
        # session.play(wav_b64)


@app_stt_only.on("user.speech_started")
def on_vad_start(session, event: VadSpeechStarted):
    # VAD runs automatically when any config is present
    print(f"  Speech started at {event.timestamp_ms}ms")


@app_stt_only.on("user.speech_stopped")
def on_vad_stop(session, event: VadSpeechStopped):
    print(f"  Speech stopped after {event.duration_ms}ms")


# =========================================================================
# Example 4: TTS Only (tts, no stt, no llm)
#
# You send text, Plivo synthesizes and plays it. No transcription.
# Use case: announcement systems, IVR prompts, notification calls.
# =========================================================================

async def create_tts_only_agent():
    return await plivo.agent.agents.create(
        agent_name="Notification Agent",
        # stt: omitted -- no transcription needed
        # llm: omitted -- you generate the text
        tts={
            "provider": "elevenlabs", "voice": "EXAVITQu4vr4xnSDxMaL",
            "api_key": ELEVENLABS_API_KEY,
        },
        welcome_greeting="Hello, you have a new notification.",
        websocket_url="ws://localhost:9000/ws",
    )


app_tts_only = VoiceApp()


@app_tts_only.on("session.started")
def on_tts_started(session, event: AgentSessionStarted):
    print(f"  Session started: {session.agent_session_id}")
    # Welcome greeting plays automatically via TTS.
    # Use speak() to say more things:
    #   session.speak("Your appointment is confirmed for tomorrow at 3 PM.")


@app_tts_only.on("user.dtmf")
def on_tts_dtmf(session, event: Dtmf):
    """Handle DTMF input since there's no STT."""
    print(f"  DTMF: {event.digit}")
    if event.digit == "1":
        session.speak("Your balance is forty two dollars and seventeen cents.")
    elif event.digit == "2":
        session.speak("Transferring you to an agent.")
        session.transfer("+18005551234")
    elif event.digit == "#":
        session.speak("Goodbye.")
        session.hangup()


@app_tts_only.on("session.ended")
def on_tts_ended(session, event: AgentSessionEnded):
    print(f"  Session ended: {event.duration_seconds}s")


# =========================================================================
# Example 5: Raw Audio Relay (no stt, no llm, no tts)
#
# No configs at all. Plivo sends raw audio frames, you send audio back.
# No VAD, no turn detection, no AI processing.
# Use case: OpenAI Realtime API, custom voice pipeline, speech-to-speech.
# =========================================================================

async def create_raw_audio_agent():
    return await plivo.agent.agents.create(
        agent_name="Raw Audio Relay",
        # No stt, llm, or tts -- pure audio relay
        websocket_url="ws://localhost:9000/ws",
    )


app_raw_audio = VoiceApp()


@app_raw_audio.on("start")
def on_audio_start(session, event: StreamStart):
    """Plivo stream started -- raw audio mode uses the Plivo protocol directly."""
    session.data["frames"] = []
    print(
        f"  Raw audio: format={event.content_type} "
        f"rate={event.sample_rate}"
    )


@app_raw_audio.on("media")
def on_media(session, event: StreamMedia):
    """Raw audio frames -- do whatever you want."""
    audio_bytes = base64.b64decode(event.payload)
    session.data["frames"].append(audio_bytes)

    # Feed to your own STT, speech-to-speech model, etc.
    # Send audio back (Plivo playAudio protocol):
    #   session.send_media(response_audio_b64, content_type="audio/x-mulaw", sample_rate=8000)
    # Mark playback position:
    #   session.send_checkpoint("my-marker")
    # Clear queued audio (for interruption):
    #   session.clear_audio()


@app_raw_audio.on("dtmf")
def on_dtmf(session, event: StreamDtmf):
    print(f"  DTMF: {event.digit}")
    if event.digit == "#":
        session.hangup()


# =========================================================================
# Run whichever example you want
# =========================================================================

if __name__ == "__main__":
    import sys

    examples = {
        "full-ai": (create_full_ai_agent, app_full_ai),
        "customer-llm": (create_customer_llm_agent, app_customer_llm),
        "stt-only": (create_stt_only_agent, app_stt_only),
        "tts-only": (create_tts_only_agent, app_tts_only),
        "raw-audio": (create_raw_audio_agent, app_raw_audio),
    }

    choice = sys.argv[1] if len(sys.argv) > 1 else "full-ai"
    if choice not in examples:
        print(f"Usage: python pipeline_modes.py [{' | '.join(examples)}]")
        sys.exit(1)

    create_fn, voice_app = examples[choice]
    agent = asyncio.run(create_fn())
    print(f"Agent created: {agent['agent_uuid']}  (example: {choice})")
    voice_app.run(port=9000)
