"""WhatsApp template builder with fluent API."""

from __future__ import annotations

from typing import Any


class Template:
    """Build a WhatsApp template payload for the Plivo Message API.

    Usage::

        tpl = (
            Template("order_confirmation", language="en")
            .add_header_media("https://example.com/receipt.pdf")
            .add_body_param("Alice")
            .add_body_param("ORD-42")
            .add_body_currency("$12.99", "USD", 12990)
            .add_body_datetime("2025-06-15T10:30:00Z")
            .add_button_param("url", 0, "https://example.com/track/ORD-42")
            .build()
        )
    """

    def __init__(self, name: str, language: str = "en") -> None:
        self._name = name
        self._language = language
        self._header_params: list[dict[str, Any]] = []
        self._body_params: list[dict[str, Any]] = []
        self._button_params: list[dict[str, Any]] = []

    # -- Header ----------------------------------------------------------

    def add_header_param(self, value: str) -> Template:
        """Add a text parameter to the header component."""
        self._header_params.append({"type": "text", "text": value})
        return self

    def add_header_media(self, url: str) -> Template:
        """Add a media header (image, video, or document URL)."""
        self._header_params.append({"type": "media", "media": url})
        return self

    # -- Body ------------------------------------------------------------

    def add_body_param(self, value: str) -> Template:
        """Add a text parameter to the body component."""
        self._body_params.append({"type": "text", "text": value})
        return self

    def add_body_currency(
        self,
        fallback: str,
        code: str,
        amount_1000: int,
    ) -> Template:
        """Add a currency parameter to the body component.

        Args:
            fallback: Fallback display string (e.g. "$12.99").
            code: ISO 4217 currency code (e.g. "USD").
            amount_1000: Amount multiplied by 1000 (e.g. 12990 for $12.99).
        """
        self._body_params.append({
            "type": "currency",
            "currency": {
                "fallback_value": fallback,
                "code": code,
                "amount_1000": amount_1000,
            },
        })
        return self

    def add_body_datetime(self, fallback: str) -> Template:
        """Add a date-time parameter to the body component.

        Args:
            fallback: Fallback display string (e.g. "2025-06-15T10:30:00Z").
        """
        self._body_params.append({
            "type": "date_time",
            "date_time": {
                "fallback_value": fallback,
            },
        })
        return self

    # -- Buttons ---------------------------------------------------------

    def add_button_param(
        self,
        sub_type: str,
        index: int,
        value: str,
    ) -> Template:
        """Add a button parameter.

        Args:
            sub_type: Button sub-type (e.g. "url", "quick_reply").
            index: Zero-based button index.
            value: Parameter value (URL suffix or quick-reply payload).
        """
        self._button_params.append({
            "type": "button",
            "sub_type": sub_type,
            "index": str(index),
            "parameters": [{"type": "text", "text": value}],
        })
        return self

    # -- Build -----------------------------------------------------------

    def build(self) -> dict[str, Any]:
        """Return the template dict ready for ``MessagesClient.create(template=...)``."""
        components: list[dict[str, Any]] = []

        if self._header_params:
            components.append({
                "type": "header",
                "parameters": self._header_params,
            })

        if self._body_params:
            components.append({
                "type": "body",
                "parameters": self._body_params,
            })

        if self._button_params:
            components.extend(self._button_params)

        payload: dict[str, Any] = {
            "name": self._name,
            "language": self._language,
        }
        if components:
            payload["components"] = components

        return payload
