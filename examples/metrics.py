"""
Metrics & Observability Example -- Latency Monitoring

Config: stt + llm + tts (full pipeline)

Demonstrates all diagnostic events available for monitoring pipeline
performance. Prints a formatted latency breakdown for every turn.

Events shown:
  - turn.metrics   -- per-turn latency chain + token/character usage
  - turn.completed -- transcript snapshot per turn
  - user.turn_completed  -- turn detection trigger + method
  - user.speech_started / user.speech_stopped -- speech activity
  - user.idle      -- user silence detection
  - agent.speech_interrupted   -- barge-in events

Usage:
  1. pip install plivo_agentstack[all]
  2. Set PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN env vars
  3. python metrics.py
"""

import asyncio
import os

from plivo_agentstack import AsyncClient
from plivo_agentstack.agent import (
    AgentSessionEnded,
    AgentSessionStarted,
    AgentSpeechCompleted,
    AgentSpeechCreated,
    AgentSpeechStarted,
    AgentStateChanged,
    Dtmf,
    DtmfSent,
    Interruption,
    TurnCompleted,
    TurnDetected,
    TurnMetrics,
    UserIdle,
    UserStateChanged,
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


async def init_agent():
    """Create a minimal full-pipeline agent for metrics observation."""
    agent = await plivo.agent.agents.create(
        agent_name="Metrics Observer",
        stt={
            # deepgram, google, azure, assemblyai, groq, openai
            "provider": "deepgram", "model": "nova-3",
            "language": "en", "api_key": DEEPGRAM_API_KEY,
        },
        llm={
            # openai, anthropic, groq, google, azure, together,
            # fireworks, perplexity, mistral
            "provider": "openai",
            "model": "gpt-4o",
            "api_key": OPENAI_API_KEY,
            "system_prompt": "You are a helpful assistant. Keep responses brief.",
            "tools": [],
        },
        tts={
            # elevenlabs, cartesia, google, azure, openai, deepgram
            "provider": "elevenlabs", "voice": "EXAVITQu4vr4xnSDxMaL",
            "model": "eleven_flash_v2_5", "api_key": ELEVENLABS_API_KEY,
        },
        welcome_greeting="Hi! Say something and I'll show you the latency breakdown.",
        websocket_url="ws://localhost:9000/ws",
    )
    print(f"Agent created: {agent['agent_uuid']}")
    return agent


# --- Event handlers ---

app = VoiceApp()


@app.on("session.started")
def on_started(session, event: AgentSessionStarted):
    print(f"Session started: {session.agent_session_id}")
    print("Enabling all diagnostic events...")

    # Enable all event categories
    session.update(events={
        "metrics_events": True,     # turn.metrics after each turn
        "vad_events": True,         # user.speech_started, user.speech_stopped
        "turn_events": True,        # user.turn_completed
    })


@app.on("turn.metrics")
def on_metrics(session, event: TurnMetrics):
    """Per-turn latency breakdown -- the most important diagnostic event.

    user_perceived_ms = stt_delay + turn_decision + llm_ttft + tts_pipeline
    This is the total time from user stops speaking to agent audio plays.
    """
    perceived = event.user_perceived_ms or 0
    stt = event.stt_delay_ms or 0
    turn = event.turn_decision_ms or 0
    llm = event.llm_ttft_ms or 0
    tts = event.tts_pipeline_ms or 0

    print(f"\n{'='*60}")
    print(f"  TURN {event.turn_number} METRICS {'(interrupted)' if event.interrupted else ''}")
    print(f"{'='*60}")
    print(f"  User perceived latency:  {perceived}ms")
    print(f"  +- STT delay:            {stt}ms")
    print(f"  +- Turn decision:        {turn}ms")
    print(f"  +- LLM TTFT:             {llm}ms")
    print(f"  +- TTS pipeline:         {tts}ms")

    if event.tts_gate_wait_ms:
        print(f"  TTS gate wait:           {event.tts_gate_wait_ms}ms")

    # Latency budget breakdown
    if perceived > 0:
        print("\n  Budget breakdown:")
        print(f"    STT:  {stt/perceived*100:5.1f}%")
        print(f"    Turn: {turn/perceived*100:5.1f}%")
        print(f"    LLM:  {llm/perceived*100:5.1f}%")
        print(f"    TTS:  {tts/perceived*100:5.1f}%")

    # Turn detection info
    print(f"\n  Turn method:     {event.turn_method or 'n/a'}")
    if event.turn_probability is not None:
        print(f"  Turn confidence: {event.turn_probability:.2f}")

    # LLM usage
    if event.llm_model:
        print(f"\n  LLM model:       {event.llm_model}")
        print(
            f"  Tokens:          "
            f"{event.llm_prompt_tokens or 0}p / {event.llm_completion_tokens or 0}c"
        )
        if event.llm_cache_read_tokens:
            print(f"  Cache read:      {event.llm_cache_read_tokens}")
        if event.context_msg_count:
            print(f"  Context msgs:    {event.context_msg_count}")

    # TTS usage
    if event.tts_characters:
        print(f"\n  TTS characters:  {event.tts_characters}")
        if event.tts_ttfb_ms:
            print(f"  TTS TTFB:        {event.tts_ttfb_ms}ms")
        if event.tts_audio_duration_ms:
            print(f"  TTS audio:       {event.tts_audio_duration_ms}ms")

    # Provider info
    if event.stt_provider:
        print(
            f"\n  Providers:       "
            f"{event.stt_provider} -> {event.llm_provider} -> {event.tts_provider}"
        )

    # STT confidence
    if event.stt_confidence is not None:
        print(f"  STT confidence:  {event.stt_confidence:.2f}")

    # Wall-clock timestamps
    if event.user_started_speaking_at:
        print("\n  Timestamps:")
        print(f"    User started:  {event.user_started_speaking_at}")
        print(f"    User stopped:  {event.user_stopped_speaking_at}")
        print(f"    Agent started: {event.agent_started_speaking_at}")
        print(f"    Agent stopped: {event.agent_stopped_speaking_at}")

    # Interruption details
    if event.interruption_reason:
        print(f"\n  Interruption:    {event.interruption_reason}")
        if event.pause_duration_ms:
            print(f"  Pause duration:  {event.pause_duration_ms}ms")

    print(f"{'='*60}\n")


@app.on("turn.completed")
def on_turn(session, event: TurnCompleted):
    print("  Turn completed:")
    print(f"    User:  {event.user_text}")
    print(f"    Agent: {event.agent_text}")


@app.on("user.turn_completed")
def on_turn_detected(session, event: TurnDetected):
    """Turn end detected by the turn detector."""
    print(f"  Turn detected: trigger={event.trigger} duration={event.duration_ms}ms")


@app.on("user.speech_started")
def on_vad_start(session, event: VadSpeechStarted):
    print(f"  VAD: speech started at {event.timestamp_ms}ms")


@app.on("user.speech_stopped")
def on_vad_stop(session, event: VadSpeechStopped):
    print(f"  VAD: speech stopped at {event.timestamp_ms}ms (duration={event.duration_ms}ms)")


@app.on("user.idle")
def on_user_idle(session, event: UserIdle):
    print(f"  User idle: retry={event.retry_count}, reason={event.reason}")


@app.on("user.dtmf")
def on_dtmf(session, event: Dtmf):
    print(f"  DTMF received: digit={event.digit}")


@app.on("dtmf.sent")
def on_dtmf_sent(session, event: DtmfSent):
    print(f"  DTMF sent: digits={event.digits}")


@app.on("agent.speech_interrupted")
def on_interruption(session, event: Interruption):
    print(f"  Interruption: '{event.interrupted_text or ''}'")


@app.on("user.state_changed")
def on_user_state(session, event: UserStateChanged):
    print(f"  User state: {event.old_state} -> {event.new_state}")


@app.on("agent.state_changed")
def on_agent_state(session, event: AgentStateChanged):
    print(f"  Agent state: {event.old_state} -> {event.new_state}")


@app.on("agent.speech_created")
def on_speech_created(session, event: AgentSpeechCreated):
    print(f"  Speech created: source={event.source}")


@app.on("agent.speech_started")
def on_speech_started(session, event: AgentSpeechStarted):
    print("  Agent speaking started")


@app.on("agent.speech_completed")
def on_speech_completed(session, event: AgentSpeechCompleted):
    print(f"  Agent speaking completed ({event.playback_position_s}s)")


@app.on("session.error")
def on_error(session, event):
    print(f"  Error [{event.code}]: {event.message}")


@app.on("session.ended")
def on_ended(session, event: AgentSessionEnded):
    print(f"\nSession ended: {event.duration_seconds}s, {event.turn_count} turns")


if __name__ == "__main__":
    asyncio.run(init_agent())
    app.run(port=9000)
