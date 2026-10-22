"""Native results must match the independent JVM oracle, not byte candidates."""

import zipfile
from dataclasses import replace

import pytest

from droidasc_mcp.config import Settings
from droidasc_mcp.method_backend import query_methods
from droidasc_mcp.native_dex import Dex, InvalidDex, query_references


@pytest.mark.parametrize(
    "operation,descriptor",
    [
        ("find_method_refs", "Lfixture/Target;->pick(I)V"),
        ("find_field_refs", "Lfixture/Ordering;->value:I"),
        ("get_method_calls", "Lfixture/Caller;->run()V"),
    ],
)
def test_native_matches_independent_oracle(
    tmp_path, smali_dex_files, boundary_dex_file, operation, descriptor
):
    bundle = tmp_path / "analysis.apk"
    with zipfile.ZipFile(bundle, "w") as archive:
        for number, path in enumerate([*smali_dex_files, boundary_dex_file]):
            archive.write(path, f"classes{number}.dex")
    settings = Settings.from_env()
    query = {
        "operation": operation,
        "offset": 0,
        "limit": 100,
        "class_name": "",
        "field_descriptor" if operation == "find_field_refs" else "method_descriptor": descriptor,
    }
    actual = query_references(settings, bundle, query)
    expected = query_methods(settings, bundle, "", query, tmp_path)
    assert expected["status"] == "ok", expected
    for result in (actual, expected):
        result.pop("backend")
        result.pop("backend_version")
    assert actual == expected
    # No configured Java or JADX is necessary on the production path.
    isolated = replace(settings, jadx_home=None, java_executable=None)
    assert query_references(isolated, bundle, query)["items"] == expected["items"]


@pytest.mark.parametrize("accelerator", [False, True])
def test_bulk_cursor_matches_simple_cursor(
    smali_dex_files, boundary_dex_file, graph_dex_files, accelerator
):
    from droidasc_mcp.native_dex import METHOD_NAMES
    from droidasc_mcp.native_scan import scanner

    for path in [*smali_dex_files, boundary_dex_file, *graph_dex_files]:
        dex = Dex(path.read_bytes())
        assert dex.classes() == dex.classes(accelerator=False)
        for _, cls in dex.classes():
            assert dex.raw_members(cls) == dex.raw_members(cls, accelerator=False)
        for fields in (True, False):
            scan = scanner(dex, set(), fields, False, accelerator=accelerator)
            for _, cls in dex.classes():
                for _, _, code in dex.members(cls)[1]:
                    if not code:
                        continue
                    simple = list(dex.instructions(code))
                    bulk = list(scan(code))
                    assert sum(row[3] for row in bulk) == len(simple)
                    expected = [
                        row
                        for row in simple
                        if (0x52 <= row[2] <= 0x6D if fields else row[2] in METHOD_NAMES)
                        or row[2] >= 0xFA
                        and row[2] <= 0xFE
                        or row[2] == 0
                        and dex.data[row[0] + 1] != 0
                    ]
                    assert [row[:3] for row in bulk if row[2] != -1] == expected
        dex.close()


def test_allocation_free_selector_matches_independent_cursor(
    smali_dex_files, boundary_dex_file, graph_dex_files
):
    from droidasc_mcp.native_dex import METHOD_NAMES
    from droidasc_mcp.native_scan import method_selector

    for path in [*smali_dex_files, boundary_dex_file, *graph_dex_files]:
        dex = Dex(path.read_bytes())
        for fields in (False, True):
            targets = set(range(0, dex.tables[3 if fields else 4][0], 2))
            for access in ("all", "read", "write"):
                select = method_selector(dex, targets, fields, access)
                if select is None:
                    pytest.skip("Optional C accelerator is not installed")
                for _, cls in dex.classes():
                    _, methods = dex.raw_members(cls)
                    expected = []
                    instructions = dynamic = without = 0
                    for method in methods:
                        _, _, code = method
                        without += not code
                        wanted = False
                        for position, _, op in dex.instructions(code) if code else ():
                            instructions += 1
                            dynamic += op in {0xFA, 0xFB, 0xFC, 0xFD, 0xFE}
                            wanted |= op in {0xFA, 0xFB, 0xFC, 0xFD, 0xFE}
                            if 0x52 <= op <= 0x6D if fields else op in METHOD_NAMES:
                                read = 0x52 <= op <= 0x58 or 0x60 <= op <= 0x66
                                wanted |= dex.u16(position + 2) in targets and (
                                    not fields
                                    or access == "all"
                                    or access == ("read" if read else "write")
                                )
                        if wanted:
                            expected.append(method)
                    assert select(methods) == (expected, instructions, dynamic, without)
        dex.close()


