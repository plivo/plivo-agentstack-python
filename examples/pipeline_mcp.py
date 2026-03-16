"""
MCP Server Integration -- Voice Agent with External Tool Servers

Config: stt + llm + tts + mcp_servers

Demonstrates connecting MCP (Model Context Protocol) servers to a voice
agent. MCP servers provide tools that the LLM can call -- just like
regular tools defined in llm.tools, but hosted externally.

Two MCP server types:
  - HTTP: Connect to an MCP server over HTTP (SSE or streamable HTTP)
  - Stdio: Spawn an MCP server as a subprocess

MCP tools are discovered automatically at session start and added to
the LLM's tool list alongside any tools from llm.tools. Tool calls
are handled server-side -- results go directly to the LLM without
hitting the customer WebSocket.

Usage:
  1. Start an MCP server (see below)
  2. Set provider API keys as env vars
  3. pip install plivo_agentstack[all]
  4. python pipeline_mcp.py

Example MCP servers:
  # HTTP server (requires running MCP server):
  npx @anthropic-ai/mcp-server --port 3001

  # SQLite server (stdio, spawned by the agent):
  npx -y @modelcontextprotocol/server-sqlite /path/to/database.db
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
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

# MCP server URL (for HTTP type)
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:3001/mcp")

client = AsyncClient(PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN, base_url=BASE_URL)


# --- Regular tools (alongside MCP tools) ---

LOOKUP_ACCOUNT_TOOL = {
    "name": "lookup_account",
    "description": "Look up a customer account by phone number",
    "parameters": {
        "type": "object",
        "properties": {
            "phone": {"type": "string", "description": "Customer phone number"},
        },
        "required": ["phone"],
    },
}

SYSTEM_PROMPT = (
    "You are a helpful support agent. You have access to tools from "
    "both the platform and external MCP servers. Use them as needed "
    "to help customers. When looking up data, use the appropriate tool."
)


async def init_agent():
    """Create an agent with MCP server connections.

    MCP servers are initialized at session start. Their tools are
    discovered automatically and added to the LLM's available tools.
    If an MCP server fails to initialize, the session continues
    without those tools (logged as a warning).
    """
    agent = await client.agent.agents.create(
        agent_name="MCP-Enabled Agent",

        stt={
            "provider": "deepgram",             # deepgram, google, azure, assemblyai, groq, openai
            "model": "nova-3",
            "language": "en",
            "api_key": DEEPGRAM_API_KEY,
        },
        llm={
            "provider": "openai",               # openai, anthropic, groq, google, azure,
                                                # together, fireworks, perplexity, mistral
            "model": "gpt-4o",
            "temperature": 0.2,
            "api_key": OPENAI_API_KEY,
            "system_prompt": SYSTEM_PROMPT,
            "tools": [LOOKUP_ACCOUNT_TOOL],  # Regular tools work alongside MCP
        },
        tts={
            "provider": "elevenlabs",           # elevenlabs, cartesia, google, azure, openai, deepgram
            "voice": "EXAVITQu4vr4xnSDxMaL",
            "model": "eleven_flash_v2_5",
            "api_key": ELEVENLABS_API_KEY,
        },

        # --- MCP Servers ---
        # Tools from these servers are added to the LLM automatically.
        # MCP tool calls are handled server-side (not routed to customer WS).
        mcp_servers=[
            # HTTP MCP server -- connect to a running server
            {
                "type": "http",
                "url": MCP_SERVER_URL,
                # Optional: filter which tools to expose to the LLM
                # "allowed_tools": ["search_docs", "create_ticket"],
                # Optional: auth headers for the MCP server
                # "headers": {"Authorization": "Bearer sk-..."},
                # Optional: connection timeout (default: 5s)
                # "timeout": 10,
                # Optional: transport type ("sse" or "streamable_http")
                # "transport_type": "sse",
            },

            # Stdio MCP server -- spawned as a subprocess
            # Uncomment to use a local SQLite MCP server:
            # {
            #     "type": "stdio",
            #     "command": "npx",
            #     "args": ["-y", "@modelcontextprotocol/server-sqlite", "/tmp/test.db"],
            #     # Optional: environment variables for the subprocess
            #     # "env": {"NODE_ENV": "production"},
            #     # Optional: working directory
            #     # "cwd": "/path/to/project",
            # },
        ],

        welcome_greeting=(
            "Hello! I'm your support agent with extended tool access. How can I help?"
        ),
        websocket_url="ws://localhost:9000/ws",
        speaks_first="agent",
        allow_interruptions=True,
        semantic_vad={
            "completed_turn_delay_ms": 250,
            "incomplete_turn_delay_ms": 1200,
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
    """Handle regular tool calls (non-MCP).

    MCP tool calls are handled server-side -- they never reach this
    handler. Only tools defined in llm.tools arrive here.
    """
    print(f"  Tool call: {event.name}({event.arguments})")

    if event.name == "lookup_account":
        session.send_tool_result(event.id, {
            "name": "Jane Smith",
            "account_id": "ACC-12345",
            "status": "active",
        })
    else:
        session.send_tool_error(event.id, f"Unknown tool: {event.name}")


@app.on("turn.metrics")
def on_metrics(session, event: TurnMetrics):
    print(
        f"  Metrics [turn {event.turn_number}]: "
        f"perceived={event.user_perceived_ms}ms "
        f"llm_ttft={event.llm_ttft_ms}ms"
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
