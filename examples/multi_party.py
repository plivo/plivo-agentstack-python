"""
Multi-Party Example -- Conference Calls with AI Agent

Config: stt + llm + tts, participant_mode="multi"

Uses Plivo Multi-Party Conferences (MPC) to support 3+ participants.
The AI agent joins as a conference participant alongside human callers.

Features demonstrated:
  - Multi-party agent creation (requires Plivo credentials)
  - Number assignment for inbound calls
  - Outbound call initiation (auto-joins MPC)
  - Adding participants mid-call via dial()
  - Warm transfer pattern (add human agent, AI drops)
  - Participant lifecycle events
  - DTMF send via LLM tool call (IVR navigation in MPC)

Providers:
  STT:  Deepgram Nova-3
  LLM:  OpenAI GPT-4o
  TTS:  ElevenLabs Flash v2.5

Usage:
  1. pip install plivo_agentstack[all]
  2. Set PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN env vars
  3. python multi_party.py
"""

import asyncio
import os

from plivo_agentstack import AsyncClient
from plivo_agentstack.agent import (
    AgentSessionEnded,
    AgentSessionStarted,
    Dtmf,
    DtmfSent,
    Interruption,
    ParticipantAdded,
    ParticipantRemoved,
    ToolCall,
    TurnCompleted,
    VoiceApp,
)

PLIVO_AUTH_ID = os.environ.get("PLIVO_AUTH_ID", "")
PLIVO_AUTH_TOKEN = os.environ.get("PLIVO_AUTH_TOKEN", "")
BASE_URL = os.environ.get("PLIVO_API_URL", "https://api.plivo.com")
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

# REST client -- used for agent CRUD and mid-call dial()
client = AsyncClient(PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN, base_url=BASE_URL)


# --- Tool definitions ---

SEND_DTMF_TOOL = {
    "name": "send_dtmf",
    "description": "Send DTMF digits on the call (e.g. to navigate an IVR menu)",
    "parameters": {
        "type": "object",
        "properties": {
            "digits": {
                "type": "string",
                "description": "DTMF digits to send (0-9, *, #)",
            },
        },
        "required": ["digits"],
    },
}

TRANSFER_TO_HUMAN_TOOL = {
    "name": "transfer_to_human",
    "description": "Add a human agent to the conference for a warm transfer",
    "parameters": {
        "type": "object",
        "properties": {
            "reason": {"type": "string", "description": "Reason for transfer"},
        },
        "required": ["reason"],
    },
}

ADD_PARTICIPANT_TOOL = {
    "name": "add_participant",
    "description": "Add another person to the conference call",
    "parameters": {
        "type": "object",
        "properties": {
            "number": {"type": "string", "description": "Phone number to dial"},
        },
        "required": ["number"],
    },
}

SYSTEM_PROMPT = (
    "You are a conference call moderator for Acme Corp. "
    "You can add participants to the call and transfer to human agents. "
    "Be concise -- this is a phone call."
)


# --- Agent setup ---


async def init_agent():
    """Create a multi-party agent.

    Multi-party mode uses Plivo MPC (Multi-Party Conferences). Requires:
      - plivo_auth_id: Your Plivo account auth ID
      - plivo_auth_token: Your Plivo account auth token
      - plivo_number: A Plivo number for caller ID on outbound legs
    """
    agent = await client.agent.agents.create(
        agent_name="Acme Conference Agent",
        participant_mode="multi",

        # Plivo credentials -- required for multi-party to manage MPC
        plivo_auth_id=PLIVO_AUTH_ID,
        plivo_auth_token=PLIVO_AUTH_TOKEN,
        plivo_number="+14155551234",       # caller ID for outbound dial legs

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
            "system_prompt": SYSTEM_PROMPT,
            "tools": [TRANSFER_TO_HUMAN_TOOL, ADD_PARTICIPANT_TOOL, SEND_DTMF_TOOL],
        },
        tts={
            # elevenlabs, cartesia, google, azure, openai, deepgram
            "provider": "elevenlabs", "voice": "EXAVITQu4vr4xnSDxMaL",
            "model": "eleven_flash_v2_5", "api_key": ELEVENLABS_API_KEY,
        },

        welcome_greeting="Welcome to the Acme conference line. How can I help?",
        websocket_url="ws://localhost:9000/ws",
        allow_interruptions=True,
    )
    agent_uuid = agent["agent_uuid"]
    print(f"Agent created: {agent_uuid}")

    # Assign a number so inbound calls auto-connect to this agent's MPC
    # await client.agent.numbers.assign(agent_uuid, "+14155551234")
    # print("Number assigned -- inbound calls join the conference")

    return agent


