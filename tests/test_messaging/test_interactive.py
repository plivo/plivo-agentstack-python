"""Tests for plivo_agent.messaging.interactive — InteractiveMessage and Location."""

from __future__ import annotations

from plivo_agent.messaging.interactive import InteractiveMessage, Location


def test_button_message():
    """InteractiveMessage.button builds a button message payload."""
    result = InteractiveMessage.button(
        body_text="Choose an option:",
        buttons=[
            {"id": "yes", "title": "Yes"},
            {"id": "no", "title": "No"},
        ],
        header={"type": "text", "text": "Confirm"},
        footer_text="Reply to continue",
    )
    assert result["type"] == "button"
    assert result["body"] == {"text": "Choose an option:"}
    assert result["header"] == {"type": "text", "text": "Confirm"}
    assert result["footer"] == {"text": "Reply to continue"}

    action_buttons = result["action"]["buttons"]
    assert len(action_buttons) == 2
    assert action_buttons[0] == {
        "type": "reply",
        "reply": {"id": "yes", "title": "Yes"},
    }
    assert action_buttons[1] == {
        "type": "reply",
        "reply": {"id": "no", "title": "No"},
    }


def test_list_message():
    """InteractiveMessage.list builds a list message payload."""
    sections = [
        {
            "title": "Popular",
            "rows": [
                {"id": "pizza", "title": "Pizza", "description": "Classic"},
                {"id": "pasta", "title": "Pasta"},
            ],
        },
    ]
    result = InteractiveMessage.list(
        body_text="Choose a meal:",
        button_text="View Menu",
        sections=sections,
        header_text="Our Menu",
        footer_text="Tap to select",
    )
    assert result["type"] == "list"
    assert result["body"] == {"text": "Choose a meal:"}
    assert result["action"]["button"] == "View Menu"
    assert result["action"]["sections"] == sections
    assert result["header"] == {"type": "text", "text": "Our Menu"}
    assert result["footer"] == {"text": "Tap to select"}


def test_cta_url_message():
    """InteractiveMessage.cta_url builds a CTA URL message payload."""
    result = InteractiveMessage.cta_url(
        body_text="Visit our website",
        button_title="Open",
        url="https://example.com",
        footer_text="Powered by Plivo",
    )
    assert result["type"] == "cta_url"
    assert result["body"] == {"text": "Visit our website"}
    assert result["footer"] == {"text": "Powered by Plivo"}

    buttons = result["action"]["buttons"]
    assert len(buttons) == 1
    assert buttons[0] == {
        "type": "cta_url",
        "title": "Open",
        "url": "https://example.com",
    }


def test_location_build():
    """Location.build produces a location payload with optional fields."""
    loc = Location.build(37.7749, -122.4194, name="HQ", address="SF, CA")
    assert loc["latitude"] == 37.7749
    assert loc["longitude"] == -122.4194
    assert loc["name"] == "HQ"
    assert loc["address"] == "SF, CA"

    # Without optional fields
    loc_minimal = Location.build(0.0, 0.0)
    assert loc_minimal == {"latitude": 0.0, "longitude": 0.0}
    assert "name" not in loc_minimal
    assert "address" not in loc_minimal
