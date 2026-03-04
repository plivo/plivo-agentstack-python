"""Per-connection session handle for Agent Stack WebSocket events.

Every event handler receives a Session instance as its first argument.
All methods are sync-safe -- they enqueue messages via the event loop,
so they work identically from sync and async handlers.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Any

logger = logging.getLogger("plivo_agent.agent.session")


class Session:
    """Per-session handle passed to every event handler.

    All methods are sync -- safe to call from both sync and async handlers.
    Messages are queued internally and sent via the async event loop.
    """

    def __init__(self, ws: Any, loop: Any) -> None:
        self.agent_session_id: str | None = None
        self.call_uuid: str | None = None
        self.stream_id: str | None = None  # set from Plivo "start" event
        self.data: dict = {}  # arbitrary per-session state
        self._ws = ws
        self._loop = loop
        self._queue: asyncio.Queue = asyncio.Queue()

    # --- Managed mode ---

    def send_tool_result(self, tool_call_id: str, result: Any) -> None:
        """Send a tool_result response."""
        self._enqueue({"type": "tool_result", "id": tool_call_id, "result": result})

    def send_tool_error(self, tool_call_id: str, error: str) -> None:
        """Send a tool_error response."""
        self._enqueue({"type": "tool_error", "id": tool_call_id, "error": error})

    # --- Text mode ---

    def send_text(self, token: str, last: bool = False) -> None:
        """Stream an LLM token to the platform for TTS."""
        self._enqueue({"type": "text", "token": token, "last": last})

    def extend_wait(self) -> None:
        """Extend idle timeout (BYOLLM: user asked for more time)."""
        self._enqueue({"type": "agent_session.extend_wait"})

    def send_raw(self, msg: dict) -> None:
        """Send an arbitrary JSON message to the platform."""
        self._enqueue(msg)

    # --- Audio mode (Plivo audio streaming protocol) ---

    def send_media(
        self,
        payload_b64: str,
        content_type: str = "audio/x-mulaw",
        sample_rate: int = 8000,
    ) -> None:
        """Send audio to the caller via Plivo's playAudio protocol.

        Args:
            payload_b64: Base64-encoded audio data.
            content_type: Audio MIME type (must match the stream's encoding).
                          Defaults to "audio/x-mulaw" (G.711 mu-law).
            sample_rate: Sample rate in Hz (must match the stream's rate).
                         Defaults to 8000.
        """
        self._enqueue({
            "event": "playAudio",
            "media": {
                "contentType": content_type,
                "sampleRate": sample_rate,
                "payload": payload_b64,
            },
        })

    def send_checkpoint(self, name: str) -> None:
        """Mark a playback position in the audio queue.

        When Plivo finishes playing audio up to this checkpoint, it sends
        a "playedStream" event with the same name back.
        """
        self._enqueue({
            "event": "checkpoint",
            "streamId": self.stream_id or "",
            "name": name,
        })

    def clear_audio(self) -> None:
        """Clear all queued audio on the Plivo side (for interruption)."""
        self._enqueue({
            "event": "clearAudio",
            "streamId": self.stream_id or "",
        })

    # --- Session control (all modes) ---

    def update(self, **kwargs: Any) -> None:
        """Update session config mid-call (LLM, TTS, STT, interruption, etc.)."""
        self._enqueue({"type": "agent_session.update", **kwargs})

    def inject(self, content: str) -> None:
        """Inject context into the LLM conversation."""
        self._enqueue({"type": "agent_session.inject", "content": content})

    def speak(self, text: str) -> None:
        """Speak text to the caller (synthesized via the session's TTS provider)."""
        self._enqueue({"type": "agent_session.speak", "text": text})

    def play(self, file_path: str, *, allow_interruption: bool = True) -> None:
        """Play a pre-recorded WAV file through the call.

        Args:
            file_path: Path to a WAV file (PCM, 16-bit, any sample rate).
                       The file is read and base64-encoded automatically.
                       The platform auto-detects format, resamples to 16kHz,
                       and converts stereo to mono.
            allow_interruption: If False, user speech will not interrupt playback.
                                Default True.
        """
        with open(file_path, "rb") as f:
            audio_data = base64.b64encode(f.read()).decode()
        msg: dict = {
            "type": "agent_session.play",
            "audio_data": audio_data,
        }
        if not allow_interruption:
            msg["allow_interruption"] = False
        self._enqueue(msg)

    def transfer_to_number(
        self,
        destination: str | list[str],
        *,
        dial_mode: str = "parallel",
        timeout: int = 30,
    ) -> None:
        """Transfer the call to one or more phone numbers.

        Args:
            destination: Phone number or list of numbers (E.164 format).
            dial_mode: "parallel" (ring all at once, first to answer wins)
                       or "sequential" (try each in order).
            timeout: Ring timeout per destination in seconds.
        """
        if isinstance(destination, str):
            destination = [destination]
        self._enqueue({
            "type": "agent_session.transfer",
            "destination": destination,
            "dial_mode": dial_mode,
            "timeout": timeout,
        })

    def transfer_to_sip(
        self,
        sip_uri: str,
        *,
        sip_headers: dict[str, str] | None = None,
        timeout: int = 30,
    ) -> None:
        """Transfer the call to a SIP endpoint via Plivo Dial XML.

        Plivo uses ``<Dial><User>sip_uri</User></Dial>`` internally.

        Args:
            sip_uri: SIP URI (e.g. ``"sip:agent@phone.plivo.com"``).
            sip_headers: Optional custom SIP headers (alphanumeric keys,
                         max 24 chars each).
            timeout: Ring timeout in seconds.
        """
        msg: dict = {
            "type": "agent_session.transfer",
            "destination": [sip_uri],
            "sip": True,
            "timeout": timeout,
        }
        if sip_headers:
            msg["sip_headers"] = sip_headers
        self._enqueue(msg)

    def hangup(self) -> None:
        """End the call."""
        self._enqueue({"type": "agent_session.hangup"})

    # --- Background audio ---

    def play_background(self, sound: str, *, volume: float = 0.5, loop: bool = True) -> None:
        """Play or switch background audio (e.g. hold music, ambient noise).

        Args:
            sound: Audio source identifier.
            volume: Volume level 0.0-1.0.
            loop: Whether to loop the audio.
        """
        self._enqueue({"type": "audio.mix", "sound": sound, "volume": volume, "loop": loop})

    def stop_background(self) -> None:
        """Stop background audio mixing."""
        self._enqueue({"type": "audio.mix_enable", "enabled": False})

    # --- Internal ---

    def _enqueue(self, msg: dict) -> None:
        self._loop.call_soon_threadsafe(self._queue.put_nowait, msg)

    async def _run_sender(self) -> None:
        """Background task that drains the queue and sends over WS."""
        try:
            while True:
                msg = await self._queue.get()
                await self._ws.send(json.dumps(msg))
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Sender task error for session %s", self.agent_session_id)
