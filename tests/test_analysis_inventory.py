"""Compact handle inventory retains all-entry budgets and discovery metadata."""

import io
import struct
import zipfile

import pytest

from droidasc_mcp.analysis_session import inspect_snapshot
from droidasc_mcp.archive_errors import ArchiveError
from droidasc_mcp.preparation_zip import PreparationZipFile


def make_archive(entries, prefix=b""):
    output = io.BytesIO(prefix)
    output.seek(len(prefix))
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return output.getvalue()


@pytest.mark.parametrize("zip64", [False, True])
@pytest.mark.parametrize("prefix", [b"", b"self-extracting prefix"])
def test_all_member_statistics_match_stdlib(zip64, prefix, monkeypatch):
    if zip64:
        monkeypatch.setattr(zipfile, "ZIP64_LIMIT", 500)
    data = make_archive(
        [
            ("res/raw/value.bin", b"resource" * 1000),
            ("base/dex/classes.dex", b"dex" * 300),
            ("feature/dex/OTHER.DEX", b"dex" * 500),
            ("pkg/Probe.class", b"class"),
            ("assets/", b""),
        ],
        prefix,
    )
    with (
        zipfile.ZipFile(io.BytesIO(data)) as expected,
        PreparationZipFile(io.BytesIO(data)) as actual,
    ):
        infos = expected.infolist()
        assert actual.uncompressed_size == sum(info.file_size for info in infos)
        assert actual.largest_dex_size == max(
            info.file_size for info in infos if info.filename.lower().endswith(".dex")
        )
        assert set(actual.inventory) == {info.filename for info in infos}
        assert actual.inventory["res/raw/value.bin"] is None


def test_handle_inventory_uses_compact_reader_and_keeps_all_capabilities(tmp_path, monkeypatch):
    import droidasc_mcp.preparation_zip as module

    path = tmp_path / "sample.aab"
    path.write_bytes(
        make_archive(
            [
                ("base/manifest/AndroidManifest.xml", b"<manifest/>"),
                ("base/dex/classes.dex", b"dex"),
                ("feature/dex/classes.dex", b"second"),
                ("pkg/Probe.class", b"class"),
                *[(f"res/raw/{number}.bin", b"value") for number in range(1000)],
            ]
        )
    )
    observed = []
    original = module.PreparationZipFile

    class Observed(original):
        def __init__(self, *args):
            super().__init__(*args)
            observed.append((len(self.inventory), len(self.filelist)))

    monkeypatch.setattr(module, "PreparationZipFile", Observed)
    result = inspect_snapshot(path, path, path.stat(), "digest", 1024)
    assert observed == [(1004, 3)]
    assert result.entry_count == 1004
    assert result.dex_files == ("base/dex/classes.dex", "feature/dex/classes.dex")
    assert set(result.capabilities) == {"dex", "jvm-class-inventory", "manifest", "archive"}


def test_omitted_resources_still_count_towards_expansion_budget(tmp_path):
    data = bytearray(make_archive([("assets/one.bin", b"x"), ("assets/two.bin", b"y")]))
    position = data.index(zipfile.stringCentralDir)
    while data[position : position + 4] == zipfile.stringCentralDir:
        struct.pack_into("<I", data, position + 24, 3 * 1024**3)
        name, extra, comment = struct.unpack_from("<HHH", data, position + 28)
        position += 46 + name + extra + comment
    path = tmp_path / "large.apk"
    path.write_bytes(data)
    with pytest.raises(ArchiveError, match="uncompressed-size") as raised:
        inspect_snapshot(path, path, path.stat(), "digest", 1024)
    assert raised.value.code == "container_limit"


def test_noncanonical_dex_still_counts_towards_per_member_budget(tmp_path):
    path = tmp_path / "large.aab"
    path.write_bytes(make_archive([("feature/dex/OTHER.DEX", b"x" * 200)]))
    with pytest.raises(ArchiveError, match="DEX above the size limit") as raised:
        inspect_snapshot(path, path, path.stat(), "digest", 100)
    assert raised.value.code == "input_limit"


def test_no_code_or_members_has_zero_largest_dex(tmp_path):
    path = tmp_path / "empty.jar"
    path.write_bytes(make_archive([]))
    with PreparationZipFile(path) as archive:
        assert archive.uncompressed_size == archive.largest_dex_size == 0
    result = inspect_snapshot(path, path, path.stat(), "digest", 1)
    assert result.entry_count == 0 and result.dex_files == ()
    assert result.capabilities == ("archive",)
