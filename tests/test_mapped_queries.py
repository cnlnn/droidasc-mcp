"""Stored query windows retain the byte cursor's complete validation and results."""

import array
import mmap
import zipfile
from contextlib import closing

import pytest

from droidasc_mcp import native_dex
from droidasc_mcp.config import Settings
from droidasc_mcp.native_dex import Dex, InvalidDex, dex_entries, query_references
from droidasc_mcp.native_scan import scanner


def test_stored_queries_do_not_allocate_full_dex_bytes(tmp_path, monkeypatch):
    from test_native_directory import class_dex

    bundle = tmp_path / "snapshot.apk"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("classes.dex", class_dex(["La/A;", "Lu/\U0001f600;"]))

    def no_read(*args, **kwargs):
        pytest.fail("A mapped stored query must not read the complete member into bytes")

    monkeypatch.setattr(zipfile.ZipFile, "read", no_read)
    with closing(dex_entries(bundle)) as entries:
        name, dex = next(entries)
        assert name == "classes.dex"
        assert isinstance(dex.data, memoryview) and dex.data.readonly
        assert sorted(name for name, _ in dex.classes()) == ["La/A;", "Lu/\U0001f600;"]
    assert dex.data == b""
    bundle.unlink()


@pytest.mark.parametrize("compression", [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED])
def test_mapped_and_owned_cursors_match_complete_fixture(tmp_path, smali_dex_files, compression):
    from droidasc_mcp.native_strings import string_mask

    bundle = tmp_path / "snapshot.apk"
    with zipfile.ZipFile(bundle, "w", compression=compression) as archive:
        for number, path in enumerate(smali_dex_files):
            archive.writestr(f"classes{number}.dex", path.read_bytes())
    with closing(dex_entries(bundle)) as entries:
        for (_, actual), path in zip(entries, smali_dex_files, strict=True):
            expected = Dex(path.read_bytes())
            try:
                assert actual.classes() == expected.classes(accelerator=False)
                assert actual.matching_types("Lfixture/", fuzzy=True) == expected.matching_types(
                    "Lfixture/", fuzzy=True, accelerator=False
                )
                for field in (False, True):
                    assert actual.owner_members(field, {0, 1}) == expected.owner_members(
                        field, {0, 1}, accelerator=False
                    )
                for _, cls in expected.classes(accelerator=False):
                    assert actual.raw_members(cls) == expected.raw_members(cls, accelerator=False)
                    for _, _, code in expected.raw_members(cls, accelerator=False)[1]:
                        if code:
                            for field in (False, True):
                                assert list(scanner(actual, set(), field, False)(code)) == list(
                                    scanner(expected, set(), field, False, accelerator=False)(code)
                                )
                assert string_mask(actual, "fixture", True) == string_mask(
                    expected, "fixture", True, accelerator=False
                )
            finally:
                expected.close()
    bundle.unlink()


def test_every_query_page_matches_owned_input(tmp_path, smali_dex_files, monkeypatch):
    bundle = tmp_path / "snapshot.apk"
    with zipfile.ZipFile(bundle, "w") as archive:
        for number, path in enumerate(smali_dex_files):
            archive.writestr(f"classes{number}.dex", path.read_bytes())
    settings = Settings.from_env()
    queries = [
        {"operation": "find_field_refs", "field_descriptor": "Lfixture/Ordering;->value:I"},
        {"operation": "find_method_refs", "method_descriptor": "Lfixture/Target;->pick(I)V"},
        {
            "operation": "search_refs",
            "kind": "method",
            "class_name": "Lfixture/",
            "fuzzy_class": True,
        },
    ]
    owned = dex_entries
    for query in queries:
        query.update(offset=0, limit=1)
        while True:
            actual = query_references(settings, bundle, query)
            with monkeypatch.context() as context:
                context.setattr(native_dex, "dex_entries", lambda path: owned(path, mapped=False))
                expected = query_references(settings, bundle, query)
            assert actual == expected
            if not actual.get("has_more"):
                break
            query["offset"] = actual["next_offset"]
    bundle.unlink()


def test_mapped_snapshot_rechecks_crc_before_exposing_data(tmp_path):
    from test_native_directory import class_dex

    bundle = tmp_path / "snapshot.apk"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("classes.dex", class_dex(["La/A;"]))
    data = bytearray(bundle.read_bytes())
    base = 30 + len("classes.dex")
    data[base + 12] ^= 1
    bundle.write_bytes(data)
    with pytest.raises((InvalidDex, zipfile.BadZipFile), match="CRC"):
        next(dex_entries(bundle))
    bundle.unlink()


