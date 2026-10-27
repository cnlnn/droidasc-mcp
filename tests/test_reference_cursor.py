"""Reference tokens reject altered, incompatible and cross-query continuations."""

import base64
import hmac
import json

import pytest

from droidasc_mcp.reference_cursor import ReferenceCursor


@pytest.mark.parametrize("offset", [0, 9, 10, 999, 1000, 2**63 - 1])
def test_cursor_round_trip_and_exact_encoded_size(offset):
    codec = ReferenceCursor(b"session-key", {"operation": "find_string_refs", "value": "x"})
    token = codec.encode(offset)
    assert len(token) == codec.size(offset)
    assert codec.decode(token) == offset
    with pytest.raises(ValueError):
        ReferenceCursor(
            b"different-session", {"operation": "find_string_refs", "value": "x"}
        ).decode(token)


@pytest.mark.parametrize(
    "version,offset", [(2, 1), (True, 1), (1, True), (1, -1), (1, 2**63), (1, 1.5)]
)
def test_signed_cursor_still_requires_supported_version_and_integer_bounds(version, offset):
    key = b"session-key"
    codec = ReferenceCursor(key, {"operation": "find_string_refs", "value": "x"})
    payload = json.dumps([version, codec.selector, offset], separators=(",", ":")).encode()
    token = base64.urlsafe_b64encode(payload + hmac.digest(key, payload, "sha256")).decode()
    with pytest.raises(ValueError, match="Invalid cursor"):
        codec.decode(token)
