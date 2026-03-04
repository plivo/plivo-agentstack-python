"""Tests for plivo_agent.agent.app.VoiceApp."""

from __future__ import annotations

from plivo_agent.agent.app import VoiceApp


def test_on_decorator_registers_handler():
    """@app.on('event_type') registers the handler in _handlers."""
    app = VoiceApp()

    @app.on("tool_call")
    def handle_tool_call(session, event):
        pass

    assert "tool_call" in app._handlers
    assert app._handlers["tool_call"] is handle_tool_call


def test_on_event_registers_catch_all():
    """@app.on_event registers a catch-all handler."""
    app = VoiceApp()

    @app.on_event
    def log_all(session, event):
        pass

    assert app._catch_all is log_all


def test_on_connect_registers_lifecycle():
    """@app.on_connect registers the on_connect lifecycle handler."""
    app = VoiceApp()

    @app.on_connect
    def on_connect(session):
        pass

    assert app._on_connect is on_connect


def test_multiple_handlers():
    """Different event types can each have their own handler."""
    app = VoiceApp()

    @app.on("tool_call")
    def handle_tool(session, event):
        pass

    @app.on("turn.completed")
    def handle_turn(session, event):
        pass

    @app.on("agent_session.started")
    def handle_start(session, event):
        pass

    assert len(app._handlers) == 3
    assert app._handlers["tool_call"] is handle_tool
    assert app._handlers["turn.completed"] is handle_turn
    assert app._handlers["agent_session.started"] is handle_start
