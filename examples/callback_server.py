"""
Callback Server — Receives async HTTP callbacks from Plivo.

Handles hangup, recording, and ring post-call events.
Shared by all modes (managed, text, audio).

Usage:
  pip install fastapi uvicorn
  uvicorn callback_server:app --port 9001
"""

from fastapi import FastAPI, Request

app = FastAPI()


@app.post("/callbacks/hangup")
async def on_hangup(request: Request):
    body = await request.json()
    print(
        f"[callback] Hangup: call_uuid={body.get('call_uuid')} "
        f"duration={body.get('duration')}s cause={body.get('hangup_cause')}"
    )
    return {"status": "ok"}


@app.post("/callbacks/recording")
async def on_recording(request: Request):
    body = await request.json()
    print(f"[callback] Recording ready: {body.get('recording_url')}")
    return {"status": "ok"}


@app.post("/callbacks/ring")
async def on_ring(request: Request):
    body = await request.json()
    print(
        f"[callback] Ring: call_uuid={body.get('call_uuid')} "
        f"direction={body.get('direction')} from={body.get('from')} to={body.get('to')}"
    )
    return {"status": "ok"}
