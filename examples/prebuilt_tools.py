"""
Prebuilt Tools Example -- Agent Tools + Simple Tools

Config: stt + llm + tts (full pipeline)

Demonstrates all prebuilt tools that ship with the SDK:

Agent tools (server-side sub-agents for multi-turn collection):
  - CollectEmail     -- Voice-optimized email collection
  - CollectAddress   -- Voice-optimized mailing address collection
  - CollectPhone     -- E.164 phone number collection
  - CollectName      -- First/last name collection
  - CollectDOB       -- Date of birth collection
  - CollectDigits    -- DTMF or spoken digit collection (PINs, account numbers)
  - CollectCreditCard -- Secure credit card detail collection

Simple tools (single-shot, customer-side):
  - EndCall         -- LLM-driven graceful call ending
  - SendDtmf        -- LLM sends DTMF tones (IVR navigation)
  - WarmTransfer     -- Transfer to human with hold message

Usage:
  1. pip install plivo_agentstack[all]
  2. Set PLIVO_AUTH_ID, DEEPGRAM_API_KEY, OPENAI_API_KEY, ELEVENLABS_API_KEY
  3. python prebuilt_tools.py
"""

import asyncio
import os

from plivo_agentstack import AsyncClient
from plivo_agentstack.agent import (
    AgentSessionEnded,
    AgentSessionStarted,
    AgentToolCompleted,
    AgentToolFailed,
    AgentToolStarted,
    CollectAddress,
    CollectCreditCard,
    CollectDigits,
    CollectDOB,
    CollectEmail,
    CollectName,
    CollectPhone,
    EndCall,
    SendDtmf,
    ToolCall,
    TurnCompleted,
    VoiceApp,
    WarmTransfer,
)

PLIVO_AUTH_ID = os.environ.get("PLIVO_AUTH_ID", "")
PLIVO_AUTH_TOKEN = os.environ.get("PLIVO_AUTH_TOKEN", "")
BASE_URL = os.environ.get("PLIVO_API_URL", "https://api.plivo.com")
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

client = AsyncClient(PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN, base_url=BASE_URL)


# --- Initialize tools ---

# Agent tools: server handles multi-turn collection automatically.
# Customer only receives agent_tool.started/completed events.
collect_email = CollectEmail()
collect_address = CollectAddress()
collect_phone = CollectPhone()
collect_name = CollectName(first_name=True, last_name=True)
collect_dob = CollectDOB()
collect_pin = CollectDigits(num_digits=4, label="PIN")
collect_card = CollectCreditCard()

# Customization examples:
# collect_email_custom = CollectEmail(
#     extra_instructions="Only accept company emails ending in @acme.com.",
#     on_enter_message="What is your company email address?",
#     timeout_s=90.0,
# )
# collect_name_full = CollectName(
#     first_name=True, middle_name=True, last_name=True, verify_spelling=True,
# )
# collect_dob_with_time = CollectDOB(include_time=True)

# Simple tools: customer handles tool calls directly.
end_call = EndCall(goodbye_message="Thanks for calling Acme Corp. Have a great day!")
send_dtmf = SendDtmf()
transfer = WarmTransfer(
    destination="+18005551234",
    hold_message="Connecting you now. One moment.",
)


# --- Build system prompt with agent tool hints ---

SYSTEM_PROMPT = (
    "You are a customer service agent for Acme Corp. "
    "You help customers with orders, account updates, and general inquiries.\n\n"
    f"{collect_email.prompt_hint}\n"
    f"{collect_address.prompt_hint}\n"
    f"{collect_phone.prompt_hint}\n"
    f"{collect_name.prompt_hint}\n"
    f"{collect_dob.prompt_hint}\n"
    f"{collect_pin.prompt_hint}\n"
    f"{collect_card.prompt_hint}\n\n"
    f"{transfer.instructions}\n\n"
    f"{end_call.instructions}"
)


