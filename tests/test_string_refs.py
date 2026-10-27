"""Literal string-use navigation and independent checked-cursor differentials."""

import hashlib
import struct
import zipfile
import zlib
from dataclasses import replace
from functools import partial
from types import SimpleNamespace

import pytest

from droidasc_mcp.config import Settings
from droidasc_mcp.native_dex import Dex
from droidasc_mcp.service import DroidAscService


@pytest.mark.parametrize("accelerator", [False, True])
@pytest.mark.parametrize("sensitive", [False, True])
@pytest.mark.parametrize(
    "value", ["https://example.test/a[b]?x=1.*", "mixedcase", "pool-only[never]"]
)
def test_literal_string_refs_match_independent_cursor(
    tmp_path, string_reference_dex_files, value, sensitive, accelerator, monkeypatch
):
    bundle = tmp_path / "analysis.apk"
    expected = []
    instructions = methods = without = 0
    with zipfile.ZipFile(bundle, "w") as archive:
        for number, path in enumerate(string_reference_dex_files, 1):
            entry = "classes.dex" if number == 1 else f"classes{number}.dex"
            archive.write(path, entry)
            dex = Dex(path.read_bytes())
            try:
                for _, cls in dex.classes(accelerator=False):
                    _, definitions = dex.raw_members(cls, accelerator=False)
                    for index, _, code in dex.ordered_methods(definitions):
                        methods += 1
                        without += not code
                        for position, address, op in dex.instructions(code) if code else ():
                            instructions += 1
                            if op not in {0x1A, 0x1B}:
                                continue
                            target = dex.u16(position + 2) if op == 0x1A else dex.u32(position + 2)
                            text = dex.string(target)
                            if (value if sensitive else value.lower()) not in (
                                text if sensitive else text.lower()
                            ):
                                continue
                            expected.append(
                                {
                                    "caller": dex.method(index),
                                    "dex_entry": entry,
                                    "string_index": target,
                                    "value": text,
                                    "instruction_offset": address,
                                    "offset_unit": "code_units_from_method_start",
                                    "opcode": "const-string"
                                    if op == 0x1A
                                    else "const-string/jumbo",
                                }
                            )
            finally:
                dex.close()
    from droidasc_mcp import native_strings
    from droidasc_mcp.native_scan import scanner

    if not accelerator:
        monkeypatch.setattr(native_strings, "class_selector", lambda *args: None)
        monkeypatch.setattr(native_strings, "scanner", partial(scanner, accelerator=False))
        monkeypatch.setattr(
            native_strings, "string_mask", partial(native_strings.string_mask, accelerator=False)
        )

    settings = replace(Settings.from_env(), java_executable="must-not-run", jadx_home=None)
    actual = native_strings.query_strings(
        settings,
        bundle,
        {
            "operation": "find_string_refs",
            "value": value,
            "case_sensitive": sensitive,
            "offset": 0,
            "limit": 100,
        },
    )
    assert actual["items"] == expected
    assert actual["total"] == len(expected)
    assert actual["scanned_instructions"] == instructions
    assert actual["scanned_methods"] == methods
    assert actual["methods_without_code"] == without
    assert actual["instruction_scan_complete"] and not actual["scan_errors"]
    assert not (tmp_path / "xrefs.sqlite").exists()


