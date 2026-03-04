"""VoiceApp -- WebSocket server with @app.on() decorators.

Register event handlers with decorators, then either:
- Call app.run() to start a standalone server (blocks forever)
- Use app.handle_fastapi(ws) / app.handle_starlette(ws) in framework routes

Every handler can be sync or async -- the framework auto-detects:

    @app.on("tool_call")
    def on_tool_call(session, event: ToolCall):       # sync -- runs in thread pool
        session.send_tool_result(event.id, ...)

    @app.on("tool_call")
    async def on_tool_call(session, event: ToolCall):  # async -- runs in event loop
        result = await db.lookup(event.arguments["id"])
        session.send_tool_result(event.id, result)

Handlers receive typed event objects from events.py instead of raw dicts.
Error handling: exceptions in handlers are logged and reported to the
on_handler_error callback. They do NOT crash the connection.
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
from typing import Any, Callable

import websockets

from plivo_agent.agent.events import parse_event
from plivo_agent.agent.session import Session

logger = logging.getLogger("plivo_agent.agent.app")


class VoiceApp:
    """WebSocket server that receives connections from Plivo.

    Register event handlers with @app.on() decorators, then either:
    - Call app.run() to start a standalone server (blocks forever)
    - Use app.handle_fastapi(ws) or app.handle_starlette(ws) in framework routes

    Handlers receive typed event objects instead of raw dicts.
    The event type matches the decorator name (e.g. @app.on("tool_call") -> ToolCall).
    """

    def __init__(self) -> None:
        self._handlers: dict[str, Callable] = {}
        self._catch_all: Callable | None = None
        self._on_connect: Callable | None = None
        self._on_disconnect: Callable | None = None
        self._on_handler_error: Callable | None = None

    def on(self, event_type: str) -> Callable:
        """Register a handler for a specific event type."""

        def decorator(fn: Callable) -> Callable:
            self._handlers[event_type] = fn
            return fn

        return decorator

    def on_event(self, fn: Callable) -> Callable:
        """Register a catch-all handler that fires for every event.

            @app.on_event
            def log_all(session, event):
                print(f"[{session.agent_session_id}] {event}")
        """
        self._catch_all = fn
        return fn

    def on_connect(self, fn: Callable) -> Callable:
        """Register a handler called when a WebSocket connects.

            @app.on_connect
            def connected(session):
                print(f"New connection: {session}")
        """
        self._on_connect = fn
        return fn

    def on_disconnect(self, fn: Callable) -> Callable:
        """Register a handler called when a WebSocket disconnects.

            @app.on_disconnect
            def disconnected(session):
                print(f"Disconnected: {session.agent_session_id}")
        """
        self._on_disconnect = fn
        return fn

    def on_handler_error(self, fn: Callable) -> Callable:
        """Register a callback for handler exceptions.

        Called with (session, event, exception) when a handler raises.
        If not set, exceptions are logged and swallowed.

            @app.on_handler_error
            def handle_error(session, event, exc):
                sentry_sdk.capture_exception(exc)
        """
        self._on_handler_error = fn
        return fn

    # --- Standalone server ---

    def run(self, host: str = "0.0.0.0", port: int = 9000) -> None:
        """Start the WebSocket server. Blocks forever.

        Handles SIGINT/SIGTERM for graceful shutdown.
        """
        asyncio.run(self._serve(host, port))

    async def _serve(self, host: str, port: int) -> None:
        stop = asyncio.Event()
        loop = asyncio.get_event_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)

        async with websockets.serve(self._handle_connection, host, port):
            logger.info("VoiceApp listening on ws://%s:%d", host, port)
            await stop.wait()
            logger.info("Shutting down")

    # --- Framework integration ---

    async def handle_fastapi(self, websocket: Any) -> None:
        """Handle a FastAPI WebSocket connection.

        Usage with FastAPI::

            from fastapi import FastAPI, WebSocket

            fastapi_app = FastAPI()
            voice = VoiceApp()

            @fastapi_app.websocket("/ws")
            async def ws_endpoint(websocket: WebSocket):
                await websocket.accept()
                await voice.handle_fastapi(websocket)

        The WebSocket must already be accepted before calling this method.
        """
        adapted = _StarletteWebSocket(websocket)
        await self._handle_connection(adapted)

    async def handle_starlette(self, websocket: Any) -> None:
        """Handle a Starlette/FastAPI WebSocket connection.

        Usage with FastAPI::

            from fastapi import FastAPI, WebSocket

            fastapi_app = FastAPI()
            voice = VoiceApp()

            @fastapi_app.websocket("/ws")
            async def ws_endpoint(websocket: WebSocket):
                await websocket.accept()
                await voice.handle_starlette(websocket)

        The WebSocket must already be accepted before calling this method.
        """
        adapted = _StarletteWebSocket(websocket)
        await self._handle_connection(adapted)

    # --- Internal connection handler ---

    async def _handle_connection(self, ws: Any) -> None:
        loop = asyncio.get_event_loop()
        session = Session(ws, loop)
        sender_task = asyncio.create_task(session._run_sender())

        # Connection lifecycle: on_connect
        if self._on_connect:
            try:
                await self._dispatch(self._on_connect, session, None, loop, lifecycle=True)
            except Exception:
                logger.exception("on_connect handler raised")

        try:
            async for raw in ws:
                data = json.loads(raw)

                # Parse into typed event (falls back to raw dict for unknown types)
                event = parse_event(data)

                # Resolve event type from "type" or "event" field
                event_type = data.get("type") or data.get("event")

                if event_type == "agent_session.started":
                    session.agent_session_id = data.get("agent_session_id")
                    session.call_uuid = data.get("call_id")

                # Plivo "start" event -- extract stream metadata
                if event_type == "start":
                    start_data = data.get("start", {})
                    session.stream_id = (
                        data.get("streamId") or start_data.get("streamId")
                    )
                    session.call_uuid = session.call_uuid or start_data.get("callId")

                # Catch-all handler
                if self._catch_all:
                    await self._dispatch(self._catch_all, session, event, loop)

                # Type-specific handler
                handler = self._handlers.get(event_type)
                if handler:
                    await self._dispatch(handler, session, event, loop)

                if event_type in ("agent_session.ended", "stop"):
                    break
        except websockets.exceptions.ConnectionClosed:
            pass  # normal -- server closed after hangup or call ended
        except Exception:
            logger.exception(
                "Connection handler error for session %s", session.agent_session_id
            )
        finally:
            sender_task.cancel()

            # Connection lifecycle: on_disconnect
            if self._on_disconnect:
                try:
                    await self._dispatch(
                        self._on_disconnect, session, None, loop, lifecycle=True
                    )
                except Exception:
                    logger.exception("on_disconnect handler raised")

    async def _dispatch(
        self,
        handler: Callable,
        session: Session,
        event: Any,
        loop: Any,
        *,
        lifecycle: bool = False,
    ) -> None:
        """Run handler -- async directly, sync in thread pool.

        Exceptions are caught, logged, and forwarded to on_handler_error.
        They never crash the connection.
        """
        try:
            if lifecycle:
                # Lifecycle handlers get (session,) only
                if asyncio.iscoroutinefunction(handler):
                    await handler(session)
                else:
                    await loop.run_in_executor(None, handler, session)
            else:
                if asyncio.iscoroutinefunction(handler):
                    await handler(session, event)
                else:
                    await loop.run_in_executor(None, handler, session, event)
        except Exception as exc:
            logger.exception(
                "Handler %s raised for session %s",
                handler.__name__,
                session.agent_session_id,
            )
            if self._on_handler_error:
                try:
                    self._on_handler_error(session, event, exc)
                except Exception:
                    logger.exception("on_handler_error callback raised")


# ---------------------------------------------------------------------------
# Starlette/FastAPI WebSocket adapter
# ---------------------------------------------------------------------------


class _StarletteWebSocket:
    """Wraps a Starlette/FastAPI WebSocket to match the websockets interface.

    The websockets library uses ``async for msg in ws`` and ``ws.send()``.
    Starlette uses ``ws.receive_text()`` and ``ws.send_text()``.
    This adapter bridges the difference.
    """

    def __init__(self, ws: Any) -> None:
        self._ws = ws

    async def send(self, data: str) -> None:
        await self._ws.send_text(data)

    def __aiter__(self) -> _StarletteWebSocket:
        return self

    async def __anext__(self) -> str:
        try:
            return await self._ws.receive_text()
        except Exception:
            # Starlette raises WebSocketDisconnect on close
            raise StopAsyncIteration
