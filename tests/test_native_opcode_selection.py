"""Complete opcode counters and bounds agree across native selection cursors."""

import struct

import pytest

from droidasc_mcp import _dexscan
from droidasc_mcp.native_dex import WIDTHS


def selection(body, version, fields):
    data = bytearray(64)
    struct.pack_into("<I", data, 32, len(data) + len(body))
    struct.pack_into("<I", data, 60, len(body) // 2)
    data.extend(body)
    data.extend(b"\0\0\1\0\0\0\x30")
    mask = bytes(1 if fields == 2 else 65536)
    arguments = (version, WIDTHS, mask, fields, 1, 1, 0, 1, 1, 0)
    return (
        lambda: _dexscan.select_class(bytes(data), 8, *arguments),
        lambda: _dexscan.select_classes(bytes(data), [("La/A;", 8)], *arguments),
    )


@pytest.mark.parametrize("version", [35, 37, 38, 39, 40])
@pytest.mark.parametrize("fields", [0, 1, 2])
def test_every_opcode_bulk_matches_single_class_cursor_and_rejects_truncation(version, fields):
    for opcode, width in enumerate(WIDTHS):
        body = bytes([opcode]) + bytes(max(width, 1) * 2 - 1)
        single, bulk = selection(body, version, fields)
        unavailable = opcode >= 0xFA and version < (39 if opcode >= 0xFE else 38)
        if not width or unavailable:
            for call in (single, bulk):
                with pytest.raises(ValueError, match="instruction"):
                    call()
            continue
        matches, definitions, *metrics = single()
        expected = ([("La/A;", matches)] if matches else [], definitions, *metrics)
        assert bulk() == expected, (version, fields, opcode)
        assert metrics[1] == 1
        if width > 1:
            for call in selection(body[:-2], version, fields):
                with pytest.raises(ValueError, match="instruction"):
                    call()


@pytest.mark.parametrize("fields", [0, 1, 2])
def test_long_mixed_method_accumulates_all_counters_and_checks_the_tail(fields):
    body = (b"\x0e\0\xfe\0\0\0") * 257
    single, bulk = selection(body, 39, fields)
    matches, definitions, *metrics = single()
    assert matches == [(0, 0, 48)]
    assert metrics == [1, 514, 257, 0]
    assert bulk() == ([("La/A;", matches)], definitions, *metrics)
    for call in selection(body + b"\x3e\0", 39, fields):
        with pytest.raises(ValueError, match="instruction"):
            call()
