# CLAUDE.md — plivo-agentstack-python

## Project overview

Async-first Python SDK for Plivo (`plivo_agentstack`). Covers Voice AI Agents (WebSocket + REST), Messaging (SMS/MMS/WhatsApp), and Numbers. Python 3.10+, built with `hatchling`.

## Repository layout

```
src/plivo_agentstack/
  __init__.py          # Public exports: AsyncClient, errors
  client.py            # AsyncClient entry point
  _http.py             # HttpTransport — retry, auth, error mapping
  errors.py            # PlivoError hierarchy
  types.py             # Shared models
  utils.py             # Webhook signature validation (v3)
  agent/               # Voice AI Agent stack
    app.py             # VoiceApp WebSocket server
    client.py          # Agent REST client (agents, calls, numbers, sessions) + semantic_vad presets
    events.py          # 38 typed event dataclasses + parse_event()
    session.py         # Per-connection Session handle
    tools.py           # Prebuilt tools: EndCall, SendDtmf, WarmTransfer, Collect* agent tools
  messaging/           # SMS/MMS/WhatsApp
    client.py          # MessagesClient
    templates.py       # WhatsApp Template builder
    interactive.py     # InteractiveMessage + Location builders
  numbers/             # Phone number management
    client.py          # NumbersClient + LookupResource
tests/                 # pytest + pytest-asyncio + respx
examples/              # 18 runnable scripts
```

## Build & run

```bash
pip install -e ".[dev]"       # install in dev mode
pytest tests/ -v              # run all tests (~87)
ruff check src/ tests/        # lint
```

## Code conventions

- **Async-first**: all I/O uses `async/await` via `httpx.AsyncClient`
- **Type hints**: use Python 3.10+ syntax (`dict | None`, `list[str]`, not `Optional`/`List`)
- **Dataclasses**: for all typed events and models — no Pydantic
- **Line length**: 100 characters max (ruff enforced)
- **Imports**: `from __future__ import annotations` first, then stdlib → third-party → project. Use `ruff check --select I` to verify ordering
- **Naming**: PascalCase classes, snake_case functions, UPPER_SNAKE constants, underscore prefix for private (`_http`, `_handlers`)
- **Ruff rules**: E, F, I, W only — keep it minimal
- **No bare `except`**: always catch specific exceptions
- **asyncio_mode = "auto"**: all async test functions run without explicit markers

## Event type strings

All WebSocket events use dotted naming convention:

| Event | Type string | Dataclass |
|---|---|---|
| Session started | `session.started` | `AgentSessionStarted` |
| Session ended | `session.ended` | `AgentSessionEnded` |
| Session error | `session.error` | `Error` |
| Tool called | `tool.called` | `ToolCall` |
| Tool executed (MCP) | `tool.executed` | `ToolExecuted` |
| Turn completed | `turn.completed` | `TurnCompleted` |
| Turn metrics | `turn.metrics` | `TurnMetrics` |
| User transcription | `user.transcription` | `Prompt` |
| User DTMF | `user.dtmf` | `Dtmf` |
| DTMF sent | `dtmf.sent` | `DtmfSent` |
| User idle | `user.idle` | `UserIdle` |
| User speech started | `user.speech_started` | `VadSpeechStarted` |
| User speech stopped | `user.speech_stopped` | `VadSpeechStopped` |
| User turn completed | `user.turn_completed` | `TurnDetected` |
| User state changed | `user.state_changed` | `UserStateChanged` |
| Agent handoff | `agent.handoff` | `AgentHandoff` |
| Agent speech interrupted | `agent.speech_interrupted` | `Interruption` |
| Agent speech created | `agent.speech_created` | `AgentSpeechCreated` |
| Agent speech started | `agent.speech_started` | `AgentSpeechStarted` |
| Agent speech completed | `agent.speech_completed` | `AgentSpeechCompleted` |
| Agent false interruption | `agent.false_interruption` | `AgentFalseInterruption` |
| Agent state changed | `agent.state_changed` | `AgentStateChanged` |
| Agent tool started | `agent_tool.started` | `AgentToolStarted` |
| Agent tool completed | `agent_tool.completed` | `AgentToolCompleted` |
| Agent tool failed | `agent_tool.failed` | `AgentToolFailed` |
| LLM availability | `llm.availability_changed` | `LlmAvailabilityChanged` |
| Voicemail detected | `voicemail.detected` | `VoicemailDetected` |
| Voicemail beep | `voicemail.beep` | `VoicemailBeep` |
| Participant added | `participant.added` | `ParticipantAdded` |
| Participant removed | `participant.removed` | `ParticipantRemoved` |
| Call transferred | `call.transferred` | `CallTransferred` |
| Play completed | `play.completed` | `PlayCompleted` |

