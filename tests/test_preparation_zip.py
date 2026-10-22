"""Compact preparation inventory versus the independent stdlib directory reader."""

import io
import stat
import struct
import zipfile

import pytest

from droidasc_mcp.archive_errors import ArchiveError
from droidasc_mcp.archive_worker import _entries
from droidasc_mcp.preparation_zip import PreparationZipFile


def archive_bytes(compression=zipfile.ZIP_DEFLATED, prefix=b"", comment=b"", entries=None):
    output = io.BytesIO(prefix)
    output.seek(len(prefix))
    with zipfile.ZipFile(output, "w", compression=compression) as archive:
        archive.comment = comment
        for name, data in entries or [
            ("classes.dex", b"first dex" * 100),
            ("res/raw/other.bin", b"resource"),
            ("base/dex/classes2.dex", b"second dex"),
            ("lib/example.jar", b"nested jar"),
            ("pkg/Test.class", b"class file"),
            ("splits/feature.apk", b"split apk"),
            ("res/", b""),
            ("assets/\u4e2d\u6587.txt", b"unicode resource"),
        ]:
            archive.writestr(name, data)
    return output.getvalue()


@pytest.mark.parametrize("compression", [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED])
@pytest.mark.parametrize("prefix", [b"", b"arbitrary self-extractor prefix"])
@pytest.mark.parametrize("comment", [b"", b"archive comment" * 200], ids=["no-comment", "comment"])
@pytest.mark.parametrize("zip64", [False, True])
def test_retained_member_metadata_and_bytes_match_stdlib(
    compression, prefix, comment, zip64, monkeypatch
):
    if zip64:
        monkeypatch.setattr(zipfile, "ZIP64_LIMIT", 500)
    data = archive_bytes(compression, prefix, comment)
    with (
        zipfile.ZipFile(io.BytesIO(data)) as baseline,
        PreparationZipFile(io.BytesIO(data)) as compact,
    ):
        assert set(compact.inventory) == set(_entries(baseline))
        assert compact.comment == baseline.comment
        assert compact.start_dir == baseline.start_dir
        assert len(compact.filelist) == 5
        assert compact.inventory["res/raw/other.bin"] is None
        for info in compact.filelist:
            expected = baseline.getinfo(info.filename)
            for field in zipfile.ZipInfo.__slots__:
                if hasattr(info, field):
                    assert getattr(info, field) == getattr(expected, field), field
            with baseline.open(expected) as original, compact.open(info) as stream:
                assert stream.read() == original.read()


def test_prepended_zip_with_unadjusted_offsets_matches_stdlib():
    data = b"concatenated prefix" + archive_bytes()
    with (
        zipfile.ZipFile(io.BytesIO(data)) as baseline,
        PreparationZipFile(io.BytesIO(data)) as compact,
    ):
        assert compact.start_dir == baseline.start_dir
        for info in compact.filelist:
            assert info.header_offset == baseline.getinfo(info.filename).header_offset
            assert compact.read(info) == baseline.read(info.filename)


@pytest.mark.parametrize("name", ["../bad", "/absolute", "a\\b", "a/./b", "a//b", "C:/bad"])
def test_omitted_resource_names_still_validated(name):
    wire_name = name.replace("\\", "/")
    data = archive_bytes(entries=[("classes.dex", b"dex"), (wire_name, b"resource")])
    if wire_name != name:
        # Windows ZipInfo writers normalize backslashes; mutate both on-wire names.
        assert data.count(wire_name.encode()) == 2
        data = data.replace(wire_name.encode(), name.encode())
    with pytest.raises(ArchiveError, match="safe relative"):
        PreparationZipFile(io.BytesIO(data))


def test_omitted_resource_duplicates_still_rejected():
    with pytest.warns(UserWarning, match="Duplicate"):
        data = archive_bytes(entries=[("assets/a", b"one"), ("assets/a", b"two")])
    with pytest.raises(ArchiveError, match="duplicate"):
        PreparationZipFile(io.BytesIO(data))


def test_omitted_resource_special_type_still_rejected():
    member = zipfile.ZipInfo("assets/link")
    member.external_attr = (stat.S_IFLNK | 0o777) << 16
    data = archive_bytes(entries=[(member, b"/etc/passwd")])
    with pytest.raises(ArchiveError, match="non-regular"):
        PreparationZipFile(io.BytesIO(data))


def test_omitted_resource_nul_name_still_rejected():
    data = archive_bytes(entries=[("assets/abc", b"resource")])
    start = data.index(zipfile.stringCentralDir)
    data = data[:start] + data[start:].replace(b"assets/abc", b"assets/a\0c")
    with pytest.raises(ArchiveError, match="NUL"):
        PreparationZipFile(io.BytesIO(data))


def test_inventory_limit_includes_omitted_resources(monkeypatch):
    from droidasc_mcp import preparation_zip

    data = archive_bytes(entries=[("assets/a", b""), ("assets/b", b""), ("classes.dex", b"dex")])
    monkeypatch.setattr(preparation_zip, "MAX_ENTRIES", 2)
    with pytest.raises(ArchiveError, match="too many"):
        PreparationZipFile(io.BytesIO(data))