def test_string_search_result_handoff_pagination_and_cache(tmp_path, string_reference_dex_files):
    paths = []
    for number, source in enumerate(string_reference_dex_files):
        target = tmp_path / f"input{number}.dex"
        target.write_bytes(source.read_bytes())
        paths.append(str(target))
    settings = replace(
        Settings.from_env(),
        allowed_roots=(tmp_path,),
        java_executable="must-not-run",
        jadx_home=None,
    )
    service = DroidAscService(settings)
    try:
        opened = service.open_dex_session(paths)
        assert opened["status"] == "ok", opened
        key = opened["session_id"]
        pool = service.query_dex_session(
            key, operation="search_strings", value="a[b]?", offset=0, limit=100
        )
        value = next(row["value"] for row in pool["items"] if row["value"].startswith("https://"))
        rows, offset = [], 0
        while True:
            page = service.query_dex_session(
                key, operation="find_string_refs", value=value, offset=offset, limit=1
            )
            assert page["status"] == "ok", page
            rows.extend(page["items"])
            if not page["has_more"]:
                break
            offset = page["next_offset"]
        assert len(rows) == page["total"] == 3
        repeat = service.query_dex_session(
            key, operation="find_string_refs", value=value, offset=0, limit=1
        )
        assert repeat["query_cache"]["hit"]
        assert repeat["items"] == rows[:1]
        with pytest.raises(ValueError, match="nonempty literal"):
            service.query_dex_session(
                key, operation="find_string_refs", value="", offset=0, limit=10
            )
    finally:
        service.close()


def test_string_unseen_pages_reuse_complete_sites(string_reference_dex_files, monkeypatch):
    service = DroidAscService(
        replace(
            Settings.from_env(),
            allowed_roots=(string_reference_dex_files[0].parent,),
            java_executable="must-not-run",
            jadx_home=None,
        )
    )
    try:
        opened = service.open_dex_session([str(p) for p in string_reference_dex_files])
        assert opened["status"] == "ok", opened
        key = opened["session_id"]
        query = {
            "operation": "find_string_refs",
            "value": "https://example.test/a[b]?x=1.*",
            "offset": 0,
            "limit": 1,
        }
        expected = service.analyze_dex(
            [str(p) for p in string_reference_dex_files], **{**query, "limit": 100}
        )
        first = service.query_dex_session(key, **query)
        assert first["status"] == "ok" and first["total"] == 3, first

        def rescan(*args, **kwargs):
            pytest.fail("An unseen string page must reuse the complete selected set")

        monkeypatch.setattr(service.runner, "query_dex_session", rescan)
        rest = service.query_dex_session(key, **{**query, "offset": 1, "limit": 2})
        assert rest["query_cache"]["scope"] == "selected_reference_set"
        assert first["items"] + rest["items"] == expected["items"]
        assert not rest["has_more"] and rest["next_offset"] is None
        for field in ("scanned_methods", "scanned_instructions", "methods_without_code"):
            assert rest[field] == first[field] == expected[field]
        empty = service.query_dex_session(key, **{**query, "offset": 100, "limit": 2})
        assert empty["items"] == [] and empty["total"] == 3
        repeated = service.query_dex_session(key, **{**query, "limit": 100})
        assert repeated["items"] == expected["items"]
    finally:
        service.close()