Audio stream events use the Plivo protocol: `start`, `media`, `dtmf`, `playedStream`, `clearedAudio`, `stop`.

## Session methods

- **Managed mode**: `send_tool_result()`, `send_tool_error()`
- **Text mode (BYOLLM)**: `send_text()`, `extend_wait()`, `send_raw()`
- **Audio stream**: `send_media()`, `send_checkpoint()`, `clear_audio()`
- **Control**: `update()`, `inject()`, `handoff()`, `speak()`, `play()`, `transfer()`, `send_dtmf()`, `hangup()`
- **Background audio**: `play_background()`, `stop_background()`

## Prebuilt tools

Simple tools (customer-side): `EndCall`, `SendDtmf`, `WarmTransfer` — each has `.tool` (schema), `.instructions` (prompt hint), `.match(event)`, `.handle(session, event)`.

Agent tools (server-side sub-agents): `CollectEmail`, `CollectAddress`, `CollectPhone`, `CollectName`, `CollectDOB`, `CollectDigits`, `CollectCreditCard` — each has `.definition` (for `agent_tools=[]`), `.prompt_hint` (for system prompt).

## Supported providers

| Component | Providers |
|---|---|
| STT | deepgram, google, azure, assemblyai, groq, openai |
| LLM | openai, anthropic, groq, google, azure, together, fireworks, perplexity, mistral |
| TTS | elevenlabs, cartesia, google, azure, openai, deepgram |
| S2S | openai_realtime, gemini_live, azure_openai |

Provider names are case-insensitive. BYOK API keys are validated at agent creation time.

All provider configs (STT, LLM, TTS) accept optional `base_url` for custom endpoints. ElevenLabs TTS also accepts `region` (`"us"` default, `"in"` for India residency). Azure OpenAI uses `azure_deployment`, `azure_endpoint`, `api_version`.

## Semantic VAD

Agent creation supports `semantic_vad` as a string preset or dict:
- `"high"` / `"medium"` / `"low"` / `"auto"` — eagerness presets
- `{"eagerness": "high", "min_interruption_duration_ms": 200}` — preset + overrides
- Raw dict — full manual control

## Testing patterns

- **HTTP mocking**: use `respx` (not `unittest.mock` for HTTP). Fixture `mock_api` provides a router scoped to `https://api.plivo.com`
- **Fixtures**: `http_transport` and `client` fixtures in `conftest.py` — use `yield` for cleanup
- **Async tests**: just write `async def test_*` — pytest-asyncio auto mode handles it
- **Request verification**: use `mock_api.calls[0].request` to inspect sent requests
- **Error assertions**: `with pytest.raises(ErrorType)` and check `.status_code`, `.body`

## Key design decisions

- Sub-clients (`agent`, `messages`, `numbers`) are lazy-loaded properties on `AsyncClient`
- Session methods are sync-safe — they enqueue to an `asyncio.Queue`, sender task drains it
- VoiceApp auto-detects sync vs async handlers — sync runs in thread pool via `asyncio.to_thread()`
- Unknown WebSocket events parse to raw `dict` (forward-compatible)
- HttpTransport retries on 429 (respects `Retry-After`) and 5xx with exponential backoff
- Agent REST client auto-expands `semantic_vad` presets to full config dicts

## Git & commit rules

- **Do NOT include "Claude", "Anthropic", "AI-generated", "AI-assisted", or similar attribution in commit messages.** Write commit messages as if a human developer wrote the code.
- Keep commit messages concise (1-2 lines), focused on the "why" not the "what"
- Do not amend previous commits unless explicitly asked — always create new commits
- Do not force-push to main
- Do not commit `.env`, credentials, or API keys
- Do not commit `__pycache__/`, `.ruff_cache/`, `*.egg-info/`, `.venv/`, `dist/`, `build/` — these are in `.gitignore`

## Adding new features

- New REST resources: add to the appropriate sub-client (`agent/client.py`, `messaging/client.py`, `numbers/client.py`), wire into the parent client, add tests with `respx` mocks
- New WebSocket events: add a `@dataclass` to `agent/events.py`, register in `_EVENT_REGISTRY`, add parse test in `test_events.py`
- New prebuilt tools: add to `agent/tools.py`, export in `agent/__init__.py`
- New examples: add to `examples/`, use `from plivo_agentstack import AsyncClient` and `from plivo_agentstack.agent import VoiceApp, ...` pattern. Update README Quick start section
- Keep dependencies minimal — core deps are `httpx`, `websockets`, `starlette` only
