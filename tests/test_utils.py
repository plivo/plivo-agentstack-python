"""Tests for plivo_agentstack.utils — webhook signature validation."""

from __future__ import annotations

import base64
import hashlib
import hmac

from plivo_agentstack.utils import validate_signature_v3

AUTH_TOKEN = "my_secret_token"


def _compute_v3_signature(
    uri: str, nonce: str, params: dict | None = None, method: str = "POST"
) -> str:
    """Helper to compute a valid V3 signature for testing."""
    if params is None:
        params = {}

    nonce_bytes = nonce.encode("utf-8")

    if method.upper() == "GET":
        from urllib.parse import parse_qs, urlencode, urlparse

        parsed = urlparse(uri)
        existing = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        merged = {**existing, **params}
        sorted_params = urlencode(sorted(merged.items()))
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if sorted_params:
            base_url = f"{base_url}?{sorted_params}"
    else:
        from urllib.parse import urlencode

        sorted_params = urlencode(sorted(params.items()))
        base_url = f"{uri}.{sorted_params}" if sorted_params else uri

    payload = base_url.encode("utf-8") + b"." + nonce_bytes
    computed = hmac.new(AUTH_TOKEN.encode("utf-8"), payload, hashlib.sha256).digest()
    return base64.b64encode(computed).decode("utf-8")


def test_validate_signature_v3_post():
    """Valid POST signature returns True."""
    uri = "https://example.com/webhook"
    nonce = "abc123nonce"
    params = {"CallUUID": "call-1", "From": "+14155551234"}
    sig = _compute_v3_signature(uri, nonce, params, method="POST")

    result = validate_signature_v3(
        method="POST",
        uri=uri,
        nonce=nonce,
        auth_token=AUTH_TOKEN,
        v3_signature=sig,
        params=params,
    )
    assert result is True


def test_validate_signature_v3_invalid():
    """Wrong signature returns False."""
    uri = "https://example.com/webhook"
    nonce = "abc123nonce"
    params = {"CallUUID": "call-1"}

    result = validate_signature_v3(
        method="POST",
        uri=uri,
        nonce=nonce,
        auth_token=AUTH_TOKEN,
        v3_signature="totally_wrong_signature",
        params=params,
    )
    assert result is False
