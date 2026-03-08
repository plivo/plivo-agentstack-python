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
    client.py          # Agent REST client (agents, calls, numbers, sessions)
    events.py          # 25+ typed event dataclasses + parse_event()
    session.py         # Per-connection Session handle
  messaging/           # SMS/MMS/WhatsApp
    client.py          # MessagesClient
    templates.py       # WhatsApp Template builder
    interactive.py     # InteractiveMessage + Location builders
  numbers/             # Phone number management
    client.py          # NumbersClient + LookupResource
tests/                 # pytest + pytest-asyncio + respx
examples/              # 15 runnable scripts
```

## Build & run

```bash
pip install -e ".[dev]"       # install in dev mode
pytest tests/ -v              # run all tests (~70)
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
- New examples: add to `examples/`, use `from plivo_agentstack import AsyncClient` and `from plivo_agentstack.agent import VoiceApp, ...` pattern. Update README Quick start section
- Keep dependencies minimal — core deps are `httpx`, `websockets`, `starlette` only
