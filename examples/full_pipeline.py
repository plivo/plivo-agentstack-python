"""
Full Pipeline Example — Customer Support Agent with Model Switching

Config: stt + llm + tts (Plivo runs the full AI pipeline)

Your code only handles:
  - Tool calls (e.g. order lookup, transfers, escalation)
  - Flow control (update, inject, speak, play, hangup)

Features demonstrated:
  - VoiceApp server pattern (Plivo connects to you)
  - Agent tools: server-side sub-agents for data collection (CollectEmail)
  - Mid-call model switching (fast -> powerful on escalation)
  - Transfer with parallel/sequential hunt
  - Outbound calls with async voicemail detection
  - Pre-recorded audio playback (agent_session.play)
  - Per-turn latency metrics (turn.metrics)
  - DTMF receive (caller keypresses) and send (IVR navigation)

TTS streaming:
  All speech -- welcome_greeting, speak(), and LLM responses -- is streamed
  through TTS by default. Audio chunks are sent to the caller as they're
  synthesized, not buffered until complete. This minimizes time-to-first-byte.

Providers:
  STT:  Deepgram Nova-3
  LLM:  OpenAI GPT-4o (conversation) / GPT-4o (escalation)
  TTS:  ElevenLabs Flash v2.5 (voice: Sarah)

Usage:
  1. pip install plivo_agentstack[all]
  2. Set PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN env vars
  3. python full_pipeline.py
  4. In a separate terminal: uvicorn callback_server:app --port 9001
"""

import asyncio
import os

