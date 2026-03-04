"""Send a WhatsApp template message using the Plivo Agent SDK.

Prerequisites:
    pip install plivo_agent

Environment variables:
    PLIVO_AUTH_ID      -- Your Plivo auth ID
    PLIVO_AUTH_TOKEN   -- Your Plivo auth token

Run:
    python whatsapp.py
"""

import asyncio

from plivo_agent import AsyncClient
from plivo_agent.messaging import Template


async def main():
    async with AsyncClient() as client:
        # Build a WhatsApp template with body parameters
        tpl = (
            Template("order_confirmation", language="en")
            .add_body_param("Alice")
            .add_body_param("ORD-42")
            .add_body_currency("$12.99", "USD", 12990)
            .add_body_datetime("2026-03-07T10:30:00Z")
            .add_button_param("url", 0, "https://example.com/track/ORD-42")
            .build()
        )

        response = await client.messages.create(
            src="+14155551234",
            dst="+14155559876",
            type_="whatsapp",
            template=tpl,
        )
        print("Message UUID:", response["message_uuid"])


if __name__ == "__main__":
    asyncio.run(main())
