"""Offline receiving-side contract for original physical DEX 041 addressing."""

import hashlib
import struct
import zipfile
import zlib
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import pytest
from dex041_fixture import dex041_container

from droidasc_mcp.native_dex import Dex, InvalidDex
from droidasc_mcp.service import DroidAscService


def headers(data):
    offsets, position = [], 0
    while position < len(data):
        offsets.append(position)
        position += struct.unpack_from("<I", data, position + 32)[0]
    assert position == len(data)
    return offsets


def shared_container(names, sharing, *, references=False):
    data = bytearray(
        dex041_container(names, shared_strings=sharing == "backward_compat", references=references)
    )
    offsets = headers(data)
    if sharing == "forward" and len(offsets) > 1:
        # Common strings, type IDs and prototypes are addressed in the later logical file.
        last = offsets[-1]
        table = struct.unpack_from("<I", data, last + 60)[0]
        for offset in offsets[:-1]:
            target = struct.unpack_from("<I", data, offset + 60)[0]
            data[target : target + 12] = data[table : table + 12]
            for position in (68, 76):
                data[offset + position : offset + position + 4] = data[
                    last + position : last + position + 4
                ]
    for offset in offsets:
        size = struct.unpack_from("<I", data, offset + 32)[0]
        data[offset + 12 : offset + 32] = hashlib.sha1(data[offset + 32 : offset + size]).digest()
        struct.pack_into("<I", data, offset + 8, zlib.adler32(data[offset + 12 : offset + size]))
    return bytes(data)


def original_oracle(data, header):
    """Read fixture pools and const-string directly, without product/header-view helpers."""

    def u32(position):
        return struct.unpack_from("<I", data, position)[0]

    def leb(position):
        value = 0
        for shift in range(0, 35, 7):
            byte = data[position]
            position += 1
            value |= (byte & 127) << shift
            if byte < 128:
                return value, position
        raise AssertionError("fixture contains an unterminated integer")

    def string(index):
        position = u32(u32(header + 60) + index * 4)
        length, position = leb(position)
        end = data.index(0, position)
        value = data[position:end].decode("ascii")
        assert len(value) == length
        return value

    def type_name(index):
        return string(u32(u32(header + 68) + index * 4))

    cls = u32(header + 100)
    name = type_name(u32(cls))
    position = u32(cls + 24)
    counts = []
    for _ in range(4):
        value, position = leb(position)
        counts.append(value)
    assert counts in ([0, 0, 1, 0], [1, 0, 1, 0])
    if counts[0]:
        field, position = leb(position)
        flags, position = leb(position)
        assert field == 0 and flags == 9
    method, position = leb(position)
    flags, position = leb(position)
    code, position = leb(position)
    assert method == 0 and flags == 9
    method_id = u32(header + 92)
    owner, prototype, name_id = struct.unpack_from("<HHI", data, method_id)
    proto = u32(header + 76) + prototype * 12
    assert u32(proto + 8) == 0
    descriptor = type_name(owner) + "->" + string(name_id) + "()" + type_name(u32(proto + 4))
    assert struct.unpack_from("<H", data, code + 16)[0] == 0x1A
    assert struct.unpack_from("<H", data, code + 14 + u32(code + 12) * 2)[0] == 0x11
    index = struct.unpack_from("<H", data, code + 18)[0]
    return name, descriptor, code, string(index)


@pytest.mark.parametrize("names", [("A",), ("A", "B"), ("A", "B", "C")])
@pytest.mark.parametrize("sharing", ["none", "forward", "backward_compat"])
@pytest.mark.parametrize("accelerator", [False, True])
def test_every_physical_header_reads_original_pools_and_code(names, sharing, accelerator):
    data = shared_container(names, sharing)
    original = hashlib.sha256(data).hexdigest()
    for header, expected_name in zip(headers(data), names, strict=True):
        name, descriptor, code, value = original_oracle(data, header)
        dex = Dex(data, header_offset=header)
        try:
            assert dex.data is data and dex.header_offset == header and dex.version == 41
            classes = dex.classes(accelerator=accelerator)
            assert [row[0] for row in classes] == [name] == [f"Loracle/{expected_name};"]
            fields, methods = dex.members(classes[0][1])
            assert fields == [] and methods == [(descriptor, 9, code)]
            instructions = list(dex.instructions(code))
            assert instructions[0][1] == 0 and instructions[0][2] == 0x1A
            assert dex.string(dex.u16(code + 18)) == value == f"value-{expected_name}"
        finally:
            dex.close()
        assert hashlib.sha256(data).hexdigest() == original


