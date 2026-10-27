"""Versioned reference continuations bound to one session and normalized selector."""

import base64
import binascii
import hashlib
import hmac
import json
from pathlib import Path

from .memory_cache import signature

MAX_CURSOR_LENGTH = 1024


def cursor_identity(settings, root):
    identity = signature(settings, root)
    if identity is None:
        return None
    version, settings, files = identity
    return (
        version,
        settings,
        tuple(item for item in files if Path(item[0]).name not in {"xrefs.sqlite", "calls.sqlite"}),
    )


class ReferenceCursor:
    def __init__(self, key, query, identity=None):
        self.key = key
        selector = {k: v for k, v in query.items() if k not in {"offset", "limit"}}
        self.selector = hashlib.sha256(
            json.dumps([selector, repr(identity)], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        self.base_size = len(self._payload(0)) - 1

    def _payload(self, offset):
        return json.dumps([1, self.selector, offset], separators=(",", ":")).encode()

    def size(self, offset):
        size = self.base_size + len(str(offset)) + 32
        return 4 * ((size + 2) // 3)

    def encode(self, offset):
        payload = self._payload(offset)
        signature = hmac.digest(self.key, payload, "sha256")
        return base64.urlsafe_b64encode(payload + signature).decode("ascii")

    def decode(self, value):
        try:
            if not isinstance(value, str) or not 1 <= len(value) <= MAX_CURSOR_LENGTH:
                raise ValueError
            raw = base64.b64decode(value.encode("ascii"), altchars=b"-_", validate=True)
            payload, signature = raw[:-32], raw[-32:]
            if not hmac.compare_digest(hmac.digest(self.key, payload, "sha256"), signature):
                raise ValueError
            version, selector, offset = json.loads(payload)
            if (
                type(version) is not int
                or version != 1
                or selector != self.selector
                or type(offset) is not int
                or not 0 <= offset < 2**63
            ):
                raise ValueError
            return offset
        except (ValueError, TypeError, UnicodeError, binascii.Error) as exc:
            raise ValueError("Invalid cursor for this session and query") from exc
