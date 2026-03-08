"""
Audio Stream Example — Full DIY Pipeline (Plivo Audio Streaming Protocol)

Config: no stt/llm/tts (raw audio relay, you handle everything)

Plivo is just the telephony bridge. You get raw audio frames and handle
everything yourself: STT, LLM, TTS, VAD, turn detection.

This is the escape hatch for customers running:
  - Speech-to-speech models (e.g. OpenAI Realtime API)
  - Custom voice pipelines on their own infra
  - Non-standard audio processing (music, sound effects, etc.)

Features demonstrated:
  - VoiceApp server pattern (Plivo connects to you)
  - Full Plivo Audio Streaming protocol compatibility
  - Sync handlers with per-session state (session.data)
  - Audio echo bot (buffers audio, plays it back)
  - Checkpoint events for playback tracking
  - clearAudio for interruption

Protocol (Plivo Audio Streaming):
  Inbound events (server -> you):
    - start:        Stream metadata (callId, streamId, mediaFormat, etc.)
    - media:        Audio chunk (base64 payload, ~20ms per chunk)
    - dtmf:         DTMF digit detected
    - playedStream: Checkpoint reached (audio before this point finished playing)
    - clearedAudio: Audio queue was cleared
    - stop:         Stream ended

  Outbound events (you -> server):
    - playAudio:  Send audio to the caller (base64 payload)
    - checkpoint: Mark a playback position (triggers playedStream when reached)
    - clearAudio: Clear all queued audio (for interruption)

Usage:
  1. pip install plivo_agentstack[all]
  2. Set PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN env vars
  3. python audio_stream.py
"""

import asyncio
import os
import time

from plivo_agentstack import AsyncClient
from plivo_agentstack.agent import (
    AgentSessionEnded,
    AgentSessionStarted,
    ClearedAudio,
    Dtmf,
    Error,
    PlayedStream,
    StreamMedia,
    StreamStart,
    StreamStop,
    VoiceApp,
)

PLIVO_AUTH_ID = os.environ.get("PLIVO_AUTH_ID", "")
PLIVO_AUTH_TOKEN = os.environ.get("PLIVO_AUTH_TOKEN", "")
BASE_URL = os.environ.get("PLIVO_API_URL", "https://api.plivo.com")
CALLBACK_HOST = os.environ.get("CALLBACK_HOST", "http://localhost:9001")
PLIVO_NUMBER = os.environ.get("PLIVO_NUMBER", "")

plivo = AsyncClient(PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN, base_url=BASE_URL)


async def init_agent():
    agent = await plivo.agent.agents.create(
        agent_name="Audio Echo Bot",
        audio_format="mulaw_8k",
        audio_channels=1,
        websocket_url="ws://localhost:9000/ws",
        stream={
            "extra_headers": {"userId": "12345", "tenant": "acme"},
        },
        callbacks={
            "hangup": {"url": f"{CALLBACK_HOST}/callbacks/hangup", "method": "POST"},
            "recording": {"url": f"{CALLBACK_HOST}/callbacks/recording", "method": "POST"},
            "ring": {"url": f"{CALLBACK_HOST}/callbacks/ring", "method": "POST"},
        },
    )
    agent_uuid = agent["agent_uuid"]
    print(f"Agent created: {agent_uuid}")

    if PLIVO_NUMBER:
        await plivo.agent.numbers.assign(agent_uuid, PLIVO_NUMBER)
        print(f"Number {PLIVO_NUMBER} assigned to agent")

        numbers = await plivo.agent.numbers.list(agent_uuid)
        print(f"Agent numbers: {numbers['numbers']}")
        print(f"Call {PLIVO_NUMBER} to reach the echo bot")


# --- Event handlers ---

app = VoiceApp()


@app.on("agent_session.started")
def on_session_started(session, event: AgentSessionStarted):
    print(f"Session started: {session.agent_session_id}")


@app.on("start")
def on_start(session, event: StreamStart):
    """Plivo stream started — receive audio stream metadata."""
    session.data["echo_buffer"] = []
    session.data["echo_playing"] = False
    session.data["encoding"] = event.content_type or "audio/x-mulaw"
    session.data["sample_rate"] = event.sample_rate or 8000

    print(
        f"Stream started: streamId={session.stream_id} "
        f"callId={event.call_id} "
        f"format={session.data['encoding']} "
        f"rate={session.data['sample_rate']}"
    )


@app.on("media")
def on_media(session, event: StreamMedia):
    """Plivo audio chunk received (~20ms of audio)."""
    session.data["echo_buffer"].append(event.payload)

    if len(session.data["echo_buffer"]) >= 100 and not session.data["echo_playing"]:
        session.data["echo_playing"] = True
        print(f"  Playing echo: {len(session.data['echo_buffer'])} chunks")

        for chunk_b64 in session.data["echo_buffer"]:
            session.send_media(
                chunk_b64,
                content_type=session.data.get("encoding", "audio/x-mulaw"),
                sample_rate=session.data.get("sample_rate", 8000),
            )
            time.sleep(0.020)  # 20ms pacing — sync handler, runs in thread

        session.send_checkpoint("echo-complete")
        session.data["echo_buffer"].clear()
        session.data["echo_playing"] = False


@app.on("dtmf")
def on_dtmf(session, event: Dtmf):
    print(f"  DTMF: {event.digit}")
    if event.digit == "*":
        print("  Clearing audio queue...")
        session.clear_audio()
    elif event.digit == "#":
        session.hangup()


@app.on("playedStream")
def on_played_stream(session, event: PlayedStream):
    print(f"  Checkpoint reached: {event.name}")


@app.on("clearedAudio")
def on_cleared_audio(session, event: ClearedAudio):
    print("  Audio cleared")


@app.on("error")
def on_error(session, event: Error):
    print(f"  Error [{event.code}]: {event.message}")


@app.on("stop")
def on_stop(session, event: StreamStop):
    print("Stream stopped")


@app.on("agent_session.ended")
def on_ended(session, event: AgentSessionEnded):
    print(f"Session ended: {event.duration_seconds}s")


if __name__ == "__main__":
    asyncio.run(init_agent())
    app.run(port=9000)
