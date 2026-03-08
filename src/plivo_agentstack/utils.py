"""SDK utilities — webhook signature validation."""

from __future__ import annotations

import base64
import hashlib
import hmac
from urllib.parse import parse_qs, urlencode, urlparse


def validate_signature_v3(
    method: str,
    uri: str,
    nonce: str,
    auth_token: str,
    v3_signature: str,
    params: dict | None = None,
) -> bool:
    """Validate a Plivo webhook signature (v3).

    Args:
        method: HTTP method ("GET" or "POST").
        uri: Full callback URL.
        nonce: Value of X-Plivo-Signature-V3-Nonce header.
        auth_token: Your Plivo auth token.
        v3_signature: Value of X-Plivo-Signature-V3 header.
        params: Callback parameters (query params for GET, body for POST).

    Returns:
        True if signature is valid, False otherwise.
    """
    if params is None:
        params = {}

    auth_token_bytes = auth_token.encode("utf-8")
    nonce_bytes = nonce.encode("utf-8")

    if method.upper() == "GET":
        parsed = urlparse(uri)
        existing = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        merged = {**existing, **params}
        sorted_params = urlencode(sorted(merged.items()))
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if sorted_params:
            base_url = f"{base_url}?{sorted_params}"
    else:
        sorted_params = urlencode(sorted(params.items()))
        base_url = f"{uri}.{sorted_params}" if sorted_params else uri

    payload = base_url.encode("utf-8") + b"." + nonce_bytes
    computed = hmac.new(auth_token_bytes, payload, hashlib.sha256).digest()
    signature = base64.b64encode(computed)

    return signature in v3_signature.encode("utf-8").split(b",")