def test_unsorted_class_directory_preserves_validation(smali_dex_files):
    for path in smali_dex_files:
        dex = Dex(path.read_bytes())
        try:
            unordered = dex.classes(ordered=False)
            assert sorted(unordered) == sorted(dex.classes())
            assert unordered == dex.classes(accelerator=False, ordered=False)
        finally:
            dex.close()


def test_fused_class_selection_matches_independent_cursor(
    smali_dex_files, boundary_dex_file, graph_dex_files
):
    from droidasc_mcp.native_dex import METHOD_NAMES
    from droidasc_mcp.native_scan import class_selector

    for path in [*smali_dex_files, boundary_dex_file, *graph_dex_files]:
        dex = Dex(path.read_bytes())
        try:
            for fields in (False, True):
                targets = set(range(0, dex.tables[3 if fields else 4][0], 2))
                for access in ("all", "read", "write"):
                    select = class_selector(dex, targets, fields, access)
                    assert select is not None
                    for _, cls in dex.classes():
                        field_defs, methods = dex.raw_members(cls, accelerator=False)
                        expected = []
                        definitions = [
                            item[0]
                            for item in (field_defs if fields else methods)
                            if item[0] in targets
                        ]
                        instructions = dynamic = without = 0
                        for method in methods:
                            _, _, code = method
                            without += not code
                            wanted = False
                            for position, _, op in dex.instructions(code) if code else ():
                                instructions += 1
                                dynamic += op in {0xFA, 0xFB, 0xFC, 0xFD, 0xFE}
                                wanted |= op in {0xFA, 0xFB, 0xFC, 0xFD, 0xFE}
                                if 0x52 <= op <= 0x6D if fields else op in METHOD_NAMES:
                                    read = 0x52 <= op <= 0x58 or 0x60 <= op <= 0x66
                                    wanted |= dex.u16(position + 2) in targets and (
                                        not fields
                                        or access == "all"
                                        or access == ("read" if read else "write")
                                    )
                            if wanted:
                                expected.append(method)
                        assert select(cls) == (
                            expected,
                            definitions,
                            len(methods),
                            instructions,
                            dynamic,
                            without,
                        )
        finally:
            dex.close()


def test_directory_selection_batches_the_same_checked_class_cursor(
    smali_dex_files, boundary_dex_file, graph_dex_files
):
    from droidasc_mcp.native_dex import utf16_key
    from droidasc_mcp.native_scan import class_selector, select_directory

    for path in [*smali_dex_files, boundary_dex_file, *graph_dex_files]:
        dex = Dex(path.read_bytes())
        try:
            for fields in (False, True):
                targets = set(range(0, dex.tables[3 if fields else 4][0], 2))
                for access in ("all", "read", "write"):
                    select = class_selector(dex, targets, fields, access)
                    assert callable(getattr(select, "directory", None))
                    selected, declared, counts = [], [], [0, 0, 0, 0]
                    for owner, cls in dex.classes(ordered=False):
                        matches, definitions, *metrics = select(cls)
                        declared.extend(definitions)
                        counts = [a + b for a, b in zip(counts, metrics, strict=True)]
                        if matches:
                            selected.append((owner, matches))
                    selected.sort(key=lambda row: utf16_key(row[0]))
                    assert select_directory(dex, select) == (selected, declared, *counts)
        finally:
            dex.close()


