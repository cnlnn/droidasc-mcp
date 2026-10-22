"""Read-only mapped directory parity, CRC checks and bounded Unicode fallback."""

import hashlib
import os
import struct
import zipfile
import zlib

import pytest

from droidasc_mcp.native_dex import Dex, InvalidDex


def class_dex(names):
    from test_native_dex import type_pool_dex

    encoded = []
    for name in names:
        units = name.encode("utf-16-le", "surrogatepass")
        characters = "".join(
            chr(int.from_bytes(units[i : i + 2], "little")) for i in range(0, len(units), 2)
        )
        encoded.append(
            bytes([len(units) // 2])
            + characters.encode("utf-8", "surrogatepass").replace(b"\0", b"\xc0\x80")
            + b"\0"
        )
    dex = type_pool_dex(encoded)
    data = bytearray(dex.data)
    dex.close()
    data += bytes(-len(data) % 4)
    start = len(data)
    for index in range(len(names)):
        data += struct.pack("<8I", index, 0, 0xFFFFFFFF, 0, 0xFFFFFFFF, 0, 0, 0)
    struct.pack_into("<II", data, 96, len(names), start if names else 0)
    struct.pack_into("<I", data, 32, len(data))
    data[12:32] = hashlib.sha1(data[32:]).digest()
    struct.pack_into("<I", data, 8, zlib.adler32(data[12:]))
    return bytes(data)


def test_mapped_directory_returns_names_without_per_class_offset_tuples(tmp_path):
    from droidasc_mcp._dexscan import mapped_classes

    data = class_dex(["Lascii/C;", "Lunicode/\U0001f600;"])
    path = tmp_path / "names.dex"
    path.write_bytes(data)
    with path.open("rb") as stream:
        handle = stream.fileno()
        if os.name == "nt":
            import msvcrt

            handle = msvcrt.get_osfhandle(handle)
        names = mapped_classes(handle, 0, len(data), zlib.crc32(data))
    assert names == ["Lascii/C;", struct.unpack_from("<I", data, 100)[0] + 32]
    path.unlink()


@pytest.mark.parametrize("accelerator", [False, True])
def test_directory_matches_independent_unicode_cursor(tmp_path, accelerator):
    from droidasc_mcp.native_directory import class_entries

    names = ["Lz/Z;", "La/\U0001f600;", "La/\ud800;", "La/\0;", "La/\uffff;", "La/A;"]
    data = class_dex(names)
    dex = Dex(data)
    expected = [name for name, _ in dex.classes(accelerator=False, ordered=False)]
    dex.close()
    bundle = tmp_path / "input + mapped.apk"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("classes.dex", data)
    assert list(class_entries(bundle, accelerator=accelerator)) == [("classes.dex", expected)]
    # The mapping and every file handle must be released before session cleanup.
    bundle.unlink()


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize(
    "names",
    [
        ["Lz/Z;", "La/A;"],
        ["La/A;", "Lunicode/\U0001f600;", "Lunicode/\ud800;", "Lunicode/\0;"],
        ["La/A;", "La/A;"],
        ["Lunicode/\U0001f600;", "Lunicode/\U0001f600;"],
        ["Lunicode/\U0001f600;", "Lunicode/\ud83d\ude00;"],
    ],
)
def test_checked_directory_matches_python_and_older_accelerator(
    tmp_path, monkeypatch, names, legacy
):
    from droidasc_mcp import _dexscan
    from droidasc_mcp.native_directory import class_entries

    if legacy:
        monkeypatch.delattr(_dexscan, "checked_classes")
        monkeypatch.delattr(_dexscan, "mapped_checked_classes")
    data = class_dex(names)
    bundle = tmp_path / "checked.apk"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("classes.dex", data)
    first, second = Dex(data), Dex(data)
    try:
        try:
            expected = first.classes(accelerator=False, ordered=False)
        except InvalidDex:
            with pytest.raises(InvalidDex, match="Duplicate"):
                second.classes(ordered=False)
            with pytest.raises(InvalidDex, match="Duplicate"):
                list(class_entries(bundle))
        else:
            assert second.classes(ordered=False) == expected
            assert list(class_entries(bundle)) == [("classes.dex", [name for name, _ in expected])]
    finally:
        first.close()
        second.close()
    bundle.unlink()


def test_checked_ascii_directory_does_not_rewalk_python_rows(monkeypatch):
    from droidasc_mcp import _dexscan

    data = class_dex(["La/A;", "Lb/B;"])
    dex = Dex(data)
    arguments = (data, dex.tables[5][1], 2, dex.tables[1][1], 2, dex.tables[0][1], 2)
    rows, deferred, seen = _dexscan.checked_classes(*arguments)
    assert deferred == [] and seen == {"La/A;", "Lb/B;"}

    class NoPythonWalk(list):
        def __iter__(self):
            pytest.fail("Checked ASCII rows must not be rebuilt in a Python loop")

    rows = NoPythonWalk(rows)
    monkeypatch.setattr(_dexscan, "checked_classes", lambda *args: (rows, [], seen))
    try:
        assert dex.classes(ordered=False) is rows
    finally:
        dex.close()


@pytest.mark.parametrize("accelerator", [False, True])
def test_checked_directory_rejects_unmatched_malformed_unicode(tmp_path, accelerator):
    from droidasc_mcp.native_directory import class_entries

    data = bytearray(class_dex(["La/A;", "Lunicode/\uffff;"]))
    start = data.index(b"\xef\xbf\xbf")
    data[start] = 0xF5
    dex = Dex(bytes(data))
    try:
        with pytest.raises(InvalidDex):
            dex.classes(accelerator=accelerator, ordered=False)
    finally:
        dex.close()
    bundle = tmp_path / "unicode.apk"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("classes.dex", data)
    with pytest.raises(InvalidDex):
        list(class_entries(bundle, accelerator=accelerator))
    bundle.unlink()


def test_mapped_directory_does_not_read_full_dex_into_python(
    tmp_path, smali_dex_files, monkeypatch
):
    from droidasc_mcp.native_directory import class_entries

    bundle = tmp_path / "stored.apk"
    expected = []
    with zipfile.ZipFile(bundle, "w") as archive:
        for index, path in enumerate(smali_dex_files):
            dex = Dex(path.read_bytes())
            expected.append(
                (f"classes{index}.dex", [name for name, _ in dex.classes(ordered=False)])
            )
            dex.close()
            archive.write(path, f"classes{index}.dex")

    def no_bulk_read(*args, **kwargs):
        pytest.fail("Directory preparation must not materialize full DEX bytes via ZipExtFile")

    monkeypatch.setattr(zipfile.ZipExtFile, "read", no_bulk_read)
    assert list(class_entries(bundle)) == expected


def test_mapped_directory_rejects_snapshot_crc_corruption(tmp_path):
    from droidasc_mcp.native_directory import class_entries

    bundle = tmp_path / "corrupt.apk"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("classes.dex", class_dex(["Lfixture/C;"]))
    with bundle.open("r+b") as stream:
        stream.seek(30 + len("classes.dex") + 112)
        original = stream.read(1)
        stream.seek(-1, 1)
        stream.write(bytes([original[0] ^ 1]))
    with pytest.raises(InvalidDex, match="CRC"):
        list(class_entries(bundle))


def test_mapped_directory_rejects_duplicate_identities(tmp_path):
    from droidasc_mcp.native_directory import class_entries

    bundle = tmp_path / "duplicates.apk"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("classes.dex", class_dex(["Lfixture/C;", "Lfixture/C;"]))
    with pytest.raises(InvalidDex, match="Duplicate"):
        list(class_entries(bundle))


@pytest.mark.parametrize("crc_error", [False, True])
def test_mapped_crc_windows_cover_tail_and_release_owned_chunks(tmp_path, monkeypatch, crc_error):
    from droidasc_mcp.native_directory import class_entries

    data = bytearray(class_dex(["Lfixture/C;"]))
    data += b"x" * (3 * 1024**2 + 137)
    struct.pack_into("<I", data, 32, len(data))
    data[12:32] = hashlib.sha1(data[32:]).digest()
    struct.pack_into("<I", data, 8, zlib.adler32(data[12:]))
    bundle = tmp_path / "crc-windows.apk"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("classes.dex", data)
    original, chunks = zlib.crc32, []

    def crc(block, initial=0):
        assert type(block) is bytes
        assert 0 < len(block) <= 256 * 1024
        chunks.append(block)
        if crc_error and len(chunks) == 3:
            raise RuntimeError("CRC callback failed")
        return original(block, initial)

    monkeypatch.setattr(zlib, "crc32", crc)
    if crc_error:
        with pytest.raises(RuntimeError, match="CRC callback failed"):
            list(class_entries(bundle))
        assert b"".join(chunks) == data[: 3 * 256 * 1024]
    else:
        assert list(class_entries(bundle)) == [("classes.dex", ["Lfixture/C;"])]
        assert b"".join(chunks) == data
    # Retained callback arguments are owned bytes, never unmapped memory views.
    bundle.unlink()
    assert chunks[-1][-1] == ord("x")


@pytest.mark.parametrize("handle,offset,length", [(-1, 0, 112), (0, -1, 112), (0, 0, 0)])
def test_mapped_directory_rejects_invalid_mapping_arguments(handle, offset, length):
    from droidasc_mcp._dexscan import mapped_classes

    with pytest.raises(ValueError):
        mapped_classes(handle, offset, length, 0)


def test_mapped_directory_checks_local_header_consistency(tmp_path):
    from droidasc_mcp.native_directory import class_entries

    bundle = tmp_path / "local-header.apk"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("classes.dex", class_dex(["Lfixture/C;"]))
    with bundle.open("r+b") as stream:
        stream.seek(6)
        stream.write(b"\x08\0")
    with pytest.raises(InvalidDex, match="local header"):
        list(class_entries(bundle))
