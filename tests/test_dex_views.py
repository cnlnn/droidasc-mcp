"""Private 041 aliases, original CRCs and independently checked source handoff."""

import hashlib
import struct
import zipfile
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from dex041_fixture import dex041_container

from droidasc_mcp.archive_errors import ArchiveError
from droidasc_mcp.dex_views import VIEW_FIELD, source_view, view_extra, view_selector
from droidasc_mcp.native_dex import InvalidDex
from droidasc_mcp.native_directory import class_entries
from droidasc_mcp.native_snapshot import query_dex
from droidasc_mcp.service import DroidAscService


def snapshot(path, data, *, extra=None, alias_data=b"", backing=True):
    offset = struct.unpack_from("<I", data, 32)[0]
    with zipfile.ZipFile(path, "w") as archive:
        if backing:
            physical = zipfile.ZipInfo("classes.dex")
            physical.extra = view_extra("classes.dex", 0)
            archive.writestr(physical, data)
        alias = zipfile.ZipInfo("classes2.dex")
        alias.extra = view_extra("classes.dex", offset) if extra is None else extra
        archive.writestr(alias, alias_data)
    return offset


@pytest.mark.parametrize("mapped", [False, True])
def test_alias_reads_full_original_and_releases_all_views(tmp_path, mapped):
    data = dex041_container(shared_strings=True)
    bundle = tmp_path / "input.apk"
    offset = snapshot(bundle, data)
    with (
        zipfile.ZipFile(bundle) as archive,
        query_dex(bundle, archive, archive.getinfo("classes2.dex"), mapped=mapped) as dex,
    ):
        assert dex.header_offset == offset and bytes(dex.data) == data
        assert [row[0] for row in dex.classes()] == ["Loracle/B;"]
    bundle.unlink()


@pytest.mark.parametrize(
    "extra",
    [
        b"\x41",
        struct.pack("<HH", VIEW_FIELD, 100),
        struct.pack("<HHBI", VIEW_FIELD, 6, 2, 120) + b"x",
        struct.pack("<HHBI", VIEW_FIELD, 6, 1, 120) + b"\xff",
        struct.pack("<HHBI", VIEW_FIELD, 9, 1, 120) + b"../x",
        view_extra("classes.dex", 120) * 2,
    ],
)
def test_private_extra_rejects_truncation_version_names_and_duplicates(extra):
    info = zipfile.ZipInfo("classes2.dex")
    info.extra = extra
    with pytest.raises(InvalidDex):
        view_selector(info)


@pytest.mark.parametrize(
    "malformation", ["missing", "nonempty", "zero", "self", "chain", "not_header"]
)
def test_alias_rejects_missing_nonempty_cyclic_and_nonheader_views(tmp_path, malformation):
    bundle = tmp_path / "invalid.apk"
    data = dex041_container()
    header = struct.unpack_from("<I", data, 32)[0]
    extra = {
        "zero": view_extra("classes.dex", 0),
        "self": view_extra("classes2.dex", header),
        "chain": view_extra("classes3.dex", header),
        "not_header": view_extra("classes.dex", 120),
    }.get(malformation)
    snapshot(
        bundle,
        data,
        extra=extra,
        backing=malformation != "missing",
        alias_data=b"x" if malformation == "nonempty" else b"",
    )
    if malformation == "chain":
        with zipfile.ZipFile(bundle, "a") as archive:
            alias = zipfile.ZipInfo("classes3.dex")
            alias.extra = view_extra("classes.dex", header)
            archive.writestr(alias, b"")
    with pytest.raises(InvalidDex):
        list(class_entries(bundle))
    bundle.unlink()


@pytest.mark.parametrize("mapped", [False, True])
def test_alias_crc_covers_physical_tail_outside_selected_class(tmp_path, mapped):
    bundle = tmp_path / "corrupt.apk"
    snapshot(bundle, dex041_container())
    with zipfile.ZipFile(bundle) as archive:
        info = archive.getinfo("classes.dex")
        position = (
            info.header_offset + 30 + len(info.filename) + len(info.extra) + info.file_size - 1
        )
    with bundle.open("r+b") as stream:
        stream.seek(position)
        byte = stream.read(1)[0]
        stream.seek(position)
        stream.write(bytes([byte ^ 1]))
    with (
        zipfile.ZipFile(bundle) as archive,
        pytest.raises((InvalidDex, zipfile.BadZipFile), match="CRC"),
        query_dex(bundle, archive, archive.getinfo("classes2.dex"), mapped=mapped),
    ):
        pytest.fail("corrupt original bytes were exposed")
    bundle.unlink()


def test_older_accelerator_uses_checked_python_041_fallback(tmp_path, monkeypatch):
    import droidasc_mcp

    def old_abi(*args):
        pytest.fail("standard-only accelerator received a 041 logical view")

    monkeypatch.setattr(droidasc_mcp, "_dexscan", SimpleNamespace(mapped_classes=old_abi))
    bundle = tmp_path / "old-abi.apk"
    snapshot(bundle, dex041_container())
    assert list(class_entries(bundle)) == [
        ("classes.dex", ["Loracle/A;"]),
        ("classes2.dex", ["Loracle/B;"]),
    ]
    bundle.unlink()