async def init_agent():
    """Create an agent with agent tools and simple tools."""
    agent = await client.agent.agents.create(
        agent_name="Prebuilt Tools Demo",
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
            "tools": [
                end_call.tool,
                send_dtmf.tool,
                transfer.tool,
            ],
        },
        tts={
            # elevenlabs, cartesia, google, azure, openai, deepgram
            "provider": "elevenlabs", "voice": "EXAVITQu4vr4xnSDxMaL",
            "model": "eleven_flash_v2_5", "api_key": ELEVENLABS_API_KEY,
        },
        agent_tools=[
            collect_email.definition,
            collect_address.definition,
            collect_phone.definition,
            collect_name.definition,
            collect_dob.definition,
            collect_pin.definition,
            collect_card.definition,
        ],
        welcome_greeting="Hi! Welcome to Acme Corp. How can I help you today?",
        websocket_url="ws://localhost:9000/ws",
        allow_interruptions=True,
    )
    print(f"Agent created: {agent['agent_uuid']}")
    return agent


# --- Event handlers ---

app = VoiceApp()


@app.on("session.started")
def on_started(session, event: AgentSessionStarted):
    print(f"Session started: {session.agent_session_id}")


@app.on("agent_tool.started")
def on_agent_tool_started(session, event: AgentToolStarted):
    print(f"  Agent tool started: {event.agent_tool_type} ({event.agent_tool_id})")


@app.on("agent_tool.completed")
def on_agent_tool_completed(session, event: AgentToolCompleted):
    """Handle completed agent tools -- result contains collected data."""
    tool_type = event.agent_tool_type
    result = event.result
    print(f"  Agent tool completed: {tool_type} ({event.agent_tool_id})")

    if result.get("timed_out"):
        print("    Timed out")
        return

    if result.get("declined"):
        print(f"    Declined: {result.get('decline_reason', '')}")
        return

    if tool_type == "collect_email":
        print(f"    Email: {result.get('email_address')}")
    elif tool_type == "collect_address":
        print(f"    Address: {result.get('street_address')}, {result.get('locality')}")
    elif tool_type == "collect_phone":
        print(f"    Phone: {result.get('phone_number')}")
    elif tool_type == "collect_name":
        print(f"    Name: {result.get('first_name')} {result.get('last_name')}")
    elif tool_type == "collect_dob":
        print(f"    DOB: {result.get('date_of_birth')}")
    elif tool_type == "collect_digits":
        print(f"    Digits: {result.get('digits')}")
    elif tool_type == "collect_credit_card":
        print(
            f"    Card: {result.get('issuer')} "
            f"****{result.get('card_number', '')[-4:]}, "
            f"exp {result.get('expiration_date')}"
        )


@app.on("agent_tool.failed")
def on_agent_tool_failed(session, event: AgentToolFailed):
    print(f"  Agent tool failed: {event.agent_tool_type} -- {event.error}")


@app.on("tool.called")
def on_tool_call(session, event: ToolCall):
    """Route simple tool calls to their handlers."""

    if end_call.match(event):
        reason = end_call.handle(session, event)
        print(f"  Call ending: {reason}")

    elif send_dtmf.match(event):
        digits = send_dtmf.handle(session, event)
        print(f"  DTMF sent: {digits}")

    elif transfer.match(event):
        reason = transfer.handle(session, event)
        print(f"  Transferring: {reason}")

    else:
        session.send_tool_error(event.id, f"Unknown tool: {event.name}")
        print(f"  Unknown tool: {event.name}")


@app.on("turn.completed")
def on_turn(session, event: TurnCompleted):
    print(f"  User:  {event.user_text}")
    print(f"  Agent: {event.agent_text}")


@app.on("session.ended")
def on_ended(session, event: AgentSessionEnded):
    print(f"Session ended: {event.duration_seconds}s, {event.turn_count} turns")


if __name__ == "__main__":
    asyncio.run(init_agent())
    app.run(port=9000)
