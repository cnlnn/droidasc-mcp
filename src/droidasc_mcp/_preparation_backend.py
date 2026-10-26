"""Optional preparation checksums, selected before consuming any user input.

Only the pinned backend is eligible. Failed availability or bounded compatibility
checks retain stdlib; selected functions are called directly thereafter, so a
runtime failure cannot retry partially consumed input or silently change engines.
"""

import zlib
from importlib import import_module

_PINNED_VERSION = "1.0.0"
_VECTORS = (b"", b"123456789", b"\x00\xff" * 17, bytes(range(256)) * 4)
_SEEDS = (0, 1, 0xFFFFFFFF)


def _compatible_checksum(checksum, name):
    if not callable(checksum):
        return False
    reference = getattr(zlib, name)
    for data in _VECTORS:
        actual = checksum(data)
        if type(actual) is not int or actual != reference(data):
            return False
        for seed in _SEEDS:
            actual = checksum(data, seed)
            if type(actual) is not int or actual != reference(data, seed):
                return False
            split = len(data) // 2
            prefix = checksum(data[:split], seed)
            if type(prefix) is not int or prefix != reference(data[:split], seed):
                return False
            continued = checksum(data[split:], prefix)
            if type(continued) is not int or continued != reference(data, seed):
                return False
    return True


def _select_backend():
    selected = {
        name: (getattr(zlib, name), "stdlib", "optional backend unavailable or unpinned")
        for name in ("crc32", "adler32")
    }
    try:
        if import_module("zlib_ng").__version__ != _PINNED_VERSION:
            return selected
        candidate = import_module("zlib_ng.zlib_ng")
    except Exception:
        # Availability/compatibility only: no user stream exists at this point.
        # KeyboardInterrupt and SystemExit are deliberately not suppressed.
        return selected
    for name in selected:
        selected[name] = (getattr(zlib, name), "stdlib", "optional checksum incompatible")
        try:
            checksum = getattr(candidate, name)
            if _compatible_checksum(checksum, name):
                if name == "crc32":
                    selected[name] = (checksum, "zlib-ng", "compatibility preflight passed")
                else:
                    selected[name] = (
                        zlib.adler32,
                        "stdlib",
                        "compatible; stdlib retained by current scope",
                    )
        except Exception:
            # A failure in one optional checksum must not select it or disable
            # the separately validated checksum. Actual calls are not retried.
            pass
    return selected


_selected = _select_backend()
crc32, CRC_BACKEND_NAME, CRC_BACKEND_REASON = _selected["crc32"]
adler32, ADLER_BACKEND_NAME, ADLER_BACKEND_REASON = _selected["adler32"]
