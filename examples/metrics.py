"""
Metrics & Observability Example -- Comprehensive Latency Monitoring

Config: stt + llm + tts (full pipeline)

Demonstrates all diagnostic events and metrics fields available for monitoring
pipeline performance. Covers every field from all 7 pipeline
metrics classes + ChatMessage MetricsReport:

  - LLMMetrics: 13/13 fields (label, request_id, speech_id, timestamp, ...)
  - STTMetrics: 9/9 fields (duration, audio_duration, streamed, tokens, ...)
  - TTSMetrics: 14/14 fields (segment_id, speech_id, streamed, tokens, ...)
  - VADMetrics: 5/5 fields (idle_time, inference_count, duration, label, ...)
  - Turn detection: 6/6 fields (speech_id, method, probability, threshold, ...)
  - InterruptionMetrics: 8/8 fields (total_duration, prediction, detection, ...)
  - RealtimeModelMetrics: 15/15 fields (all token detail breakdowns, ...)
  - ChatMessage.metrics: 8/8 fields (SDK-measured latency, ...)

Events shown:
  - turn.metrics         -- per-turn latency chain + full provider stats
  - turn.completed       -- transcript snapshot per turn (with latency highlights)
  - user.turn_completed  -- turn detection trigger + method
  - user.speech_started / user.speech_stopped -- VAD with inference stats
  - user.idle            -- user silence detection
  - user.backchannel     -- adaptive interruption classification
  - session.usage        -- cumulative per-model usage breakdown
  - agent.speech_interrupted -- barge-in events

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
    LlmAvailabilityChanged,
    SessionUsage,
    ToolExecuted,
    TurnCompleted,
    TurnDetected,
    TurnMetrics,
    UserBackchannel,
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
    """Per-turn latency breakdown -- covers ALL pipeline metrics.

    Fields organized by metrics class:
    - ChatMessage.metrics: user_perceived_ms, sdk_llm_ttft_ms, sdk_tts_ttfb_ms,
      sdk_transcription_delay_ms, sdk_end_of_turn_delay_ms,
      sdk_turn_completed_callback_ms, sdk_started/stopped_speaking_at
    - LLMMetrics: llm_ttft_ms, llm_duration_ms, llm_cancelled, llm_prompt_tokens,
      llm_completion_tokens, llm_total_tokens, llm_tokens_per_second,
      llm_cache_read_tokens, llm_cache_hit_ratio, llm_model, llm_provider,
      llm_label, llm_request_id, llm_speech_id, llm_timestamp
    - STTMetrics: stt_delay_ms, stt_duration_ms, stt_audio_duration_ms,
      stt_streamed, stt_input_tokens, stt_output_tokens, stt_model,
      stt_provider, stt_confidence, stt_label, stt_request_id, stt_timestamp
    - TTSMetrics: tts_ttfb_ms, tts_duration_ms, tts_audio_duration_ms,
      tts_cancelled, tts_characters, tts_streamed, tts_input_tokens,
      tts_output_tokens, tts_model, tts_provider, tts_label, tts_request_id,
      tts_timestamp, tts_speech_id, tts_segment_id
    - VADMetrics: vad_idle_time_s, vad_inference_count,
      vad_inference_duration_total_ms, vad_label
    - Turn detection: turn_decision_ms, turn_method, turn_probability,
      turn_unlikely_threshold, eou_speech_id, turn_completed_callback_ms
    - InterruptionMetrics: interruption_total_duration_ms,
      interruption_prediction_ms, interruption_detection_delay_ms,
      num_interruptions, num_backchannels, interruption_num_requests
    - RealtimeModelMetrics: realtime_ttft_ms, realtime_duration_ms,
      realtime_session_duration_ms, realtime_cancelled, realtime_input_tokens,
      realtime_output_tokens, realtime_total_tokens, realtime_tokens_per_second,
      realtime_label, realtime_request_id, realtime_model, realtime_provider,
      + all token detail breakdowns (audio/text/image/cached)
    """
    perceived = event.user_perceived_ms or 0
    stt = event.stt_delay_ms or 0
    turn = event.turn_decision_ms or 0
    llm = event.llm_ttft_ms or 0
    tts = event.tts_ttfb_ms or 0

    print(f"\n{'='*60}")
    print(f"  TURN {event.turn_number} METRICS {'(interrupted)' if event.interrupted else ''}")
    if event.agent_first:
        print("  [agent-first turn]")
    if event.pipeline:
        print(f"  Pipeline: {event.pipeline}")
    print(f"{'='*60}")

    # --- ChatMessage.metrics (SDK-measured latency) ---
    print(f"  User perceived latency:  {perceived}ms")
    if event.sdk_llm_ttft_ms is not None:
        print(f"  SDK LLM TTFT:            {event.sdk_llm_ttft_ms}ms")
    if event.sdk_tts_ttfb_ms is not None:
        print(f"  SDK TTS TTFB:            {event.sdk_tts_ttfb_ms}ms")
    if event.sdk_transcription_delay_ms is not None:
        print(f"  SDK transcription delay: {event.sdk_transcription_delay_ms}ms")
    if event.sdk_end_of_turn_delay_ms is not None:
        print(f"  SDK end-of-turn delay:   {event.sdk_end_of_turn_delay_ms}ms")
    if event.sdk_turn_completed_callback_ms is not None:
        print(f"  SDK turn callback:       {event.sdk_turn_completed_callback_ms}ms")

    # --- Server-measured latency chain ---
    print("\n  Server latency chain:")
    print(f"  +- STT delay:            {stt}ms")
    print(f"  +- Turn decision:        {turn}ms")
    print(f"  +- LLM TTFT:             {llm}ms")
    print(f"  +- TTS pipeline:         {tts}ms")
    # Latency budget breakdown
    if perceived > 0:
        print("\n  Budget breakdown:")
        print(f"    STT:  {stt/perceived*100:5.1f}%")
        print(f"    Turn: {turn/perceived*100:5.1f}%")
        print(f"    LLM:  {llm/perceived*100:5.1f}%")
        print(f"    TTS:  {tts/perceived*100:5.1f}%")

    # --- Turn detection ---
    print(f"\n  Turn method:     {event.turn_method or 'n/a'}")
    if event.turn_probability is not None:
        print(f"  Turn confidence: {event.turn_probability:.2f}")
    if event.turn_unlikely_threshold is not None:
        print(f"  Unlikely thresh: {event.turn_unlikely_threshold:.2f}")
    if event.eou_speech_id:
        print(f"  Turn speech ID:  {event.eou_speech_id}")
    if event.turn_completed_callback_ms is not None:
        print(f"  Turn callback:   {event.turn_completed_callback_ms}ms")

    # --- Dynamic endpointing ---
    if event.endpointing_min_delay_ms is not None:
        print("\n  Endpointing EMA:")
        print(f"    Min delay:     {event.endpointing_min_delay_ms}ms")
        print(f"    Max delay:     {event.endpointing_max_delay_ms}ms")

    # --- VADMetrics ---
    if event.vad_inference_count is not None:
        print("\n  VAD stats:")
        print(f"    Idle time:     {event.vad_idle_time_s}s")
        print(f"    Inferences:    {event.vad_inference_count}")
        print(f"    Total duration:{event.vad_inference_duration_total_ms}ms")
        if event.vad_label:
            print(f"    Label:         {event.vad_label}")

    # --- LLMMetrics ---
    if event.llm_model:
        print(f"\n  LLM ({event.llm_provider}/{event.llm_model}):")
        print(
            f"    Tokens:        "
            f"{event.llm_prompt_tokens or 0}p / {event.llm_completion_tokens or 0}c"
            f" ({event.llm_total_tokens or 0} total)"
        )
        if event.llm_tokens_per_second:
            print(f"    Throughput:    {event.llm_tokens_per_second:.1f} tok/s")
        if event.llm_cache_read_tokens:
            print(f"    Cache read:    {event.llm_cache_read_tokens}")
        if event.llm_cache_hit_ratio:
            print(f"    Cache ratio:   {event.llm_cache_hit_ratio:.2f}")
        if event.llm_duration_ms:
            print(f"    Duration:      {event.llm_duration_ms}ms")
        if event.llm_cancelled:
            print("    [CANCELLED]")
        if event.llm_label:
            print(f"    Label:         {event.llm_label}")
        if event.llm_request_id:
            print(f"    Request ID:    {event.llm_request_id}")
        if event.llm_speech_id:
            print(f"    Speech ID:     {event.llm_speech_id}")

    # --- STTMetrics ---
    if event.stt_provider:
        print(f"\n  STT ({event.stt_provider}/{event.stt_model or '?'}):")
        if event.stt_duration_ms:
            print(f"    Duration:      {event.stt_duration_ms}ms")
        if event.stt_audio_duration_ms:
            print(f"    Audio:         {event.stt_audio_duration_ms}ms")
        if event.stt_confidence is not None:
            print(f"    Confidence:    {event.stt_confidence:.2f}")
        if event.stt_streamed is not None:
            print(f"    Streamed:      {event.stt_streamed}")
        if event.stt_input_tokens:
            print(f"    Tokens:        {event.stt_input_tokens}in / {event.stt_output_tokens}out")
        if event.stt_label:
            print(f"    Label:         {event.stt_label}")
        if event.stt_request_id:
            print(f"    Request ID:    {event.stt_request_id}")

    # --- TTSMetrics ---
    if event.tts_provider:
        print(f"\n  TTS ({event.tts_provider}/{event.tts_model or '?'}):")
        if event.tts_ttfb_ms:
            print(f"    TTFB:          {event.tts_ttfb_ms}ms")
        if event.tts_duration_ms:
            print(f"    Duration:      {event.tts_duration_ms}ms")
        if event.tts_characters:
            print(f"    Characters:    {event.tts_characters}")
        if event.tts_audio_duration_ms:
            print(f"    Audio:         {event.tts_audio_duration_ms}ms")
        if event.tts_cancelled:
            print("    [CANCELLED]")
        if event.tts_streamed is not None:
            print(f"    Streamed:      {event.tts_streamed}")
        if event.tts_input_tokens:
            print(f"    Tokens:        {event.tts_input_tokens}in / {event.tts_output_tokens}out")
        if event.tts_label:
            print(f"    Label:         {event.tts_label}")
        if event.tts_request_id:
            print(f"    Request ID:    {event.tts_request_id}")
        if event.tts_speech_id:
            print(f"    Speech ID:     {event.tts_speech_id}")
        if event.tts_segment_id:
            print(f"    Segment ID:    {event.tts_segment_id}")

    # --- InterruptionMetrics ---
    if event.num_interruptions or event.interruption_total_duration_ms:
        print("\n  Interruption stats:")
        if event.interruption_total_duration_ms:
            print(f"    Total:         {event.interruption_total_duration_ms}ms")
        if event.interruption_prediction_ms:
            print(f"    Prediction:    {event.interruption_prediction_ms}ms")
        if event.interruption_detection_delay_ms:
            print(f"    Detection:     {event.interruption_detection_delay_ms}ms")
        if event.num_interruptions:
            print(f"    Count:         {event.num_interruptions}")
        if event.num_backchannels:
            print(f"    Backchannels:  {event.num_backchannels}")
        if event.interruption_num_requests:
            print(f"    ML requests:   {event.interruption_num_requests}")

    # --- RealtimeModelMetrics (S2S) ---
    if event.realtime_model:
        print(f"\n  Realtime ({event.realtime_provider}/{event.realtime_model}):")
        print(f"    TTFT:          {event.realtime_ttft_ms}ms")
        if event.realtime_duration_ms:
            print(f"    Duration:      {event.realtime_duration_ms}ms")
        if event.realtime_session_duration_ms:
            print(f"    Session:       {event.realtime_session_duration_ms}ms")
        if event.realtime_cancelled:
            print("    [CANCELLED]")
        print(
            f"    Tokens:        {event.realtime_input_tokens or 0}in"
            f" / {event.realtime_output_tokens or 0}out"
            f" ({event.realtime_total_tokens or 0} total)"
        )
        if event.realtime_tokens_per_second:
            print(f"    Throughput:    {event.realtime_tokens_per_second:.1f} tok/s")
        if event.realtime_cache_hit_ratio:
            print(f"    Cache ratio:   {event.realtime_cache_hit_ratio:.2f}")
        # Token breakdowns
        if event.realtime_input_audio_tokens:
            print(
                f"    Audio tokens:  {event.realtime_input_audio_tokens}in"
                f" / {event.realtime_output_audio_tokens}out"
            )
        if event.realtime_input_text_tokens:
            print(
                f"    Text tokens:   {event.realtime_input_text_tokens}in"
                f" / {event.realtime_output_text_tokens}out"
            )
        if event.realtime_input_image_tokens:
            print(
                f"    Image tokens:  {event.realtime_input_image_tokens}in"
                f" / {event.realtime_output_image_tokens}out"
            )
        if event.realtime_cached_tokens:
            print(f"    Cached total:  {event.realtime_cached_tokens}")
            if event.realtime_cached_audio_tokens:
                print(f"    Cached audio:  {event.realtime_cached_audio_tokens}")
            if event.realtime_cached_text_tokens:
                print(f"    Cached text:   {event.realtime_cached_text_tokens}")

    # --- Wall-clock timestamps ---
    if event.user_started_speaking_at:
        print("\n  Timestamps:")
        print(f"    User started:  {event.user_started_speaking_at}")
        print(f"    User stopped:  {event.user_stopped_speaking_at}")
        print(f"    Agent started: {event.agent_started_speaking_at}")
        print(f"    Agent stopped: {event.agent_stopped_speaking_at}")

    # --- Other ---
    if event.speaking_rate:
        print(f"\n  Speaking rate:   {event.speaking_rate:.1f} words/s")
    if event.error_source:
        print(f"  Error source:    {event.error_source}")

    print(f"{'='*60}\n")


@app.on("turn.completed")
def on_turn(session, event: TurnCompleted):
    """Turn completed with per-turn latency highlights."""
    prefix = "[agent-first] " if event.agent_first else ""
    print(f"  {prefix}Turn {event.turn_number}:")
    print(f"    User:  {event.user_text}")
    print(f"    Agent: {event.agent_text}")
    # Per-turn latency highlights (seconds)
    latencies = []
    if event.transcription_delay_s is not None:
        latencies.append(f"stt={event.transcription_delay_s:.3f}s")
    if event.turn_decision_s is not None:
        latencies.append(f"turn={event.turn_decision_s:.3f}s")
    if event.llm_ttft_s is not None:
        latencies.append(f"llm={event.llm_ttft_s:.3f}s")
    if event.tts_ttfb_s is not None:
        latencies.append(f"tts={event.tts_ttfb_s:.3f}s")
    if event.realtime_ttft_s is not None:
        latencies.append(f"realtime={event.realtime_ttft_s:.3f}s")
    if latencies:
        print(f"    Latency: {' '.join(latencies)}")


@app.on("user.turn_completed")
def on_turn_detected(session, event: TurnDetected):
    """Turn end detected by the turn detector."""
    print(f"  Turn detected: trigger={event.trigger} duration={event.duration_ms}ms")


@app.on("user.speech_started")
def on_vad_start(session, event: VadSpeechStarted):
    """VAD speech onset -- includes inference stats."""
    parts = [f"at {event.timestamp_ms}ms"]
    if event.vad_idle_time_s is not None:
        parts.append(f"idle={event.vad_idle_time_s:.1f}s")
    if event.vad_inference_count is not None:
        parts.append(f"inferences={event.vad_inference_count}")
    if event.vad_inference_duration_total_ms is not None:
        parts.append(f"duration={event.vad_inference_duration_total_ms}ms")
    print(f"  VAD started: {' '.join(parts)}")


@app.on("user.speech_stopped")
def on_vad_stop(session, event: VadSpeechStopped):
    """VAD speech offset -- includes inference stats."""
    parts = [f"at {event.timestamp_ms}ms", f"spoke={event.duration_ms}ms"]
    if event.vad_inference_count is not None:
        parts.append(f"inferences={event.vad_inference_count}")
    if event.vad_inference_duration_total_ms is not None:
        parts.append(f"duration={event.vad_inference_duration_total_ms}ms")
    print(f"  VAD stopped: {' '.join(parts)}")


@app.on("user.idle")
def on_user_idle(session, event: UserIdle):
    print(f"  User idle: retry={event.retry_count}, reason={event.reason}")


@app.on("user.backchannel")
def on_backchannel(session, event: UserBackchannel):
    """Overlapping speech classified as backchannel or real interruption."""
    label = "INTERRUPTION" if event.is_interruption else "backchannel"
    parts = [label]
    if event.probability is not None:
        parts.append(f"prob={event.probability:.2f}")
    if event.detection_delay_ms is not None:
        parts.append(f"delay={event.detection_delay_ms:.0f}ms")
    if event.total_duration_ms is not None:
        parts.append(f"duration={event.total_duration_ms:.0f}ms")
    if event.num_requests is not None:
        parts.append(f"requests={event.num_requests}")
    print(f"  Backchannel: {' '.join(parts)}")


@app.on("session.usage")
def on_usage(session, event: SessionUsage):
    """Cumulative session usage -- per-model token/character/audio breakdown."""
    if not event.models:
        return
    parts = []
    for m in event.models:
        t = m.get("type", "")
        provider = m.get("provider", "?")
        model = m.get("model", "?")
        if t == "llm_usage":
            cached = m.get("input_cached_tokens", 0)
            parts.append(
                f"LLM({provider}/{model}): "
                f"{m.get('input_tokens', 0)}in/{m.get('output_tokens', 0)}out "
                f"cached={cached}"
            )
        elif t == "tts_usage":
            parts.append(
                f"TTS({provider}/{model}): "
                f"{m.get('characters_count', 0)} chars, "
                f"{m.get('audio_duration', 0):.1f}s"
            )
        elif t == "stt_usage":
            parts.append(
                f"STT({provider}/{model}): {m.get('audio_duration', 0):.1f}s"
            )
        elif t == "interruption_usage":
            parts.append(
                f"Interruption({provider}): {m.get('total_requests', 0)} reqs"
            )
    if parts:
        print(f"  Usage: {' | '.join(parts)}")


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


@app.on("tool.executed")
def on_tool_executed(session, event: ToolExecuted):
    """Tool call results -- shows what tools were called and their outputs."""
    for call in event.calls:
        output = call.get("output", "")
        is_error = call.get("is_error", False)
        status = "ERROR" if is_error else "ok"
        print(
            f"  Tool executed: {call['name']}({call.get('arguments', '')}) "
            f"[{status}] {output[:100]}"
        )


@app.on("llm.availability_changed")
def on_llm_availability(session, event: LlmAvailabilityChanged):
    status = "available" if event.available else "UNAVAILABLE"
    print(f"  LLM availability: {event.llm} -> {status}")


@app.on("session.error")
def on_error(session, event):
    print(f"  Error [{event.code}]: {event.message}")


@app.on("session.ended")
def on_ended(session, event: AgentSessionEnded):
    print(f"\nSession ended: {event.duration_seconds}s, {event.turn_count} turns")


if __name__ == "__main__":
    asyncio.run(init_agent())
    app.run(port=9000)