@pytest.mark.parametrize("header", [-1, 1, 4, 120, 0xFFFFFFFF, True, None])
def test_logical_header_selector_rejects_non_headers(header):
    with pytest.raises((InvalidDex, ValueError)):
        Dex(dex041_container(), header_offset=header)


@pytest.mark.parametrize("sharing", ["none", "forward", "backward_compat"])
@pytest.mark.parametrize("names", [("A",), ("A", "B"), ("A", "B", "C")])
@pytest.mark.parametrize("archived", [False, True])
def test_native_preparation_keeps_one_original_backing_without_java(
    settings, tmp_path, names, sharing, archived
):
    data = shared_container(names, sharing)
    path = tmp_path / ("input.apk" if archived else "input.dex")
    if archived:
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("classes.dex", data)
    else:
        path.write_bytes(data)
    with closing(
        DroidAscService(
            replace(settings, java_executable="java-must-not-run", jadx_home=None, dexlib_home=None)
        )
    ) as svc:
        opened = (
            svc.open_artifact_session(str(path), max_uncompressed_bytes=1024**2)
            if archived
            else svc.open_dex_session([str(path)])
        )
        assert opened["status"] == "ok", opened
        key = opened["session_id"]
        assert opened["class_count"] == len(names)
        assert [row["logical_header_offset"] for row in opened["sources"]] == headers(data)
        assert all(row["sha256"] == hashlib.sha256(data).hexdigest() for row in opened["sources"])
        assert all(
            row["normalization"] == "none_physical_logical_view" for row in opened["sources"]
        )
        root = Path(svc.sessions.entries[key].storage.name)
        with zipfile.ZipFile(root / "analysis.apk") as archive:
            assert archive.read("classes.dex") == data
            assert sum(info.file_size for info in archive.infolist()) == len(data)
            assert all(not archive.read(row["dex_entry"]) for row in opened["sources"][1:])
        path.unlink()
        inventory = svc.query_dex_session(key, operation="list_classes", offset=0, limit=100)
        assert [row["class_name"] for row in inventory["items"]] == [
            f"Loracle/{name};" for name in names
        ]
        for name in names:
            constants = svc.query_dex_session(
                key,
                operation="get_string_constants",
                class_name=f"oracle.{name}",
                offset=0,
                limit=100,
            )
            assert constants["status"] == "ok", constants
            assert [row["value"] for row in constants["items"]] == [f"value-{name}"]
            refs = svc.query_dex_session(
                key, operation="find_string_refs", value=f"value-{name}", offset=0, limit=100
            )
            assert refs["status"] == "ok" and refs["total"] == 1, refs
            assert refs["items"][0]["caller"] == f"Loracle/{name};->hello()Ljava/lang/String;"
            assert refs["items"][0]["instruction_offset"] == 0
        svc.close_artifact(key)
        assert svc.sessions.reserved == 0 and not svc.sessions.entries and not root.exists()


