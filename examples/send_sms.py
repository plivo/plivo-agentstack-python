"""Send an SMS message using the Plivo Agent SDK.

Prerequisites:
    pip install plivo_agent

Environment variables:
    PLIVO_AUTH_ID      -- Your Plivo auth ID
    PLIVO_AUTH_TOKEN   -- Your Plivo auth token

Run:
    python send_sms.py
"""

import asyncio

from plivo_agent import AsyncClient


async def main():
    async with AsyncClient() as client:
        response = await client.messages.create(
            src="+14155551234",
            dst="+14155559876",
            text="Hello from the Plivo Agent SDK!",
        )
        print("Message UUID:", response["message_uuid"])
        print("API ID:", response["api_id"])


if __name__ == "__main__":
    asyncio.run(main())
