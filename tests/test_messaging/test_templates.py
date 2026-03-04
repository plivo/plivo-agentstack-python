"""Tests for plivo_agent.messaging.templates — Template builder."""

from __future__ import annotations

from plivo_agent.messaging.templates import Template


def test_basic_template():
    """Template with just name and language produces minimal payload."""
    tpl = Template("hello_world", language="en").build()
    assert tpl == {"name": "hello_world", "language": "en"}
    assert "components" not in tpl


def test_template_with_body_params():
    """Body parameters are included in a body component."""
    tpl = (
        Template("order_update", language="en")
        .add_body_param("Alice")
        .add_body_param("ORD-42")
        .build()
    )
    assert tpl["name"] == "order_update"
    assert tpl["language"] == "en"
    components = tpl["components"]
    assert len(components) == 1
    body_component = components[0]
    assert body_component["type"] == "body"
    assert len(body_component["parameters"]) == 2
    assert body_component["parameters"][0] == {"type": "text", "text": "Alice"}
    assert body_component["parameters"][1] == {"type": "text", "text": "ORD-42"}


def test_template_with_header_media():
    """Header media is included in a header component."""
    tpl = (
        Template("receipt", language="en")
        .add_header_media("https://example.com/receipt.pdf")
        .add_body_param("Alice")
        .build()
    )
    components = tpl["components"]
    assert len(components) == 2
    header = components[0]
    assert header["type"] == "header"
    assert header["parameters"] == [
        {"type": "media", "media": "https://example.com/receipt.pdf"}
    ]
    body = components[1]
    assert body["type"] == "body"


def test_template_with_currency_and_datetime():
    """Currency and datetime body parameters produce correct structures."""
    tpl = (
        Template("invoice", language="en")
        .add_body_currency("$12.99", "USD", 12990)
        .add_body_datetime("2025-06-15T10:30:00Z")
        .build()
    )
    body_params = tpl["components"][0]["parameters"]
    assert len(body_params) == 2

    currency_param = body_params[0]
    assert currency_param["type"] == "currency"
    assert currency_param["currency"] == {
        "fallback_value": "$12.99",
        "code": "USD",
        "amount_1000": 12990,
    }

    datetime_param = body_params[1]
    assert datetime_param["type"] == "date_time"
    assert datetime_param["date_time"] == {
        "fallback_value": "2025-06-15T10:30:00Z",
    }


def test_template_with_button_params():
    """Button parameters are added as top-level components."""
    tpl = (
        Template("tracking", language="en")
        .add_body_param("ORD-42")
        .add_button_param("url", 0, "https://example.com/track/ORD-42")
        .build()
    )
    components = tpl["components"]
    # body component + button component
    assert len(components) == 2

    body = components[0]
    assert body["type"] == "body"

    button = components[1]
    assert button["type"] == "button"
    assert button["sub_type"] == "url"
    assert button["index"] == "0"
    assert button["parameters"] == [
        {"type": "text", "text": "https://example.com/track/ORD-42"}
    ]


def test_fluent_chaining():
    """All builder methods return self for fluent chaining."""
    tpl = Template("full", language="pt_BR")
    result = (
        tpl
        .add_header_param("Header Value")
        .add_header_media("https://example.com/img.png")
        .add_body_param("Name")
        .add_body_currency("R$10,00", "BRL", 10000)
        .add_body_datetime("2025-12-31")
        .add_button_param("quick_reply", 0, "yes")
    )
    # Each method returns the same Template instance
    assert result is tpl

    built = result.build()
    assert built["name"] == "full"
    assert built["language"] == "pt_BR"
    assert len(built["components"]) == 3  # header, body, button
