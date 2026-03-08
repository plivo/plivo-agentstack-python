"""
SMS & MMS Examples — Text and Media Messages

Demonstrates sending SMS (text only) and MMS (with media attachments)
using the Plivo Agent SDK.

Usage:
  1. pip install plivo_agentstack
  2. Set PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN env vars
  3. python send_sms.py [sms | mms | mms-multi]
"""

import asyncio
import sys

from plivo_agentstack import AsyncClient

SRC = "+14155551234"  # your Plivo number
DST = "+14155559876"  # recipient


# --- SMS: plain text ---

async def send_sms():
    async with AsyncClient() as client:
        response = await client.messages.create(
            src=SRC,
            dst=DST,
            text="Hello from the Plivo Agent SDK!",
        )
        print("SMS sent:", response["message_uuid"])


# --- MMS: single image ---

async def send_mms():
    async with AsyncClient() as client:
        response = await client.messages.create(
            src=SRC,
            dst=DST,
            text="Check out this image!",
            type_="mms",
            media_urls=["https://media.plivo.com/demo/image-sample.jpg"],
        )
        print("MMS sent:", response["message_uuid"])


# --- MMS: multiple media (image + PDF) ---

async def send_mms_multi():
    async with AsyncClient() as client:
        response = await client.messages.create(
            src=SRC,
            dst=DST,
            text="Here are your documents.",
            type_="mms",
            media_urls=[
                "https://media.plivo.com/demo/image-sample.jpg",
                "https://media.plivo.com/demo/invoice.pdf",
            ],
        )
        print("MMS (multi) sent:", response["message_uuid"])


if __name__ == "__main__":
    examples = {
        "sms": send_sms,
        "mms": send_mms,
        "mms-multi": send_mms_multi,
    }
    choice = sys.argv[1] if len(sys.argv) > 1 else "sms"
    if choice not in examples:
        print(f"Usage: python send_sms.py [{' | '.join(examples)}]")
        sys.exit(1)
    asyncio.run(examples[choice]())