@pytest.mark.parametrize("offset", [-1, 112, 113, 2**62])
def test_native_buffer_bounds_are_checked(offset):
    from droidasc_mcp._dexscan import members

    with memoryview(bytes(112)) as data, pytest.raises(ValueError):
        members(data, offset, 0, 0)


def test_native_query_window_release_on_decode_failure(tmp_path):
    from droidasc_mcp._dexscan import members

    path = tmp_path / "window.dex"
    path.write_bytes(b"padding" + b"\xff" * 112)
    with (
        path.open("rb") as stream,
        mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as region,
    ):
        data = memoryview(region)[7:]
        for _ in range(30):
            with pytest.raises(ValueError, match="class"):
                members(data, 1, 0, 0)
        data.release()
    path.unlink()


def test_one_native_window_is_reused_for_a_dex(tmp_path, monkeypatch):
    from test_native_directory import class_dex

    from droidasc_mcp import native_snapshot

    mappings = []
    original = native_snapshot.mmap.mmap

    def counted(*args, **kwargs):
        mappings.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(native_snapshot.mmap, "mmap", counted)
    bundle = tmp_path / "snapshot.apk"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("classes.dex", class_dex(["La/A;"]))
    with closing(dex_entries(bundle)) as entries:
        _, dex = next(entries)
        for _ in range(25):
            assert dex.classes() == [("La/A;", dex.tables[5][1])]
    assert len(mappings) == 1
    bundle.unlink()


def test_early_query_close_releases_exported_window(tmp_path):
    from test_native_directory import class_dex

    bundle = tmp_path / "snapshot.apk"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("classes.dex", class_dex(["La/A;"]))
    entries = dex_entries(bundle)
    _, dex = next(entries)
    assert isinstance(dex.data, memoryview)
    entries.close()
    assert dex.data == b""
    bundle.unlink()


def test_invalid_dex_header_still_releases_mapping(tmp_path):
    bundle = tmp_path / "snapshot.apk"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("classes.dex", b"invalid" * 20)
    with pytest.raises(InvalidDex, match="header"):
        next(dex_entries(bundle))
    bundle.unlink()


def test_missing_native_mapping_retains_owned_fallback(tmp_path, monkeypatch):
    from test_native_directory import class_dex

    from droidasc_mcp import _dexscan

    monkeypatch.delattr(_dexscan, "buffer_inputs")
    bundle = tmp_path / "snapshot.apk"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("classes.dex", class_dex(["La/A;"]))
    with closing(dex_entries(bundle)) as entries:
        _, dex = next(entries)
        assert isinstance(dex.data, bytes)
        assert dex.classes() == [("La/A;", dex.tables[5][1])]
    bundle.unlink()


def test_scanner_cannot_reuse_closed_window(tmp_path, smali_dex_files):
    bundle = tmp_path / "snapshot.apk"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("classes.dex", smali_dex_files[0].read_bytes())
    with closing(dex_entries(bundle)) as entries:
        _, dex = next(entries)
        code = next(
            code for _, cls in dex.classes() for _, _, code in dex.raw_members(cls)[1] if code
        )
        scan = scanner(dex, set(), False, False)
        assert list(scan(code))
    with pytest.raises(InvalidDex):
        list(scan(code))
    bundle.unlink()


def test_buffer_export_is_pinned_across_python_argument_conversion():
    from droidasc_mcp._dexscan import members

    data = memoryview(bytes(112))

    class Offset:
        def __index__(self):
            data.release()
            return 1

    with pytest.raises(BufferError):
        members(data, Offset(), 0, 0)
    data.release()


@pytest.mark.parametrize("kind", ["writable", "strided", "wide", "released"])
def test_native_buffer_rejects_invalid_views_and_releases_exports(kind):
    from droidasc_mcp._dexscan import members

    data = (
        memoryview(bytearray(112))
        if kind == "writable"
        else memoryview(bytes(112))[::2]
        if kind == "strided"
        else memoryview(array.array("I", [0] * 28)).toreadonly()
        if kind == "wide"
        else memoryview(bytes(112))
    )
    if kind == "released":
        data.release()
    with pytest.raises((ValueError, BufferError)):
        members(data, 1, 0, 0)
    data.release()