@pytest.mark.parametrize("sharing", ["none", "forward", "backward_compat"])
def test_every_logical_header_has_exact_reference_sites_and_structure(settings, tmp_path, sharing):
    path = tmp_path / "references.dex"
    data = shared_container(("A", "B"), sharing, references=True)
    path.write_bytes(data)
    with closing(
        DroidAscService(
            replace(settings, java_executable="java-must-not-run", jadx_home=None, dexlib_home=None)
        )
    ) as svc:
        opened = svc.open_dex_session([str(path)])
        assert opened["status"] == "ok", opened
        key = opened["session_id"]
        for index, (header, name) in enumerate(zip(headers(data), ("A", "B"), strict=True)):
            owner = f"Loracle/{name};"
            method = owner + "->hello()Ljava/lang/String;"
            field = owner + "->field:Ljava/lang/String;"
            # Original physical code units, independent of product iterators/indexes.
            code = data.index(struct.pack("<7H", 0x011C, 0, 0x0162, 0, 0x0071, 0, 0), header)
            assert code >= header + 120
            cases = [
                ({"operation": "find_field_refs", "field_descriptor": field}, "sget-object", 4),
                (
                    {"operation": "find_method_refs", "method_descriptor": method},
                    "invoke-static",
                    6,
                ),
                ({"operation": "find_string_refs", "value": f"value-{name}"}, "const-string", 0),
            ]
            for query, opcode, offset in cases:
                result = svc.query_dex_session(key, offset=0, limit=100, **query)
                assert result["status"] == "ok" and result["total"] == 1, result
                row = result["items"][0]
                assert row["caller"] == method and row["instruction_offset"] == offset
                assert row["opcode"] == opcode
                assert row["dex_entry"] == ("classes.dex" if index == 0 else "classes2.dex")
            methods = svc.query_dex_session(
                key, operation="list_methods", class_name=owner, offset=0, limit=100
            )
            assert methods["status"] == "ok" and methods["items"][0]["descriptor"] == method
            fields = svc.query_dex_session(
                key, operation="get_class_outline", class_name=owner, offset=0, limit=100
            )
            assert fields["status"] == "ok" and fields["items"][0]["descriptor"] == field
            graph = svc.query_dex_session(
                key, operation="get_call_graph", method_descriptor=method, offset=0, limit=100
            )
            assert graph["status"] == "ok" and len(graph["nodes"]) == len(graph["edges"]) == 1, (
                graph
            )
            assert graph["edges"][0]["instruction_offset"] == 6
            instructions = svc.query_dex_session(
                key, operation="disassemble_method", method_descriptor=method, offset=0, limit=100
            )
            assert instructions["status"] == "ok", instructions
            assert [
                (row["opcode"], row["instruction_offset"]) for row in instructions["items"]
            ] == [
                ("const-string", 0),
                ("const-class", 2),
                ("sget-object", 4),
                ("invoke-static", 6),
                ("return-object", 9),
            ]
        types = svc.query_dex_session(
            key,
            operation="find_type_refs",
            type_descriptor="Ljava/lang/Object;",
            type_relation="operand",
            offset=0,
            limit=100,
        )
        assert types["status"] == "ok" and types["total"] == 2, types
        assert [(row["opcode"], row["instruction_offset"]) for row in types["items"]] == [
            ("const-class", 2)
        ] * 2
        # The existing broad/declaration index also reads every logical file.
        broad = svc.query_dex_session(
            key,
            operation="find_type_refs",
            type_descriptor="Ljava/lang/Object;",
            type_relation="declaration",
            offset=0,
            limit=100,
        )
        assert broad["status"] == "ok" and broad["total"] == 2, broad


@pytest.mark.parametrize(
    "field,value",
    [(0, 0), (32, 119), (36, 112), (40, 0), (60, 0xFFFFFFFF), (112, 1), (116, 0), (8, 0)],
)
def test_later_logical_header_is_validated_before_publication(settings, tmp_path, field, value):
    data = bytearray(dex041_container())
    second = headers(data)[1]
    struct.pack_into("<I", data, second + field, value)
    path = tmp_path / "invalid-later.dex"
    path.write_bytes(data)
    with closing(
        DroidAscService(
            replace(settings, java_executable="java-must-not-run", jadx_home=None, dexlib_home=None)
        )
    ) as svc:
        result = svc.open_dex_session([str(path)])
        assert result["status"] == "error", result
        assert result["code"] in {"invalid_dex_container", "invalid_table", "integrity_mismatch"}
        assert svc.sessions.reserved == svc.sessions.opening == 0 and not svc.sessions.entries
    assert path.read_bytes() == data


@pytest.mark.parametrize("count", [64, 65])
def test_logical_file_limit_counts_headers_without_physical_duplication(settings, tmp_path, count):
    path = tmp_path / "many.dex"
    data = dex041_container(tuple(f"C{index}" for index in range(count)))
    path.write_bytes(data)
    with closing(
        DroidAscService(
            replace(settings, java_executable="java-must-not-run", jadx_home=None, dexlib_home=None)
        )
    ) as svc:
        result = svc.open_dex_session([str(path)])
        if count == 65:
            assert result["status"] == "error" and result["code"] == "dex_count_limit", result
        else:
            assert result["status"] == "ok" and result["class_count"] == 64, result
            assert len(result["sources"]) == 64
            assert sum(row["stored_size_bytes"] for row in result["sources"]) == len(data)
        assert svc.sessions.reserved == svc.sessions.opening == 0
