"""
WhatsApp Examples — All Message Types

Demonstrates every WhatsApp message type supported by the SDK:
text, media, template, interactive buttons, list, CTA URL, and location.

Usage:
  1. pip install plivo_agent
  2. Set PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN env vars
  3. python whatsapp.py [text | media | template | buttons | list | cta | location]
"""

import asyncio
import sys

from plivo_agent import AsyncClient
from plivo_agent.messaging import InteractiveMessage, Location, Template

SRC = "+14155551234"  # your WhatsApp Business number
DST = "+14155559876"  # recipient


# --- Text message ---

async def send_text():
    async with AsyncClient() as client:
        response = await client.messages.create(
            src=SRC,
            dst=DST,
            type_="whatsapp",
            text="Hello from the Plivo Agent SDK!",
        )
        print("Text sent:", response["message_uuid"])


# --- Media message (image with caption) ---

async def send_media():
    async with AsyncClient() as client:
        response = await client.messages.create(
            src=SRC,
            dst=DST,
            type_="whatsapp",
            text="Here is your receipt.",
            media_urls=["https://media.plivo.com/demo/image-sample.jpg"],
        )
        print("Media sent:", response["message_uuid"])


# --- Template message (with body params, currency, datetime, button) ---

async def send_template():
    tpl = (
        Template("order_confirmation", language="en")
        .add_header_media("https://media.plivo.com/demo/banner.jpg")
        .add_body_param("Alice")
        .add_body_param("ORD-42")
        .add_body_currency("$12.99", "USD", 12990)
        .add_body_datetime("2026-03-07T10:30:00Z")
        .add_button_param("url", 0, "https://example.com/track/ORD-42")
        .build()
    )
    async with AsyncClient() as client:
        response = await client.messages.create(
            src=SRC,
            dst=DST,
            type_="whatsapp",
            template=tpl,
        )
        print("Template sent:", response["message_uuid"])


# --- Interactive: quick reply buttons ---

async def send_buttons():
    interactive = InteractiveMessage.button(
        body_text="How would you rate your experience?",
        buttons=[
            {"id": "great", "title": "Great"},
            {"id": "okay", "title": "Okay"},
            {"id": "poor", "title": "Poor"},
        ],
        header={"type": "text", "text": "Feedback"},
        footer_text="Powered by Plivo",
    )
    async with AsyncClient() as client:
        response = await client.messages.create(
            src=SRC,
            dst=DST,
            type_="whatsapp",
            interactive=interactive,
        )
        print("Buttons sent:", response["message_uuid"])


# --- Interactive: list message ---

async def send_list():
    interactive = InteractiveMessage.list(
        body_text="Browse our menu and pick your favorite.",
        button_text="View Menu",
        sections=[
            {
                "title": "Pizza",
                "rows": [
                    {"id": "margherita", "title": "Margherita", "description": "$10"},
                    {"id": "pepperoni", "title": "Pepperoni", "description": "$12"},
                ],
            },
            {
                "title": "Sides",
                "rows": [
                    {"id": "fries", "title": "Fries", "description": "$4"},
                    {"id": "salad", "title": "Garden Salad", "description": "$6"},
                ],
            },
        ],
        header_text="Mario's Pizza",
        footer_text="Prices include tax",
    )
    async with AsyncClient() as client:
        response = await client.messages.create(
            src=SRC,
            dst=DST,
            type_="whatsapp",
            interactive=interactive,
        )
        print("List sent:", response["message_uuid"])


# --- Interactive: CTA URL ---

async def send_cta():
    interactive = InteractiveMessage.cta_url(
        body_text="Track your order in real time.",
        button_title="Track Order",
        url="https://example.com/track/ORD-42",
        footer_text="Powered by Plivo",
    )
    async with AsyncClient() as client:
        response = await client.messages.create(
            src=SRC,
            dst=DST,
            type_="whatsapp",
            interactive=interactive,
        )
        print("CTA sent:", response["message_uuid"])


# --- Location message ---

async def send_location():
    location = Location.build(
        37.7749,
        -122.4194,
        name="Plivo HQ",
        address="201 Spear St, San Francisco, CA 94105",
    )
    async with AsyncClient() as client:
        response = await client.messages.create(
            src=SRC,
            dst=DST,
            type_="whatsapp",
            location=location,
        )
        print("Location sent:", response["message_uuid"])


if __name__ == "__main__":
    examples = {
        "text": send_text,
        "media": send_media,
        "template": send_template,
        "buttons": send_buttons,
        "list": send_list,
        "cta": send_cta,
        "location": send_location,
    }
    choice = sys.argv[1] if len(sys.argv) > 1 else "text"
    if choice not in examples:
        print(f"Usage: python whatsapp.py [{' | '.join(examples)}]")
        sys.exit(1)
    asyncio.run(examples[choice]())