@pytest.mark.parametrize("legacy_reader", [False, True])
@pytest.mark.parametrize("failure", ["crc", "local_name", "overlap"])
def test_stdlib_selected_member_checks_remain_active(failure, legacy_reader, monkeypatch):
    if legacy_reader:
        from droidasc_mcp import preparation_zip

        monkeypatch.setattr(preparation_zip, "_MEMBER_BOUNDS", False)
    data = bytearray(archive_bytes(entries=[("classes.dex", b"payload"), ("assets/end", b"end")]))
    first = data.index(zipfile.stringCentralDir)
    if failure == "crc":
        struct.pack_into("<I", data, first + 16, 123)
    elif failure == "local_name":
        data[zipfile.sizeFileHeader] = ord("x")
    else:
        second = data.index(zipfile.stringCentralDir, first + 4)
        struct.pack_into("<I", data, second + 42, 1)
    with PreparationZipFile(io.BytesIO(data)) as archive, pytest.raises(zipfile.BadZipFile):
        archive.read("classes.dex")


def test_legacy_overlap_guard_runs_before_stdlib_open(monkeypatch):
    from droidasc_mcp import preparation_zip

    monkeypatch.setattr(preparation_zip, "_MEMBER_BOUNDS", False)
    data = bytearray(archive_bytes(entries=[("classes.dex", b"payload"), ("assets/end", b"end")]))
    first = data.index(zipfile.stringCentralDir)
    second = data.index(zipfile.stringCentralDir, first + 4)
    struct.pack_into("<I", data, second + 42, 1)
    with PreparationZipFile(io.BytesIO(data)) as archive:

        def unchecked_open(*args, **kwargs):
            pytest.fail("Legacy stdlib must not receive an overlapping payload")

        monkeypatch.setattr(zipfile.ZipFile, "open", unchecked_open)
        with pytest.raises(zipfile.BadZipFile, match="Overlapped"):
            archive.read("classes.dex")


def test_legacy_reader_preserves_payloads_and_stream_positions(monkeypatch):
    from droidasc_mcp import preparation_zip

    monkeypatch.setattr(preparation_zip, "_MEMBER_BOUNDS", False)
    data = archive_bytes(prefix=b"prefix")
    with (
        PreparationZipFile(io.BytesIO(data)) as archive,
        archive.open("classes.dex") as first,
        archive.open("pkg/Test.class") as second,
    ):
        assert first.read(5) == b"first"
        assert second.read() == b"class file"
        assert first.read() == (b"first dex" * 100)[5:]


@pytest.mark.parametrize("failure", ["variable_bounds", "header_offset", "signature", "extra"])
def test_invalid_directory_rejected_before_any_member_read(failure):
    data = bytearray(archive_bytes(entries=[("assets/a", b"resource")]))
    start = data.index(zipfile.stringCentralDir)
    if failure == "variable_bounds":
        struct.pack_into("<H", data, start + 28, 65535)
    elif failure == "header_offset":
        struct.pack_into("<I", data, start + 42, start + 1)
    elif failure == "signature":
        data[start] = ord("X")
    else:
        # An extra field claims bytes that lie outside its own central record.
        struct.pack_into("<H", data, start + 30, 4)
        struct.pack_into("<H", data, start + 28, len("assets/a") - 4)
        data[start + zipfile.sizeCentralDir + 4 : start + zipfile.sizeCentralDir + 8] = (
            b"\x01\x00\xff\xff"
        )
    with pytest.raises(zipfile.BadZipFile):
        PreparationZipFile(io.BytesIO(data))


def test_resource_inventory_memory_is_not_full_zipinfo_retention():
    data = archive_bytes(entries=[(f"res/raw/{number}.bin", b"") for number in range(10000)])
    with PreparationZipFile(io.BytesIO(data)) as archive:
        assert len(archive.inventory) == 10000
        assert not archive.filelist and not archive.NameToInfo
        assert all(info is None for info in archive.inventory.values())


def test_directory_reads_do_not_materialize_the_whole_central_directory():
    data = archive_bytes(
        entries=[(f"res/raw/{number}/" + "a" * 100 + ".bin", b"") for number in range(10000)]
    )

    class BoundedInput(io.BytesIO):
        def read(self, count=-1):
            block = super().read(count)
            assert len(block) <= 3 * 65535, "Directory metadata reads must be record-bounded"
            return block

    with PreparationZipFile(BoundedInput(data)) as archive:
        assert len(archive.inventory) == 10000


def test_empty_archive_matches_stdlib():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w"):
        pass
    with PreparationZipFile(io.BytesIO(stream.getvalue())) as archive:
        assert not archive.inventory and not archive.infolist()


@pytest.mark.parametrize("prefix", [b"", b"prefix"])
def test_zip64_concatenation_and_data_descriptor_reads(prefix, monkeypatch):
    monkeypatch.setattr(zipfile, "ZIP64_LIMIT", 500)

    class Unseekable(io.BytesIO):
        def seek(self, *args):
            raise OSError("Unseekable output requires a data descriptor")

    stream = Unseekable()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        with archive.open("classes.dex", "w", force_zip64=True) as member:
            member.write(b"dex payload" * 1000)
        archive.writestr("assets/end", b"end")
    data = prefix + stream.getvalue()
    with (
        zipfile.ZipFile(io.BytesIO(data)) as baseline,
        PreparationZipFile(io.BytesIO(data)) as compact,
    ):
        assert compact.getinfo("classes.dex").flag_bits & 8
        assert compact.read("classes.dex") == baseline.read("classes.dex")