@pytest.mark.parametrize("fields", [False, True])
@pytest.mark.parametrize("index", [0, 65535])
@pytest.mark.parametrize(
    "damage", [None, "field_within", "field_cross", "method_within", "method_cross"]
)
def test_directory_duplicate_stamps_are_class_local_and_cover_both_member_groups(
    fields, index, damage
):
    import struct

    from droidasc_mcp import _dexscan
    from droidasc_mcp.native_dex import WIDTHS

    encoded = b"\x00" if index == 0 else b"\xff\xff\x03"
    field, method = encoded + b"\x00", encoded + b"\x00\x00"
    payload = {
        None: b"\x01\x00\x01\x00" + field + method,
        "field_within": b"\x02\x00\x00\x00" + field + b"\x00\x00",
        "field_cross": b"\x01\x01\x00\x00" + field + field,
        "method_within": b"\x00\x00\x02\x00" + method + b"\x00\x00\x00",
        "method_cross": b"\x00\x00\x01\x01" + method + method,
    }[damage]
    # A low-level cursor fixture: repeat a class's member data at two directory
    # positions to ensure the bulk duplicate table resets its logical generation.
    cls = (index + 1) * 8 + 32
    data = bytearray(cls + 64)
    for offset in (cls, cls + 32):
        struct.pack_into("<I", data, offset + 24, len(data))
    data.extend(payload)
    mask = bytearray(65536)
    mask[index] = 1
    arguments = (39, WIDTHS, bytes(mask), int(fields), index + 1, index + 1, 0, 1, 1, 0)

    def single():
        return _dexscan.select_class(bytes(data), cls, *arguments)

    def bulk():
        return _dexscan.select_classes(
            bytes(data), [("La/A;", cls), ("Lb/B;", cls + 32)], *arguments
        )

    if damage:
        for call in (single, bulk):
            with pytest.raises(ValueError, match="Invalid DEX class data"):
                call()
    else:
        assert single() == ([], [index], 1, 0, 0, 1)
        assert bulk() == ([], [index, index], 2, 0, 0, 2)
        assert bulk() == bulk(), "No duplicate-stamp state may survive a native call"


def test_directory_selection_checks_nonmatching_corrupt_code(smali_dex_files):
    from droidasc_mcp.native_scan import class_selector, select_directory

    original = Dex(smali_dex_files[0].read_bytes())
    try:
        for _, cls in original.classes():
            for _, _, code in original.raw_members(cls)[1]:
                if not code:
                    continue
                data = bytearray(original.data)
                data[code + 16] = 0x3E  # Reserved opcode, even when no IDs match.
                dex = Dex(bytes(data))
                try:
                    with pytest.raises(InvalidDex, match="instruction"):
                        select_directory(dex, class_selector(dex, set(), False, "all"))
                finally:
                    dex.close()
                return
        pytest.fail("Fixture has no code")
    finally:
        original.close()


def test_native_rejects_truncated_payload(boundary_dex_file):
    dex = Dex(boundary_dex_file.read_bytes())
    for _, cls in dex.classes():
        for _, _, code in dex.members(cls)[1]:
            if not code:
                continue
            data = bytearray(dex.data)
            data[code + 16 : code + 20] = b"\x00\x03\x08\x00"
            data[code + 20 : code + 24] = b"\xff\xff\xff\x7f"
            altered = Dex(bytes(data))
            with pytest.raises(InvalidDex):
                list(altered.instructions(code))
            return
    pytest.fail("Fixture has no code")