async def initiate_outbound_call(agent_uuid: str, to: str):
    """Start an outbound call -- auto-joins MPC since agent is multi-party."""
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


@app.on("session.started")
def on_started(session, event: AgentSessionStarted):
    print(f"Session started: {session.agent_session_id}")


@app.on("tool.called")
async def on_tool_call(session, event: ToolCall):
    print(f"  Tool call: {event.name}({event.arguments})")

    if event.name == "add_participant":
        # Dial a new participant into the conference mid-call.
        # The target is called and auto-joins the same MPC.
        number = event.arguments.get("number", "")
        await client.agent.calls.dial(
            session.call_uuid,
            targets=[{"number": number}],
        )
        session.send_tool_result(event.id, {"status": "dialing", "number": number})
        print(f"  Dialing {number} into conference")

    elif event.name == "transfer_to_human":
        # Warm transfer pattern:
        # 1. Add the human agent to the conference
        # 2. Brief the human agent (they hear the conversation)
        # 3. AI agent drops out, leaving human + caller
        session.speak("Let me connect you with a human agent. One moment.")
        await client.agent.calls.dial(
            session.call_uuid,
            targets=[{"number": "+18005551234"}],
        )
        session.send_tool_result(event.id, {"status": "transferring"})
        print("  Warm transfer: dialing human agent into conference")

    elif event.name == "send_dtmf":
        # Send DTMF digits on the agent's call leg.
        # In MPC mode, DTMF is sent from the agent's side -- useful for
        # navigating an IVR that was dialed into the conference.
        digits = event.arguments.get("digits", "")
        session.send_dtmf(digits)
        session.send_tool_result(event.id, {"status": "sent", "digits": digits})
        print(f"  Sending DTMF: {digits}")

    else:
        session.send_tool_error(event.id, f"Unknown tool: {event.name}")


@app.on("participant.added")
def on_participant_added(session, event: ParticipantAdded):
    """A new participant joined the conference."""
    print(
        f"  Participant joined: member={event.member_id} "
        f"role={event.role} target={event.target}"
    )

    # After human agent joins for warm transfer, AI can drop out
    if event.role == "agent":
        session.speak("I've connected you with a specialist. I'll leave you to it. Goodbye!")
        session.hangup()


@app.on("participant.removed")
def on_participant_removed(session, event: ParticipantRemoved):
    """A participant left the conference."""
    print(f"  Participant left: member={event.member_id} role={event.role}")


@app.on("turn.completed")
def on_turn(session, event: TurnCompleted):
    print(f"  User:  {event.user_text}")
    print(f"  Agent: {event.agent_text}")


@app.on("user.dtmf")
def on_dtmf(session, event: Dtmf):
    """DTMF digit received -- heard by all MPC participants."""
    print(f"  DTMF: {event.digit}")


@app.on("dtmf.sent")
def on_dtmf_sent(session, event: DtmfSent):
    """Confirmation that outbound DTMF was sent on the agent's call leg."""
    print(f"  DTMF sent: {event.digits}")


@app.on("agent.speech_interrupted")
def on_interruption(session, event: Interruption):
    print(f"  User interrupted: '{event.interrupted_text or ''}'")


@app.on("session.error")
def on_error(session, event):
    print(f"  Error [{event.code}]: {event.message}")


@app.on("session.ended")
def on_ended(session, event: AgentSessionEnded):
    print(f"Session ended: {event.duration_seconds}s, {event.turn_count} turns")


if __name__ == "__main__":
    asyncio.run(init_agent())
    app.run(port=9000)
