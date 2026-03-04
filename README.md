# Plivo Agent Python SDK

[![PyPI version](https://img.shields.io/pypi/v/plivo_agent.svg)](https://pypi.org/project/plivo_agent/)
[![Python 3.10+](https://img.shields.io/pypi/pyversions/plivo_agent.svg)](https://pypi.org/project/plivo_agent/)
[![Tests](https://github.com/plivo/plivo-agent-python/actions/workflows/tests.yml/badge.svg)](https://github.com/plivo/plivo-agent-python/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/plivo/plivo-agent-python/branch/main/graph/badge.svg)](https://codecov.io/gh/plivo/plivo-agent-python)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Plivo Programmable Agents SDK - Build AI Agents that work over voice calls, SMS/WhatsApp programmatically.


## Agent pipeline modes

The SDK supports every Voice AI Agent configuration. Behavior is determined by which configs you provide when creating an agent -- there is no explicit `mode` field:

| Config provided | Pipeline | You handle |
|---|---|---|
| `stt` + `llm` + `tts` | **Full AI** - Plivo runs the entire voice agent pipeline | Tool calls and flow control |
| `stt` + `tts` | **BYOLLM** - Plivo handles speech, you bring your own LLM | LLM inference, stream tokens back via `send_text()` |
| `s2s` | **Speech-to-speech** - single provider handles STT+LLM+TTS natively | Event handling (OpenAI Realtime, Gemini Live) |
| _(none)_ | **Audio stream** - Plivo is a telephony bridge | You bring and orchestrate your own STT, LLM, TTS, VAD etc. |

### Call flow

```
Inbound/Outbound Call
        |
   Plivo Platform
        |
   WebSocket ──────► Your VoiceApp server
        |                   |
   Audio stream        @app.on("tool_call")
   VAD / Turn          @app.on("prompt")       ← BYOLLM
   STT → LLM → TTS    @app.on("turn.completed")
        |                   |
   Caller hears        session.send_tool_result()
   agent speech        session.speak() / session.transfer()
                       session.send_text()     ← stream LLM tokens
                       session.send_media()    ← raw audio mode
```

### Agent capabilities

- **Tool calling** - LLM invokes tools, you handle them and return results
- **Mid-call model switching** - swap LLM model/prompt/tools via `session.update()` for agent handoff
- **Multi-party conferences** - add participants with `calls.dial()`, warm transfer patterns
- **Voicemail detection** - async AMD with beep detection for outbound calls
- **Background audio** - ambient sounds (office, typing, call-center) mixed with agent speech
- **DTMF handling** - detect keypress events for IVR flows
- **Interruption (barge-in)** - caller can interrupt the agent mid-speech
- **User idle detection** - configurable reminders and auto-hangup on silence
- **Per-turn metrics** - latency breakdown (STT, LLM TTFT, TTS) for monitoring
- **Audio streaming** - raw audio relay with `send_media()`, checkpoints, and `clear_audio()`
- **BYOK (Bring Your Own Keys)** - pass API keys for Deepgram, OpenAI, ElevenLabs, Cartesia, etc.

## SDK features

- **Async-first** - `httpx.AsyncClient` with `async/await` everywhere
- **FastAPI native** - `await voice.handle_fastapi(websocket)` drops into any FastAPI/Starlette app
- **Standalone mode** - `app.run(port=9000)` starts a WebSocket server with graceful shutdown
- **Sync + async handlers** - sync handlers run in a thread pool automatically
- **Automatic retries** - exponential backoff on 429 (respects `Retry-After`) and 5xx
- **Typed events** - 25 dataclasses for all WebSocket events (`ToolCall`, `TurnMetrics`, `StreamMedia`, ...)
- **Per-session state** - `session.data` dict persists across events within a call
- **Messaging** - SMS, MMS, WhatsApp with template and interactive message builders
- **Numbers** - search, buy, manage, and carrier lookup
- **Clean errors** - `PlivoError` hierarchy with `status_code`, `retry_after`, and structured bodies
- **Webhook verification** - `validate_signature_v3()` for securing callbacks
- **Python 3.10+** - type hints, `hatchling` build, `ruff` linting

## Installation

```bash
pip install plivo_agent
```

Requires Python 3.10+.

## Quick start

Sign up at [cx.plivo.com/signup](https://cx.plivo.com/signup) to get your `PLIVO_AUTH_ID` and `PLIVO_AUTH_TOKEN`, set them as environment variables, then see the [`examples/`](examples/) directory for runnable scripts:

- [**Full AI pipeline**](examples/full_pipeline.py) - tool calls, model switching, voicemail detection, transfers
- [**BYOLLM**](examples/byollm.py) - bring your own LLM with OpenAI streaming, per-session conversation history
- [**BYOLLM echo**](examples/byollm_echo.py) - minimal echo agent for testing, no external dependencies
- [**Multi-party conference**](examples/multi_party.py) - MPC with mid-call dial, warm transfer to human agents
- [**Speech-to-speech**](examples/s2s_agent.py) - OpenAI Realtime / Gemini Live integration
- [**Raw audio streaming**](examples/audio_stream.py) - bidirectional audio relay with checkpoints and pacing
- [**Background audio**](examples/background_audio.py) - ambient office/typing sounds mixed with agent speech
- [**Pipeline modes**](examples/pipeline_modes.py) - all five config combinations in one file
- [**Metrics & observability**](examples/metrics.py) - per-turn latency breakdown, VAD and turn events
- [**SMS**](examples/send_sms.py) - send an SMS message
- [**WhatsApp**](examples/whatsapp.py) - WhatsApp templates and interactive messages
- [**Buy a number**](examples/buy_number.py) - search and purchase a phone number
- [**Callback server**](examples/callback_server.py) - FastAPI HTTP webhook receiver for call events
- [**FastAPI integration**](examples/agent_fastapi.py) - embed VoiceApp inside an existing FastAPI app

## Development

```bash
git clone https://github.com/plivo/plivo-agent-python.git
cd plivo-agent-python
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v          # 70 tests
ruff check src/ tests/    # lint
```

## License

[MIT](LICENSE)