def type_pool_dex(values):
    import struct

    count = len(values)
    data = bytearray(112 + count * 8)
    data[:8] = b"dex\n039\0"
    struct.pack_into("<II", data, 36, 112, 0x12345678)
    struct.pack_into("<IIII", data, 56, count, 112, count, 112 + count * 4)
    for index, value in enumerate(values):
        struct.pack_into("<I", data, 112 + index * 4, len(data))
        struct.pack_into("<I", data, 112 + count * 4 + index * 4, index)
        data.extend(value)
    struct.pack_into("<I", data, 32, len(data))
    return Dex(bytes(data))


@pytest.mark.parametrize("fuzzy", [False, True])
@pytest.mark.parametrize("case_sensitive", [False, True])
def test_type_matching_matches_strict_decoder(fuzzy, case_sensitive):
    # Deliberately unsorted IDs, duplicate strings and Unicode case mappings.
    values = ["Lz;", "LABC;", "Labc;", "L\u212a;", "L\u4e2d;", "L\U0001f600;", "L\0;", "Labc;"]
    encoded = []
    for value in values:
        units = value.encode("utf-16-le", "surrogatepass")
        mutf = "".join(
            chr(int.from_bytes(units[i : i + 2], "little")) for i in range(0, len(units), 2)
        )
        encoded.append(
            bytes([len(units) // 2])
            + mutf.encode("utf-8", "surrogatepass").replace(b"\0", b"\xc0\x80")
            + b"\0"
        )
    dex = type_pool_dex(encoded)
    try:
        for query in ["", "Labc;", "abc", "k", "L\u4e2d;", "\U0001f600", "\0", "missing"]:
            expected = dex.matching_types(
                query, fuzzy=fuzzy, case_sensitive=case_sensitive, accelerator=False
            )
            assert dex.matching_types(query, fuzzy=fuzzy, case_sensitive=case_sensitive) == expected
    finally:
        dex.close()


@pytest.mark.parametrize(
    "value", [b"\x02A\0", b"\x01A", b"\xff\xff\xff\xff\x10A\0", b"\x01\xff\0", b"\x02\xc0\x80\0"]
)
@pytest.mark.parametrize("accelerator", [False, True])
def test_type_matching_rejects_unmatched_malformed_strings(value, accelerator):
    dex = type_pool_dex([b"\x01Z\0", value])
    with pytest.raises(InvalidDex):
        dex.matching_types("missing", accelerator=accelerator)
    dex.close()


@pytest.mark.parametrize("accelerator", [False, True])
def test_type_matching_rejects_invalid_string_id(accelerator):
    import struct

    dex = type_pool_dex([b"\x01Z\0"])
    data = bytearray(dex.data)
    struct.pack_into("<I", data, dex.tables[1][1], 1)
    dex.close()
    dex = Dex(bytes(data))
    with pytest.raises(InvalidDex):
        dex.matching_types("missing", accelerator=accelerator)
    dex.close()


@pytest.mark.parametrize("fields", [False, True])
def test_owner_member_filter_matches_independent_pool(smali_dex_files, fields):
    for path in smali_dex_files:
        dex = Dex(path.read_bytes())
        for owners in (set(), {0}, set(range(0, dex.tables[1][0], 2))):
            assert dex.owner_members(fields, owners) == dex.owner_members(
                fields, owners, accelerator=False
            )
        dex.close()


@pytest.mark.parametrize("accelerator", [False, True])
def test_owner_member_filter_rejects_invalid_owner(smali_dex_files, accelerator):
    import struct

    dex = Dex(smali_dex_files[0].read_bytes())
    data = bytearray(dex.data)
    struct.pack_into("<H", data, dex.tables[4][1], dex.tables[1][0])
    dex.close()
    dex = Dex(bytes(data))
    with pytest.raises(InvalidDex):
        dex.owner_members(False, set(), accelerator=accelerator)
    dex.close()


def code_dex(stream, version=39, pool=1):
    import struct

    data = bytearray(128) + stream
    data[:8] = f"dex\n{version:03d}\0".encode()
    struct.pack_into("<III", data, 32, len(data), 112, 0x12345678)
    struct.pack_into("<I", data, 124, len(stream) // 2)
    dex = Dex(bytes(data))
    for table in (3, 4):
        dex.tables[table] = (pool, 0, 8)
    return dex


def test_large_payload_rendering_is_bounded():
    import struct

    from droidasc_mcp.native_structure import render
    from droidasc_mcp.runner import DroidAscError

    stream = struct.pack("<HHI", 0x300, 8, 50000) + bytes(400000)
    dex = code_dex(stream)
    with pytest.raises(DroidAscError, match="Payload rendering exceeds"):
        render(dex, None, 128, 0, 0, budget=4096)


@pytest.mark.parametrize("fields", [False, True])
def test_query_without_native_extension_matches_accelerated(
    tmp_path, smali_dex_files, monkeypatch, fields
):
    import droidasc_mcp.native_dex as native
    import droidasc_mcp.native_scan as scan

    bundle = tmp_path / "analysis.apk"
    with zipfile.ZipFile(bundle, "w") as archive:
        for index, path in enumerate(smali_dex_files):
            archive.write(path, f"classes{index}.dex")
    query = {
        "operation": "find_field_refs" if fields else "find_method_refs",
        "field_descriptor" if fields else "method_descriptor": (
            "Lfixture/Ordering;->value:I" if fields else "Lfixture/Target;->pick(I)V"
        ),
        "offset": 0,
        "limit": 100,
    }
    expected = query_references(Settings.from_env(), bundle, query)
    original_scan, original_classes = scan.scanner, Dex.classes
    monkeypatch.setattr(native, "_native_members", None)
    monkeypatch.setattr(scan, "method_selector", lambda *args: None)
    monkeypatch.setattr(scan, "class_selector", lambda *args: None)
    monkeypatch.setattr(scan, "scanner", lambda *args: original_scan(*args, accelerator=False))
    monkeypatch.setattr(Dex, "classes", lambda self: original_classes(self, accelerator=False))
    assert query_references(Settings.from_env(), bundle, query) == expected


@pytest.mark.parametrize("accelerator", [False, True])
@pytest.mark.parametrize(
    "stream,version",
    [
        (b"\x00\x04", 39),
        (b"\x3e\x00", 39),
        (b"\x6e\x00\x00\x00", 39),
        (b"\xfa\x00\x00\x00\x00\x00\x00\x00", 37),
        (b"\xfe\x00\x00\x00", 38),
        (b"\x00\x03\x03\x00\x00\x00\x00\x00", 39),
        (b"\x00\x03\x08\x00\xff\xff\xff\x7f", 39),
        (b"\x00\x01\x01\x00", 39),
        (b"\x00\x02\x01\x00", 39),
        (b"\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00", 39),
    ],
)
def test_all_scanners_reject_malformed_instructions(stream, version, accelerator):
    from droidasc_mcp.native_scan import scanner

    dex = code_dex(stream, version)
    with pytest.raises(InvalidDex):
        list(dex.instructions(112))
    with pytest.raises(InvalidDex):
        list(scanner(dex, {0}, False, True, accelerator=accelerator)(112))


@pytest.mark.parametrize("accelerator", [False, True])
@pytest.mark.parametrize(
    "fields,stream", [(False, b"\x6e\x00\x01\x00\x00\x00"), (True, b"\x60\x00\x01\x00")]
)
def test_scanners_validate_nonmatching_reference_indexes(accelerator, fields, stream):
    from droidasc_mcp.native_scan import scanner

    dex = code_dex(stream)
    with pytest.raises(InvalidDex):
        list(scanner(dex, set(), fields, True, accelerator=accelerator)(112))


@pytest.mark.parametrize("accelerator", [False, True])
def test_dense_method_streaming_preserves_sites_and_counts(accelerator):
    from droidasc_mcp.native_scan import scanner

    dex = code_dex(b"\x6e\x00\x00\x00\x00\x00" * 10000 + b"\x0e\x00")
    rows = list(scanner(dex, {0}, False, True, accelerator=accelerator)(112))
    assert sum(row[3] for row in rows) == 10001
    assert [row[1] for row in rows if row[2] == 0x6E] == list(range(0, 30000, 3))
    if accelerator:
        try:
            from droidasc_mcp._dexscan import scan
        except ImportError:
            return  # Source installs without a compiler intentionally retain the Python path.
        from droidasc_mcp.native_dex import WIDTHS

        batch = scan(dex.data, 112, 39, WIDTHS, bytes([1]) + bytes(65535), 0, 1, 1)
        assert len(batch) == 1025 and batch[-1][2] == -2


def test_fuzzy_reference_entry_matches_exact_unions(tmp_path, smali_dex_files):
    bundle = tmp_path / "analysis.apk"
    with zipfile.ZipFile(bundle, "w") as archive:
        for i, path in enumerate(smali_dex_files):
            archive.write(path, f"classes{i}.dex")
    settings = replace(Settings.from_env(), jadx_home=None, java_executable="must-not-run")
    base = {
        "operation": "search_refs",
        "kind": "method",
        "value": "PiCk",
        "member_match": "exact_name",
        "case_sensitive": False,
        "offset": 0,
        "limit": 100,
    }
    result = query_references(settings, bundle, base)
    expected = []
    for signature in ("(I)V", "(Ljava/lang/String;)V"):
        exact = query_references(
            settings,
            bundle,
            {
                "operation": "find_method_refs",
                "method_descriptor": "Lfixture/Target;->pick" + signature,
                "offset": 0,
                "limit": 100,
            },
        )
        expected.extend(exact["items"])
    assert result["total"] == len(expected) == 2
    assert sorted(result["items"], key=str) == sorted(expected, key=str)
    assert query_references(settings, bundle, {**base, "case_sensitive": True})["total"] == 0
    assert (
        query_references(settings, bundle, {**base, "class_name": "Missing", "fuzzy_class": True})[
            "total"
        ]
        == 0
    )
    prototype = query_references(
        settings, bundle, {**base, "member_match": "prototype", "value": "(I)V"}
    )
    assert any(row["callee"] == "Lfixture/Target;->pick(I)V" for row in prototype["items"])
    selected = query_references(settings, bundle, {**base, "target_descriptor": "(I)V"})
    assert selected["total"] == 1
    assert selected["items"][0]["callee"] == "Lfixture/Target;->pick(I)V"
    owner_only = query_references(
        settings, bundle, {**base, "value": "", "class_name": "Lfixture/Target;"}
    )
    assert all(row["callee"].startswith("Lfixture/Target;->") for row in owner_only["items"])
    lower_owner = query_references(settings, bundle, {**base, "class_name": "lfixture/target;"})
    assert lower_owner["items"] == result["items"]


@pytest.mark.parametrize(
    "stream",
    [
        b"\x80" * 5,
        b"\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00",
        b"\x00\x00\x01\x01\x00\x00\x00\x00\x00\x00",
        b"\x01\x01\x00\x00\x00\x00\x00\x00",
    ],
)
def test_member_decoders_reject_malformed_class_data(stream):
    from droidasc_mcp.native_dex import _native_members
    from droidasc_mcp.native_scan import class_selector

    dex = code_dex(b"\x00\x00")
    data = bytearray(dex.data)
    import struct

    struct.pack_into("<I", data, 24, len(data))
    dex.data = bytes(data) + stream
    with pytest.raises(InvalidDex):
        dex.raw_members(0, accelerator=False)
    if _native_members is not None:
        with pytest.raises(InvalidDex):
            dex.raw_members(0)
        with pytest.raises(InvalidDex):
            class_selector(dex, set(), False, "all")(0)
