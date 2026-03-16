"""
Minimal BYOLLM echo test -- no OpenAI needed.

Receives transcription prompts from Plivo, echoes them back as text tokens.
This lets you trace the full STT -> customer WS -> TTS flow with fake API keys.

Usage:
  1. pip install plivo_agentstack[all]
  2. python byollm_echo.py
"""

from plivo_agentstack.agent import (
    AgentSessionEnded,
    AgentSessionStarted,
    Error,
    Interruption,
    Prompt,
    VoiceApp,
)

app = VoiceApp()


@app.on("session.started")
def on_started(session, event: AgentSessionStarted):
    print(f"[STARTED] session={session.agent_session_id} call={session.call_uuid}")


@app.on("user.transcription")
def on_prompt(session, event: Prompt):
    print(f"[PROMPT] text='{event.text}' is_final={event.is_final}")

    if event.is_final and event.text.strip():
        # Echo back as text tokens for TTS
        reply = f"You said: {event.text}"
        session.send_text(reply, last=True)
        print(f"[REPLY] {reply}")


@app.on("agent.speech_interrupted")
def on_interruption(session, event: Interruption):
    print(f"[INTERRUPTION] text='{event.interrupted_text or ''}'")


@app.on("session.error")
def on_error(session, event: Error):
    print(f"[ERROR] code={event.code} message={event.message}")


@app.on("session.ended")
def on_ended(session, event: AgentSessionEnded):
    print(f"[ENDED] duration={event.duration_seconds}s")


if __name__ == "__main__":
    print("Starting BYOLLM echo server on ws://0.0.0.0:9000")
    app.run(port=9000)
