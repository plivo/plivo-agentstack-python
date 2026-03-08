"""
Multi-Party Example — Conference Calls with AI Agent

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

Providers:
  STT:  Deepgram Nova-3
  LLM:  OpenAI GPT-4.1-mini
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

# REST client — used for agent CRUD and mid-call dial()
client = AsyncClient(PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN, base_url=BASE_URL)


# --- Tool definitions ---

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
    "Be concise — this is a phone call."
)


# --- Agent setup ---


async def init_agent():
    """Create a multi-party agent."""
    agent = await client.agent.agents.create(
        agent_name="Acme Conference Agent",
        participant_mode="multi",
        plivo_auth_id=PLIVO_AUTH_ID,
        plivo_auth_token=PLIVO_AUTH_TOKEN,
        plivo_number="+14155551234",
        stt={
            "provider": "deepgram", "model": "nova-3",
            "language": "en", "api_key": DEEPGRAM_API_KEY,
        },
        llm={
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "api_key": OPENAI_API_KEY,
            "system_prompt": SYSTEM_PROMPT,
            "tools": [TRANSFER_TO_HUMAN_TOOL, ADD_PARTICIPANT_TOOL],
        },
        tts={
            "provider": "elevenlabs", "voice": "sarah",
            "model": "eleven_flash_v2_5", "api_key": ELEVENLABS_API_KEY,
        },
        welcome_greeting="Welcome to the Acme conference line. How can I help?",
        websocket_url="ws://localhost:9000/ws",
        interruption_enabled=True,
    )
    agent_uuid = agent["agent_uuid"]
    print(f"Agent created: {agent_uuid}")
    return agent


async def initiate_outbound_call(agent_uuid: str, to: str):
    """Start an outbound call — auto-joins MPC since agent is multi-party."""
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


@app.on("tool_call")
async def on_tool_call(session, event: ToolCall):
    print(f"  Tool call: {event.name}({event.arguments})")

    if event.name == "add_participant":
        number = event.arguments.get("number", "")
        await client.agent.calls.dial(
            session.call_uuid,
            targets=[{"number": number}],
        )
        session.send_tool_result(event.id, {"status": "dialing", "number": number})
        print(f"  Dialing {number} into conference")

    elif event.name == "transfer_to_human":
        session.speak("Let me connect you with a human agent. One moment.")
        await client.agent.calls.dial(
            session.call_uuid,
            targets=[{"number": "+18005551234"}],
        )
        session.send_tool_result(event.id, {"status": "transferring"})

    else:
        session.send_tool_error(event.id, f"Unknown tool: {event.name}")


@app.on("participant.added")
def on_participant_added(session, event: ParticipantAdded):
    print(f"  Participant joined: member={event.member_id} role={event.role} target={event.target}")
    if event.role == "agent":
        session.speak("I've connected you with a specialist. I'll leave you to it. Goodbye!")
        session.hangup()


@app.on("participant.removed")
def on_participant_removed(session, event: ParticipantRemoved):
    print(f"  Participant left: member={event.member_id} role={event.role}")


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


if __name__ == "__main__":
    asyncio.run(init_agent())
    app.run(port=9000)