@pytest.mark.parametrize("index", [65535, 65536, 70000])
def test_jumbo_uses_32bit_string_ids(index):
    from droidasc_mcp._dexscan import scan

    from droidasc_mcp.native_dex import WIDTHS

    raw = bytearray(16)
    raw += b"\x1b\x00" + struct.pack("<I", index) + b"\x0e\x00"
    struct.pack_into("<I", raw, 12, 4)
    mask = bytearray((70001 + 7) // 8)
    mask[index >> 3] |= 1 << (index & 7)
    rows = scan(bytes(raw), 0, 39, WIDTHS, bytes(mask), 2, 1, 70001)
    assert rows == [(16, 0, 0x1B, 1), (24, 4, -1, 1)]
    assert scan(bytes(raw), 0, 39, WIDTHS, bytes(len(mask)), 2, 1, 70001) == [(24, 4, -1, 2)]


@pytest.mark.parametrize("case", ["mask", "index", "width", "payload", "unknown"])
def test_string_scan_rejects_malformed_input_even_without_matches(case):
    from droidasc_mcp._dexscan import scan

    from droidasc_mcp.native_dex import WIDTHS

    raw = bytearray(16) + b"\x1b\x00\x00\x00\x00\x00"
    struct.pack_into("<I", raw, 12, 3)
    mask, widths = b"\x00", WIDTHS
    if case == "mask":
        mask = b""
    elif case == "index":
        struct.pack_into("<I", raw, 18, 8)
    elif case == "width":
        widths = bytearray(WIDTHS)
        widths[0x1B] = 2
        widths = bytes(widths)
    elif case == "payload":
        raw[16:18] = b"\x00\x03"
    elif case == "unknown":
        raw[16] = 0xE3
    with pytest.raises(ValueError, match="Invalid|Unknown"):
        scan(bytes(raw), 0, 39, widths, mask, 2, 1, 8)


def test_dense_string_cursor_resumes_at_checked_boundaries():
    from droidasc_mcp.native_scan import scanner

    raw = bytearray(16) + (b"\x1b\x00\x01\x00\x00\x00" * 1500) + b"\x0e\x00"
    struct.pack_into("<I", raw, 12, 4501)
    dex = SimpleNamespace(data=bytes(raw), version=39, tables=[(8, 0)] * 5)
    rows = list(scanner(dex, b"\x02", 2, True)(0))
    assert [row[:3] for row in rows if row[2] == 0x1B] == [
        (16 + index * 6, index * 3, 0x1B) for index in range(1500)
    ]
    assert sum(row[3] for row in rows) == 1501


@pytest.mark.parametrize("accelerator", [False, True])
@pytest.mark.parametrize("opcode", [0x1A, 0x1B])
def test_unmatched_malformed_string_operand_fails_closed(
    tmp_path, string_reference_dex_files, monkeypatch, opcode, accelerator
):
    from droidasc_mcp import native_strings
    from droidasc_mcp.native_scan import scanner
    from droidasc_mcp.worker_errors import DroidAscError

    data = bytearray(string_reference_dex_files[0].read_bytes())
    dex = Dex(bytes(data))
    try:
        position = next(
            position
            for _, cls in dex.classes()
            for _, _, code in dex.raw_members(cls)[1]
            if code
            for position, _, op in dex.instructions(code)
            if op == opcode
        )
        struct.pack_into("<H" if opcode == 0x1A else "<I", data, position + 2, dex.tables[0][0])
    finally:
        dex.close()
    data[12:32] = hashlib.sha1(data[32:]).digest()
    struct.pack_into("<I", data, 8, zlib.adler32(data[12:]))
    bundle = tmp_path / "malformed.apk"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("classes.dex", data)
    if not accelerator:
        monkeypatch.setattr(native_strings, "class_selector", lambda *args: None)
        monkeypatch.setattr(native_strings, "scanner", partial(scanner, accelerator=False))
    with pytest.raises(DroidAscError, match="Invalid DEX"):
        native_strings.query_strings(
            Settings.from_env(),
            bundle,
            {
                "operation": "find_string_refs",
                "value": "no-match-never",
                "offset": 0,
                "limit": 1,
            },
        )


@pytest.mark.parametrize(
    "extra",
    [
        {"class_name": "stringrefs.Caller"},
        {"method_descriptor": "Lstringrefs/Caller;->first()V"},
        {"fuzzy_class": True},
        {"kind": "method"},
        {"field_access": "read"},
        {"prefix": "stringrefs"},
        {"target_descriptor": "()V"},
        {"member_match": "name"},
    ],
)
def test_literal_string_refs_reject_ignored_filters(extra):
    from droidasc_mcp.service import _normalize_dex_query

    with pytest.raises(ValueError):
        _normalize_dex_query({"operation": "find_string_refs", "value": "text", **extra})


def string_pool_dex(values):
    data = bytearray(112 + len(values) * 4)
    data[:8] = b"dex\n039\0"
    struct.pack_into("<II", data, 36, 112, 0x12345678)
    struct.pack_into("<II", data, 56, len(values), 112)
    for index, value in enumerate(values):
        struct.pack_into("<I", data, 112 + index * 4, len(data))
        data.extend(value)
    struct.pack_into("<I", data, 32, len(data))
    return Dex(bytes(data))


def mutf_string(value):
    units = value.encode("utf-16-le", "surrogatepass")
    count = len(units) // 2
    prefix = bytearray()
    while count >= 128:
        prefix.append((count & 127) | 128)
        count >>= 7
    prefix.append(count)
    text = "".join(
        chr(int.from_bytes(units[index : index + 2], "little")) for index in range(0, len(units), 2)
    )
    return bytes(prefix) + text.encode("utf-8", "surrogatepass").replace(b"\0", b"\xc0\x80") + b"\0"


@pytest.mark.parametrize("sensitive", [False, True])
def test_string_mask_matches_strict_decoder_for_unicode_and_repeated_prefixes(sensitive):
    from droidasc_mcp.native_strings import string_mask

    values = [
        "",
        "ABC",
        "abc",
        "\u212a",
        "\u4e2d",
        "\U0001f600",
        "\0",
        "x\0Y",
        "\ud800",
        "a" * 20000 + "b",
        "prefix[.*]?suffix",
        "abc",
    ]
    dex = string_pool_dex([mutf_string(value) for value in values])
    try:
        for value in [
            "",
            "abc",
            "k",
            "\u4e2d",
            "\U0001f600",
            "\0",
            "\ud800",
            "a" * 1000 + "b",
            "[.*]?",
            "missing",
        ]:
            expected = bytearray((len(values) + 7) // 8)
            for index, text in enumerate(values):
                if (value if sensitive else value.lower()) in (text if sensitive else text.lower()):
                    expected[index >> 3] |= 1 << (index & 7)
            assert string_mask(dex, value, sensitive) == bytes(expected)
            assert string_mask(dex, value, sensitive, accelerator=False) == bytes(expected)
    finally:
        dex.close()


@pytest.mark.parametrize("accelerator", [False, True])
@pytest.mark.parametrize(
    "value",
    [
        b"\x02A\0",
        b"\x01A",
        b"\xff\xff\xff\xff\x10A\0",
        b"\x01\xff\0",
        b"\x02\xc0\x80\0",
        b"\x02\xf0\x9f\x98\x80\0",
    ],
)
def test_string_mask_rejects_invalid_nonmatching_pool_values(accelerator, value):
    from droidasc_mcp.native_dex import InvalidDex
    from droidasc_mcp.native_strings import string_mask

    dex = string_pool_dex([b"\x01Z\0", value])
    try:
        with pytest.raises(InvalidDex):
            string_mask(dex, "missing", True, accelerator=accelerator)
    finally:
        dex.close()


@pytest.mark.parametrize("offset,count", [(-1, 0), (1, 1), (0, -1), (0, 2)])
def test_native_string_pool_rejects_invalid_table_ranges(offset, count):
    from droidasc_mcp._dexscan import matching_strings

    with pytest.raises(ValueError):
        matching_strings(b"\0" * 4, offset, count, b"a", True, True)


def test_string_pool_falls_back_when_native_export_is_unavailable(monkeypatch):
    from droidasc_mcp import _dexscan
    from droidasc_mcp.native_strings import string_mask

    monkeypatch.delattr(_dexscan, "matching_strings")
    dex = string_pool_dex([mutf_string("ABC"), mutf_string("\u212a")])
    try:
        assert string_mask(dex, "abc", False) == b"\x01"
        assert string_mask(dex, "k", False) == b"\x02"
    finally:
        dex.close()


def test_unicode_query_uses_strict_python_matching(monkeypatch):
    from droidasc_mcp import _dexscan
    from droidasc_mcp.native_strings import string_mask

    def unexpected(*args):
        pytest.fail("Unicode queries require strict Unicode matching")

    monkeypatch.setattr(_dexscan, "matching_strings", unexpected)
    dex = string_pool_dex([mutf_string("prefix\u4e2dsuffix"), mutf_string("other")])
    try:
        assert string_mask(dex, "\u4e2d", True) == b"\x01"
    finally:
        dex.close()
