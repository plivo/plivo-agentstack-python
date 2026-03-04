"""
Minimal BYOLLM echo test — no OpenAI needed.

Receives transcription prompts from Plivo, echoes them back as text tokens.
This lets you trace the full STT -> customer WS -> TTS flow with fake API keys.

Usage:
  1. pip install plivo_agent[all]
  2. python byollm_echo.py
"""

from plivo_agent.agent import (
    AgentSessionEnded,
    AgentSessionStarted,
    Error,
    Interruption,
    Prompt,
    VoiceApp,
)

app = VoiceApp()


@app.on("agent_session.started")
def on_started(session, event: AgentSessionStarted):
    print(f"[STARTED] session={session.agent_session_id} call={session.call_uuid}")


@app.on("prompt")
def on_prompt(session, event: Prompt):
    print(f"[PROMPT] text='{event.text}' is_final={event.is_final}")

    if event.is_final and event.text.strip():
        reply = f"You said: {event.text}"
        session.send_text(reply, last=True)
        print(f"[REPLY] {reply}")


@app.on("interruption")
def on_interruption(session, event: Interruption):
    print(f"[INTERRUPTION] text='{event.interrupted_text or ''}'")


@app.on("error")
def on_error(session, event: Error):
    print(f"[ERROR] code={event.code} message={event.message}")


@app.on("agent_session.ended")
def on_ended(session, event: AgentSessionEnded):
    print(f"[ENDED] duration={event.duration_seconds}s")


if __name__ == "__main__":
    print("Starting BYOLLM echo server on ws://0.0.0.0:9000")
    app.run(port=9000)
