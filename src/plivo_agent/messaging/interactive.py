"""WhatsApp interactive message and location builders."""

from __future__ import annotations

from typing import Any


class InteractiveMessage:
    """Factory for WhatsApp interactive message payloads.

    Each class method returns a dict suitable for
    ``MessagesClient.create(interactive=...)``.

    Usage::

        interactive = InteractiveMessage.button(
            body_text="Choose an option:",
            buttons=[
                {"id": "yes", "title": "Yes"},
                {"id": "no", "title": "No"},
            ],
        )
        await client.messages.create(
            dst="+14155559876",
            type_="whatsapp",
            interactive=interactive,
        )
    """

    @staticmethod
    def button(
        body_text: str,
        buttons: list[dict[str, str]],
        *,
        header: dict[str, Any] | None = None,
        footer_text: str | None = None,
    ) -> dict[str, Any]:
        """Build a WhatsApp interactive button message.

        Args:
            body_text: Message body text.
            buttons: List of button dicts, each with ``id`` and ``title`` keys.
                At most 3 buttons are allowed by the WhatsApp API.
            header: Optional header dict (e.g. ``{"type": "text", "text": "..."}``).
            footer_text: Optional footer text.
        """
        action_buttons = [
            {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
            for b in buttons
        ]

        payload: dict[str, Any] = {
            "type": "button",
            "body": {"text": body_text},
            "action": {"buttons": action_buttons},
        }

        if header:
            payload["header"] = header
        if footer_text:
            payload["footer"] = {"text": footer_text}

        return payload

    @staticmethod
    def list(
        body_text: str,
        button_text: str,
        sections: list[dict[str, Any]],
        *,
        header_text: str | None = None,
        footer_text: str | None = None,
    ) -> dict[str, Any]:
        """Build a WhatsApp interactive list message.

        Args:
            body_text: Message body text.
            button_text: Text on the list-opening button (max 20 chars).
            sections: List of section dicts. Each section has a ``title`` and
                a ``rows`` list. Each row has ``id``, ``title``, and optional
                ``description``.
            header_text: Optional header text.
            footer_text: Optional footer text.

        Example ``sections``::

            [
                {
                    "title": "Popular",
                    "rows": [
                        {"id": "pizza", "title": "Pizza", "description": "Classic"},
                        {"id": "pasta", "title": "Pasta"},
                    ],
                },
            ]
        """
        payload: dict[str, Any] = {
            "type": "list",
            "body": {"text": body_text},
            "action": {
                "button": button_text,
                "sections": sections,
            },
        }

        if header_text:
            payload["header"] = {"type": "text", "text": header_text}
        if footer_text:
            payload["footer"] = {"text": footer_text}

        return payload

    @staticmethod
    def cta_url(
        body_text: str,
        button_title: str,
        url: str,
        *,
        header: dict[str, Any] | None = None,
        footer_text: str | None = None,
    ) -> dict[str, Any]:
        """Build a WhatsApp interactive CTA (call-to-action) URL message.

        Args:
            body_text: Message body text.
            button_title: Display text for the CTA button.
            url: The URL to open when the button is tapped.
            header: Optional header dict.
            footer_text: Optional footer text.
        """
        payload: dict[str, Any] = {
            "type": "cta_url",
            "body": {"text": body_text},
            "action": {
                "buttons": [
                    {
                        "type": "cta_url",
                        "title": button_title,
                        "url": url,
                    },
                ],
            },
        }

        if header:
            payload["header"] = header
        if footer_text:
            payload["footer"] = {"text": footer_text}

        return payload


class Location:
    """Builder for WhatsApp location message payloads.

    Usage::

        loc = Location.build(37.7749, -122.4194, name="HQ", address="SF, CA")
        await client.messages.create(
            dst="+14155559876",
            type_="whatsapp",
            location=loc,
        )
    """

    @staticmethod
    def build(
        latitude: float,
        longitude: float,
        *,
        name: str | None = None,
        address: str | None = None,
    ) -> dict[str, Any]:
        """Build a location payload for ``MessagesClient.create(location=...)``.

        Args:
            latitude: Latitude of the location.
            longitude: Longitude of the location.
            name: Optional name of the location.
            address: Optional street address.
        """
        payload: dict[str, Any] = {
            "latitude": latitude,
            "longitude": longitude,
        }
        if name is not None:
            payload["name"] = name
        if address is not None:
            payload["address"] = address
        return payload