@pytest.mark.parametrize("accelerator", [False, True])
@pytest.mark.parametrize(
    "field,value", [(0, 0), (32, 119), (36, 112), (40, 0), (60, 0xFFFFFFFF), (112, 1), (116, 0)]
)
def test_mapped_and_python_directory_validate_every_physical_header(
    tmp_path, accelerator, field, value
):
    data = bytearray(dex041_container())
    second = struct.unpack_from("<I", data, 32)[0]
    struct.pack_into("<I", data, second + field, value)
    bundle = tmp_path / "invalid-header.apk"
    snapshot(bundle, data)
    with pytest.raises(InvalidDex):
        list(class_entries(bundle, accelerator=accelerator))
    bundle.unlink()


def test_source_handoff_is_exact_upstream_header_copy_not_input_repair(tmp_path):
    data = dex041_container(shared_strings=True)
    bundle = tmp_path / "original.apk"
    offset = snapshot(bundle, data)
    original = bundle.read_bytes()
    workspace = tmp_path / "query"
    workspace.mkdir()
    target, metadata = source_view(bundle, "classes2.dex", workspace, len(data) + 1024**2)
    expected = data[offset : offset + 120] + data[120:]
    with zipfile.ZipFile(target) as archive:
        assert archive.namelist() == ["classes2.dex"]
        assert archive.read("classes2.dex") == expected
    assert metadata["source_view"]["view_sha256"] == hashlib.sha256(expected).hexdigest()
    assert metadata["source_view"]["logical_header_offset"] == offset
    assert bundle.read_bytes() == original
    target.unlink()
    bundle.unlink()


@pytest.mark.parametrize("budget", [None, True, 0, 100])
def test_unreserved_source_view_writes_nothing(tmp_path, budget):
    bundle = tmp_path / "original.apk"
    snapshot(bundle, dex041_container())
    workspace = tmp_path / "query"
    workspace.mkdir()
    with pytest.raises(ArchiveError, match="reserved"):
        source_view(bundle, "classes2.dex", workspace, budget)
    assert not list(workspace.iterdir())


@pytest.mark.parametrize("operation", ["get_class_source", "get_method_source"])
def test_one_shot_later_source_uses_accounted_ephemeral_session(settings, tmp_path, operation):
    path = tmp_path / "input.dex"
    data = dex041_container(shared_strings=True)
    path.write_bytes(data)
    with closing(
        DroidAscService(
            replace(settings, java_executable="java-must-not-run", jadx_home=None, dexlib_home=None)
        )
    ) as svc:
        query = {
            "operation": operation,
            "class_name": "oracle.B",
            "offset": 0,
            "limit": 100,
            "threads": 1,
        }
        if operation == "get_method_source":
            query.update(
                method_descriptor="Loracle/B;->hello()Ljava/lang/String;", source_format="smali"
            )
        result = svc.analyze_dex([str(path)], **query)
        assert result["status"] == "ok" and "value-B" in result["source"], result
        assert "session_id" not in result
        assert result["sources"][1]["sha256"] == hashlib.sha256(data).hexdigest()
        assert svc.sessions.reserved == svc.sessions.opening == 0 and not svc.sessions.entries
    assert path.read_bytes() == data


def test_later_source_contents_and_temporary_files_are_removed(settings, tmp_path, monkeypatch):
    import tempfile

    path = tmp_path / "input.dex"
    path.write_bytes(dex041_container())
    temporary = tmp_path / "owned"
    temporary.mkdir()
    with closing(
        DroidAscService(
            replace(settings, java_executable="java-must-not-run", jadx_home=None, dexlib_home=None)
        )
    ) as svc:
        opened = svc.open_dex_session([str(path)])
        key = opened["session_id"]
        root = Path(svc.sessions.entries[key].storage.name)
        original = (root / "analysis.apk").read_bytes()
        monkeypatch.setattr(tempfile, "tempdir", str(temporary))
        for operation in ("get_class_source", "get_method_source"):
            query = {
                "operation": operation,
                "class_name": "oracle.B",
                "offset": 0,
                "limit": 100,
                "threads": 1,
            }
            if operation == "get_method_source":
                query.update(
                    method_descriptor="Loracle/B;->hello()Ljava/lang/String;", source_format="smali"
                )
            result = svc.query_dex_session(key, **query)
            assert result["status"] == "ok" and "value-B" in result["source"], result
            assert result["source_view"]["logical_header_offset"] > 0
            assert svc.sessions.reserved == 0 and not list(temporary.iterdir())
            assert (root / "analysis.apk").read_bytes() == original
        svc.close_artifact(key)
        assert not root.exists()