from plivo_agentstack import AsyncClient
from plivo_agentstack.agent import (
    AgentHandoff,
    AgentSessionEnded,
    AgentSessionStarted,
    AgentSpeechCompleted,
    AgentSpeechCreated,
    AgentSpeechStarted,
    AgentStateChanged,
    AgentToolCompleted,
    AgentToolFailed,
    CollectEmail,
    Dtmf,
    DtmfSent,
    EndCall,
    Interruption,
    PlayCompleted,
    ToolCall,
    TurnCompleted,
    TurnMetrics,
    UserIdle,
    UserStateChanged,
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

# Async REST client -- kept alive for mid-call operations (dial, transfer, etc.)
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

# --- Agent tools (server-side sub-agents) ---
# These run multi-turn collection dialogs server-side.
# The LLM sees them as regular tools but the server handles the sub-conversation.
collect_email = CollectEmail()
end_call = EndCall(goodbye_message="Thanks for calling Acme Corp. Goodbye!")

SYSTEM_PROMPT = (
    "You are a helpful customer support agent for Acme Corp. "
    "Be friendly, concise, and professional. When a customer "
    "asks about an order, use the lookup_order tool.\n\n"
    f"{collect_email.prompt_hint}\n"
    f"{end_call.instructions}"
)


# --- Agent setup (one-time, or pre-created via dashboard) ---


async def init_agent():
    """Create a full-pipeline agent (dual mode -- simple two-party call).

    Provider names and BYOK API keys are validated at creation time.
    Invalid provider names (e.g. "eleven_labs") or bad API keys are
    rejected immediately with a clear error -- no silent runtime failures.
    """
    agent = await client.agent.agents.create(
        agent_name="Acme Support Agent",

        # --- STT (Speech-to-Text) ----------------------------------------
        stt={
            "provider": "deepgram",         # deepgram (default), google, azure,
                                            # assemblyai, groq, openai
            "model": "nova-3",              # nova-3 (latest), nova-3-general, nova-3-meeting,
                                            # nova-3-phonecall, nova-2-general
            "language": "en",               # BCP 47: en, fr, es, de, pt, etc.
            "api_key": DEEPGRAM_API_KEY,    # BYOK -- omit to use platform key

            # Custom endpoint:
            # "base_url": "https://your-proxy.example.com/v1",  # custom Deepgram-compatible endpoint

            # Deepgram-specific options:
            # "encoding": "linear16",       # audio encoding (default: linear16 / PCM)
            # "sample_rate": 16000,         # audio sample rate (default: 16000)
            # "endpointing": 25,            # ms of silence before endpoint (default: 25)
            # "interim_results": True,       # stream partial transcriptions (default: true)
            # "smart_format": False,         # auto-format numbers/dates (default: false)
            # "punctuate": True,             # add punctuation (default: true)
            # "profanity_filter": False,     # filter profanity (default: false)
            # "no_delay": True,              # return results immediately (default: true)
            # "filler_words": True,          # include um/uh (default: true)
        },

        # --- LLM (Language Model) ----------------------------------------
        # If llm is set, both stt and tts must also be set.
        llm={
            "provider": "openai",           # openai (default), anthropic, groq, google, azure,
                                            # together, fireworks, perplexity, mistral
            "model": "gpt-4o",              # OpenAI: gpt-4.1-mini, gpt-4.1, gpt-4o, gpt-4o-mini,
                                            #         o1, o1-mini, o3, o3-mini, gpt-4-turbo
                                            # Anthropic: claude-sonnet-4-20250514, claude-haiku,
                                            #            claude-opus
                                            # Groq: llama-3.3-70b-versatile, mixtral-8x7b-32768
            "temperature": 0.2,             # 0.0-2.0 -- lower = more deterministic (default: 0.2)
            "api_key": OPENAI_API_KEY,      # BYOK -- omit to use platform key
            "system_prompt": SYSTEM_PROMPT,
            "tools": TOOLS + [end_call.tool],

            # Custom endpoint:
            # "base_url": "https://your-proxy.example.com/v1",  # custom OpenAI-compatible endpoint

            # Provider-specific options:
            # "max_tokens": 1024,           # max completion tokens (default: provider default)
            # "reasoning_effort": "low",    # o1/o3 models only: low, medium, high (default: low)
        },

        # --- TTS (Text-to-Speech) ----------------------------------------
        tts={
            "provider": "elevenlabs",       # elevenlabs (default), cartesia, google, azure,
                                            # openai, deepgram
            "voice": "EXAVITQu4vr4xnSDxMaL",  # Sarah -- see ElevenLabs voice library for IDs
                                            # Common voices: rachel, sarah, james, clyde, george
            "model": "eleven_flash_v2_5",   # eleven_flash_v2_5 (fast, recommended),
                                            # eleven_turbo_v2_5, eleven_turbo_v2,
                                            # eleven_monolingual_v1
            "api_key": ELEVENLABS_API_KEY,  # BYOK -- omit to use platform key

            # Regional endpoint (ElevenLabs):
            # "region": "in",              # "us" (default), "in" (India residency)
            # "base_url": "https://custom-endpoint.example.com/v1",  # override endpoint

            # ElevenLabs voice settings:
            "output_format": "pcm_16000",   # pcm_16000 (recommended), mp3_44100
            "stability": 0.5,              # 0.0 = expressive, 1.0 = stable (default: provider default)
            "similarity_boost": 0.75,      # voice consistency: 0.0-1.0 (default: provider default)
            # "style": 0.0,                # voice style expressiveness: 0.0-1.0
            # "use_speaker_boost": True,    # enhance speaker clarity
            # "speed": 1.0,                # speech speed: 0.1-4.0 (1.0 = normal)
            # "sample_rate": 16000,         # output sample rate in Hz

            # Cartesia-specific options (when provider="cartesia"):
            # "voice_id": "a0e99841-438c-4a64-b679-ae501e7d6091",
            # "model_id": "sonic-english",  # sonic-english (latest), sonic-multilingual
            # "output_format": "pcm_16000",
        },

        # --- Agent tools (server-side sub-agents) ---------------------------
        # Agent tools run multi-turn collection dialogs server-side.
        # The LLM calls the trigger tool -> server suspends the parent agent,
        # runs a focused sub-agent (ask -> validate -> read back -> confirm),
        # then resumes the parent with merged context.
        # Results arrive via "agent_tool.completed" WebSocket events.
        agent_tools=[
            collect_email.definition,
        ],

        # --- Semantic VAD (unified VAD + turn detection + interruption) -----
        # Controls speech detection, endpointing, and interruption behavior.
        #
        # Shorthand: "high", "medium", "low", "auto"
        #   semantic_vad="high"   -- fast turn-taking (150ms turn delay, 300ms barge-in)
        #   semantic_vad="medium" -- balanced (250ms turn delay, 500ms barge-in)
        #   semantic_vad="low"    -- conservative (500ms turn delay, 600ms barge-in)
        #
        # Dict with eagerness: preset + overrides
        #   semantic_vad={"eagerness": "high", "min_interruption_duration_ms": 200}
        #
        # Full manual control (all fields optional, server defaults apply):
        #   semantic_vad={
        #       "completed_turn_delay_ms": 150,        # delay when turn is complete
        #       "incomplete_turn_delay_ms": 800,        # delay when turn is incomplete
        #       "uncertain_turn_delay_ms": 800,         # delay when uncertain
        #       "min_interruption_duration_ms": 300,    # sustained speech before barge-in
        #       "false_interruption_timeout_ms": 800,   # PAUSE -> COMMIT/RESUME wait
        #       "completed_turn_threshold": 0.7,        # EOU probability for complete
        #       "incomplete_turn_threshold": 0.3,       # EOU probability for incomplete
        #   }
        semantic_vad="high",

        # --- Agent behavior -----------------------------------------------

        # welcome_greeting is streamed through TTS -- caller hears audio
        # as chunks are synthesized, not after the full text is rendered
        welcome_greeting="Hi there! Thanks for calling Acme Corp. How can I help you today?",
        websocket_url="ws://localhost:9000/ws",

        # Call start behavior
        speaks_first="agent",              # "agent" (default when welcome_greeting is set) or "user"
                                            # "agent": speak welcome_greeting immediately
                                            # "user": wait for user speech first; if no speech within
                                            #         wait_for_user_timeout_s, speak welcome_greeting
                                            #         as fallback (default timeout: 5s)
                                            # Default: "agent" when welcome_greeting is set,
                                            #          "user" when welcome_greeting is empty/absent
        # wait_for_user_timeout_s=5.0,     # seconds to wait for user speech when speaks_first="user"
                                            # 0 = never auto-speak (wait indefinitely)
                                            # default: 5.0 (range: 0-60)

        # User idle timeout -- detect prolonged silence after agent speaks
        # When the user goes silent mid-call, the agent can:
        #   1. Speak a reminder ("Are you still there?")
        #   2. Retry up to max_retries times
        #   3. Hang up with a goodbye message
        # If reminder_message is null/omitted, the LLM generates a contextual nudge.
        # The user can say "give me more time" -- the LLM calls the built-in
        # extend_wait tool, which extends the timer to extended_wait_time_s.
        idle_timeout={
            "no_response_timeout_s": 15,       # seconds of silence before first reminder (1-120)
            # "reminder_message": "Are you still there?",  # fixed text; omit for LLM-generated nudge
            "extended_wait_time_s": 30,         # seconds to wait after user asks for more time (1-300)
            "max_retries": 3,                   # reminder attempts before hangup (0-10)
            "hangup_message": "I haven't heard from you, so I'll end the call. Goodbye.",
        },

        # Prefill: start LLM generation while user is still speaking.
        # Reduces perceived latency at the cost of potentially wasted tokens.
        # prefill_cache=True,                    # default: true

        # Interruption (barge-in)
        allow_interruptions=True,          # allow user to interrupt agent (default: true)
        greeting_interruptible=True,       # allow interrupting welcome greeting
        greeting_interrupt_duration=0.5,   # seconds of AEC warmup

        # STT finalization strategy
        # send_on="turn_end",              # "turn_end" (wait for turn detector, default)
                                            # "speaking_stop" (as soon as VAD detects speech ended)

        # Voicemail/answering machine detection (agent-level setting)
        # detection_method="disabled",      # "disabled" (default), "audio" (fast energy analysis),
                                            # "llm" (transcript classification)

        # Tool call timeout -- how long to wait for customer tool_result.
        # Increase for tools that need human interaction (warm transfers).
        # Decrease for fast lookups. Changeable mid-call via session.update.
        # tool_call_timeout_s=30,           # seconds (default: 30, range: 1-300)

        # Audio settings
        # audio_format="pcm_16k",          # pcm_16k (default)
        # plc_enabled=False,               # packet loss concealment (default: false)
        # comfort_noise_enabled=True,       # comfort noise during silence (default: true)
        # cng_divisor=2800,                # comfort noise amplitude (default: 2800, higher = quieter)
        # noise_cancellation=False,         # client-side noise cancellation (default: false)

        # Background audio -- play ambient sound during calls
        # Built-in sounds: "office", "city-street", "crowded-room",
        #                   "call-center", "typing", "typing-short"
        # background_audio={
        #     "sound": "office",            # built-in sound name
        #     "volume": 0.3,                # 0.0-1.0 (0.3 = subtle background)
        #     "loop": True,                 # loop continuously (default: true)
        # },

        # Plivo Audio Streaming XML parameters
        # stream={
        #     "extra_headers": {"userId": "12345", "tenant": "acme"},
        #     "stream_timeout": 86400,
        #     "content_type": "audio/x-mulaw;rate=8000",
        #     "noise_cancellation": False,
        #     "noise_cancellation_level": 85,
        # },

        # Webhook callbacks
        callbacks={
            "hangup": {"url": f"{CALLBACK_HOST}/callbacks/hangup", "method": "POST"},
            "recording": {
                "url": f"{CALLBACK_HOST}/callbacks/recording",
                "method": "POST",
            },
        },

        # MCP (Model Context Protocol) servers -- see pipeline_mcp.py for full example.
        # mcp_servers=[{"type": "http", "url": "http://localhost:3001/mcp"}],
    )
    agent_uuid = agent["agent_uuid"]
    print(f"Agent created: {agent_uuid}")

    # --- Assign a phone number for inbound calls ---
    # await client.agent.numbers.assign(agent_uuid, "+14155551234")

    return agent


# --- Outbound calls ---


async def initiate_outbound_call(agent_uuid: str, to: str):
    """Initiate an outbound call.

    Voicemail/answering machine detection is an agent-level setting
    (detection_method on agent create/update), not per-call.
    When enabled, the call connects immediately and a "voicemail.detected"
    WS event arrives asynchronously once detection completes.
    """
    call = await client.agent.calls.initiate(
        agent_uuid=agent_uuid,
        from_="+14155551234",
        to=to,
        ring_timeout=30,
    )
    print(f"Outbound call: {call['call_uuid']}")
    return call


# --- Transfer helper ---


def connect_call_with_human(session):
    """Transfer the call to a human agent with a hold message.

    speak() is streamed through TTS -- the caller starts hearing audio
    immediately. The server plays the speak audio to completion before
    executing the transfer.
    """
    session.speak("Let me transfer you to a specialist. One moment please.")

    # Single destination
    session.transfer("+18005551234")

    # Parallel hunt -- ring all at once, first to answer wins
    # session.transfer(["+18005551234", "+18005559876"])

    # Sequential hunt -- try each number in order, 15s ring timeout each
    # session.transfer(
    #     ["+18005551234", "+18005559876"],
    #     dial_mode="sequential",
    #     timeout=15,
    # )


# --- Event handlers ---

app = VoiceApp()


@app.on("session.started")
def on_started(session, event: AgentSessionStarted):
    print(f"Session started: {session.agent_session_id}")

    # Enable per-turn latency metrics
    session.update(events={"metrics_events": True})

    # Opt-in to VAD/turn events (useful for debugging)
    # session.update(events={"vad_events": True, "turn_events": True})

    # Dynamic tool updates -- add or remove tools mid-call:
    # session.update(tools=[LOOKUP_ORDER_TOOL, TRANSFER_TOOL, NEW_TOOL])

    # Dynamic semantic_vad tuning -- can be changed mid-call:
    # session.update(semantic_vad={
    #     "speech_activation_threshold": 0.4,
    #     "min_interruption_words": 3,
    #     "min_interruption_duration_ms": 300,
    #     "false_interruption_timeout_ms": 800,
    # })


@app.on("agent_tool.completed")
def on_agent_tool_completed(session, event: AgentToolCompleted):
    """Handle completed agent tools -- result contains collected data.

    Agent tools run multi-turn dialogs server-side. The parent agent is
    suspended during collection and resumes automatically when done.
    """
    result = event.result
    print(f"  Agent tool completed: {event.agent_tool_type} ({event.agent_tool_id})")

    if result.get("timed_out"):
        print("    Timed out -- agent will handle gracefully")
    elif result.get("declined"):
        print(f"    User declined: {result.get('decline_reason', '')}")
    elif event.agent_tool_type == "collect_email":
        email = result.get("email_address")
        print(f"    Email collected: {email}")
        # TODO: save to your CRM, trigger follow-up, etc.


@app.on("agent_tool.failed")
def on_agent_tool_failed(session, event: AgentToolFailed):
    print(f"  Agent tool failed: {event.agent_tool_type} -- {event.error}")


@app.on("tool.called")
def on_tool_call(session, event: ToolCall):
    """Handle tool calls from the LLM.

    The pipeline supports parallel tool calls -- if the LLM emits multiple
    tool calls in one turn, each arrives as a separate event. Send results
    back independently; the pipeline collects all results before the next
    LLM turn.

    Note: Agent tools (like collect_email) are NOT routed here -- they are
    handled server-side and results arrive via agent_tool.completed events.
    """
    print(f"  Tool call: {event.name}({event.arguments})")

    if event.name == "lookup_order":
        result = lookup_order(event.arguments.get("order_id", ""))
        session.send_tool_result(event.id, result)

        # Context injection: feed external data into the conversation.
        # Unlike tool results (which the LLM requested), inject() adds
        # context the LLM didn't ask for -- customer history, account
        # details, RAG results, etc. The LLM sees it as background info.
        # session.inject("Customer account note: VIP customer since 2020, "
        #                "lifetime value $12,500. Prioritize retention.")

    elif event.name == "transfer_to_human":
        connect_call_with_human(session)

    elif event.name == "play_hold_music":
        # play() sends a pre-recorded WAV directly to the caller.
        # Unlike speak(), it bypasses TTS -- the audio is decoded, resampled
        # to 16kHz, and streamed as-is. Supports any PCM WAV sample rate.
        #
        # allow_interruption=False means user speech won't cut it short --
        # useful for hold music, legal disclaimers, or IVR prompts.
        session.play("hold_music.wav", allow_interruption=False)
        session.send_tool_result(event.id, {"status": "playing_hold_music"})
        print("  Playing hold music (non-interruptible)")

    elif event.name == "escalate":
        # Multi-agent handoff: switch persona, tools, and optionally model.
        # Conversation history is preserved -- the new agent sees all prior turns.
        # Inject a summary so the specialist has compact context without
        # re-reading the full conversation.
        reason = event.arguments.get("reason", "")
        session.speak("Let me connect you with a specialist. One moment please.")
        session.handoff(
            system_prompt=(
                "You are a senior support specialist at Acme Corp. "
                "You have access to refund and exchange tools. "
                "Be empathetic and resolve the issue."
            ),
            tools=[LOOKUP_ORDER_TOOL, TRANSFER_TOOL],
            llm={"model": "gpt-4o"},
            summary=f"Customer escalated: {reason}. Review conversation history above.",
        )
        session.send_tool_result(event.id, {"status": "escalated"})
        print(f"  Agent handoff: escalated to specialist -- {reason}")

    elif end_call.match(event):
        end_call.handle(session, event)
        print("  Call ending")

    else:
        session.send_tool_error(event.id, f"Unknown tool: {event.name}")


@app.on("voicemail.detected")
def on_voicemail(session, event: VoicemailDetected):
    """Handle async voicemail detection result.

    Arrives after the call connects when detection_method is set on the agent.
    The call is already live.

    If machine: pipeline automatically starts beep detection. Wait for
    the voicemail.beep event before speaking -- the greeting is still
    playing until the beep.
    """
    if event.result == "machine":
        print(f"  Machine detected -- waiting for beep: {session.call_uuid}")
    else:
        print(f"  Human answered: {session.call_uuid}")


@app.on("voicemail.beep")
def on_beep(session, event: VoicemailBeep):
    """Beep detected -- the voicemail greeting is done, start talking."""
    print(f"  Beep detected: freq={event.frequency_hz}Hz")
    session.speak("Hi, this is Acme Corp returning your call. Please call us back.")
    session.hangup()


@app.on("play.completed")
def on_play_completed(session, event: PlayCompleted):
    """Fired when agent_session.play finishes playing the audio."""
    print("  Play completed -- resuming conversation")
    session.speak("Thank you for waiting. I'm back.")


@app.on("agent.handoff")
def on_handoff(session, event: AgentHandoff):
    """Agent handoff detected -- session.update changed agent persona."""
    print(f"  Agent handoff: new agent = {event.new_agent}")


@app.on("user.idle")
def on_user_idle(session, event: UserIdle):
    """User has been silent after agent finished speaking."""
    print(f"  User idle: retry={event.retry_count}, reason={event.reason}")


@app.on("turn.metrics")
def on_metrics(session, event: TurnMetrics):
    """Per-turn latency metrics (opt-in via metrics_events=True)."""
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


@app.on("user.dtmf")
def on_dtmf(session, event: Dtmf):
    """DTMF digit received from the caller."""
    print(f"  DTMF: {event.digit}")
    if event.digit == "0":
        session.speak("Transferring you to an agent.")
        session.transfer("+18005551234")
    elif event.digit == "#":
        session.speak("Goodbye.")
        session.hangup()

    # Send DTMF outbound (e.g. navigate an IVR the agent dialed into):
    # session.send_dtmf("1")       # press 1
    # session.send_dtmf("123#")    # press sequence


@app.on("dtmf.sent")
def on_dtmf_sent(session, event: DtmfSent):
    """Confirmation that outbound DTMF was sent on the call."""
    print(f"  DTMF sent: {event.digits}")


@app.on("agent.speech_interrupted")
def on_interruption(session, event: Interruption):
    print(f"  User interrupted: '{event.interrupted_text or ''}'")


# --- State & lifecycle events (opt-in via events config) ---


@app.on("user.state_changed")
def on_user_state(session, event: UserStateChanged):
    """User state transitions: listening -> speaking -> listening -> away."""
    print(f"  User: {event.old_state} -> {event.new_state}")


@app.on("agent.state_changed")
def on_agent_state(session, event: AgentStateChanged):
    """Agent state transitions: listening -> thinking -> speaking -> listening."""
    print(f"  Agent: {event.old_state} -> {event.new_state}")


@app.on("agent.speech_created")
def on_speech_created(session, event: AgentSpeechCreated):
    """LLM started generating a response."""
    print(f"  Speech created: source={event.source} user_initiated={event.user_initiated}")


@app.on("agent.speech_started")
def on_speech_started(session, event: AgentSpeechStarted):
    """TTS audio started playing to the caller."""
    print("  Agent speaking")


@app.on("agent.speech_completed")
def on_speech_completed(session, event: AgentSpeechCompleted):
    """TTS audio finished playing."""
    print(f"  Agent finished speaking ({event.playback_position_s:.1f}s)")


@app.on("agent.false_interruption")
def on_false_interruption(session, event):
    """Brief speech during agent playback was classified as noise/echo."""
    print("  False interruption -- agent resumed")


@app.on("session.error")
def on_error(session, event):
    print(f"  Error [{event.code}]: {event.message}")


@app.on("session.ended")
def on_ended(session, event: AgentSessionEnded):
    print(
        f"Session ended: {event.duration_seconds}s, {event.turn_count} turns"
    )


@app.on_handler_error
def on_handler_error(session, event, exc):
    """Called when any handler raises an exception."""
    print(f"  Handler error: {exc}")


if __name__ == "__main__":
    asyncio.run(init_agent())
    app.run(port=9000)
